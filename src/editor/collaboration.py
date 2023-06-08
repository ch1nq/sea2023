import asyncio
import logging
import pathlib
from typing import Literal

import pydantic
import websockets
import websockets.server

from src import process_model
from src.editor import commands, process_model_controller
from src import server


class JoinSessionRequest(pydantic.BaseModel):
    request_type: Literal["join_session"]
    model_id: process_model.ModelId


class WatchSessionRequest(pydantic.BaseModel):
    request_type: Literal["watch_session"]
    model_id: process_model.ModelId


class ExecuteCommandRequest(pydantic.BaseModel):
    request_type: Literal["execute_command"]
    command: commands.ProcessModelCommandUnion = pydantic.Field(..., discriminator="command_type")


class InspectorRequest(pydantic.BaseModel):
    request_type: Literal["inspector"]
    node_id: process_model.NodeId


class UndoRequest(pydantic.BaseModel):
    request_type: Literal["undo"]


class RedoRequest(pydantic.BaseModel):
    request_type: Literal["redo"]


class Request(pydantic.BaseModel):
    request: JoinSessionRequest | WatchSessionRequest | ExecuteCommandRequest | InspectorRequest | UndoRequest | RedoRequest = pydantic.Field(
        ..., discriminator="request_type"
    )


class UpdateCollaboratorsEvent(pydantic.BaseModel):
    event_type: Literal["update_collaborators"] = "update_collaborators"
    collaborator_ids: list[str]


class UpdateModelEvent(pydantic.BaseModel):
    event_type: Literal["update_model"] = "update_model"
    model: dict

    @classmethod
    def from_model(cls, model: process_model.ProcessModel) -> "UpdateModelEvent":
        return cls(model=model._serialize_to_dict())


class UpdateInspectorEvent(pydantic.BaseModel):
    event_type: Literal["update_inspector"] = "update_inspector"
    node_id: process_model.NodeId
    inspector_html: str


class CloseInspectorEvent(pydantic.BaseModel):
    event_type: Literal["close_inspector"] = "close_inspector"


class SavedSuccessEvent(pydantic.BaseModel):
    event_type: Literal["saved_success"] = "saved_success"


class UpdateUndoRedoEvent(pydantic.BaseModel):
    event_type: Literal["update_undo_redo"] = "update_undo_redo"
    can_undo: bool
    can_redo: bool


class Event(pydantic.BaseModel):
    event: UpdateModelEvent | UpdateCollaboratorsEvent | UpdateInspectorEvent | UpdateUndoRedoEvent | CloseInspectorEvent = pydantic.Field(
        ..., discriminator="event_type"
    )


class EditorSession:
    model_controller: process_model_controller.ProcessModelController
    _collaborators: set[websockets.server.WebSocketServerProtocol]
    _spectators: set[websockets.server.WebSocketServerProtocol]

    def __init__(self, model: process_model.ProcessModel) -> None:
        model_controller = process_model_controller.ProcessModelController(model)
        self.model_controller = model_controller
        self._collaborators = set()
        self._spectators = set()

    def broadcast_state(self) -> None:
        """Broadcast the model state and undo/redo state"""
        websockets.broadcast(
            self._spectators,
            UpdateModelEvent.from_model(self.model_controller.model).json(),
        )
        websockets.broadcast(
            self._collaborators,
            UpdateUndoRedoEvent(
                can_undo=self.model_controller.history.can_undo, can_redo=self.model_controller.history.can_redo
            ).json(),
        )

    async def process_messages(self, client: websockets.server.WebSocketServerProtocol) -> None:
        """Receive and process messages from client and propagate changes to other client."""
        async for message in client:
            match Request.parse_raw(message).request:
                case ExecuteCommandRequest(command=command) if isinstance(command, commands.SaveModelCommand):
                    logging.info("Received save request")
                    self.model_controller.execute(command)
                    await client.send(SavedSuccessEvent().json())
                case ExecuteCommandRequest(command=command):
                    logging.info(f"Received command: {command}")
                    self.model_controller.execute(command)
                    if isinstance(command, commands.UndoableCommand):
                        self.broadcast_state()
                case UndoRequest():
                    logging.info("Received undo request")
                    self.model_controller.undo()
                    self.broadcast_state()
                case RedoRequest():
                    logging.info("Received redo request")
                    self.model_controller.redo()
                    self.broadcast_state()
                case InspectorRequest(node_id=node_id):
                    logging.info("Received inspector request for node: %s", node_id)
                    node = self.model_controller.model.get_node(node_id)
                    if node is None:
                        logging.warning(f"Received inspector request for unknown node: {node_id}")
                        await client.send(CloseInspectorEvent().json())
                        continue
                    with server.app.app_context():
                        html = server.flask.render_template(
                            "inspector_content.html",
                            properties=node.get_inspectables(),
                            node_id=node_id,
                            model_id=self.model_controller.model.id,
                        )
                        await client.send(UpdateInspectorEvent(node_id=node_id, inspector_html=html).json())
                case unknown_request:
                    logging.warning(f"Received unknown request: {unknown_request}")

    async def update_collaborators(self) -> None:
        for collaborator in self._collaborators:
            await collaborator.send(
                UpdateCollaboratorsEvent(
                    collaborator_ids=[hash(c.remote_address) for c in self._collaborators if c != collaborator]
                ).json()
            )

    async def join(self, websocket: websockets.server.WebSocketServerProtocol) -> None:
        self._collaborators.add(websocket)
        self._spectators.add(websocket)
        logging.info(f"Collaborator joined: {websocket.remote_address}")
        logging.info(f"Number of collaborators: {len(self._collaborators)}")
        try:
            # Send the current state of the model to the client.
            await websocket.send(UpdateModelEvent.from_model(self.model_controller.model).json())
            await self.update_collaborators()
            # Process messages from the client.
            await self.process_messages(websocket)
        finally:
            self._collaborators.remove(websocket)
            self._spectators.remove(websocket)
            await self.update_collaborators()
            await self.close_after_timeout(2)

    async def watch(self, websocket: websockets.server.WebSocketServerProtocol) -> None:
        self._spectators.add(websocket)
        try:
            await websocket.send(UpdateModelEvent.from_model(self.model_controller.model).json())
            await self.update_collaborators()
            # Spectators cannot send messages to the server.
            await websocket.wait_closed()
        finally:
            self._spectators.remove(websocket)
            await self.update_collaborators()
            await self.close_after_timeout(60)

    async def close_after_timeout(self, timeout: float) -> None:
        # Close the editor session if there are no collaborators or spectators left after the timeout.
        if self._collaborators or self._spectators:
            return
        logging.info(
            f"Closing editor session for model: {self.model_controller.model.id} in {timeout} seconds if no collaborators or spectators join."
        )
        await asyncio.sleep(timeout)
        if not self._collaborators and not self._spectators:
            open_editors.pop(self.model_controller.model.id)
            logging.info(f"Closed editor session for model: {self.model_controller.model.id}")


open_editors: dict[process_model.ModelId, EditorSession] = {}


def get_open_editor(path: str | None) -> EditorSession:
    global open_models

    if path is None:
        raise ValueError("Path is None")

    model_type = process_model.ProcessModelType.from_path(pathlib.Path(path))
    model_class = process_model.model_type_to_class(model_type)

    try:
        model = model_class.load(pathlib.Path(path))
        if model.id in open_editors:
            open_editor = open_editors[model.id]
        else:
            open_editor = EditorSession(model)
            open_editors[model.id] = open_editor
    except FileNotFoundError as error:
        logging.error(f"File not found {path}")
        raise error

    return open_editor


async def handler(websocket: websockets.server.WebSocketServerProtocol) -> None:
    """
    Handle a connection and dispatch it according to who is connecting.
    """
    message = await websocket.recv()
    request = Request.parse_raw(message).request

    match request:
        case JoinSessionRequest() as join_request:
            editor = get_open_editor(join_request.model_id)
            await editor.join(websocket)
        case WatchSessionRequest() as watch_request:
            editor = get_open_editor(watch_request.model_id)
            await editor.watch(websocket)
        case unknown_request:
            raise ValueError(f"Unknown request {unknown_request}")
