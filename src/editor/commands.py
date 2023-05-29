import abc
import pathlib
from typing import Any
import typing

import pydantic
from src import process_model


CommandOutputT = typing.TypeVar("CommandOutputT")


class Command(abc.ABC, typing.Generic[CommandOutputT]):
    @abc.abstractmethod
    def execute(self) -> CommandOutputT:
        ...


class ProcessModelCommand(Command[CommandOutputT], pydantic.BaseModel):
    _model: process_model.ProcessModel | None = pydantic.PrivateAttr(default=None)

    def set_model(self, model: process_model.ProcessModel) -> None:
        self._model = model


class UndoableCommand(Command[CommandOutputT]):
    @abc.abstractmethod
    def undo(self) -> None:
        ...

    def redo(self) -> CommandOutputT:
        return self.execute()


class SaveModelCommand(ProcessModelCommand):
    path: pathlib.Path

    def execute(self) -> None:
        self._model.save(self.path)


class CreateNodeCommand(ProcessModelCommand, UndoableCommand):
    x: float
    y: float
    node_kwargs: dict[str, Any] = pydantic.Field(default_factory=dict)
    _node: process_model.NodeT = pydantic.PrivateAttr()

    def execute(self) -> process_model.NodeT:
        self._node = self._model.add_node_from_values(x=self.x, y=self.y, **self.node_kwargs)
        return self._node

    def undo(self) -> None:
        self._model.delete_node(self._node.id)

    def redo(self) -> process_model.NodeT:
        self._model.add_node(self._node)
        return self._node


class DeleteNodeCommand(ProcessModelCommand, UndoableCommand):
    node_id: process_model.NodeId
    _node: process_model.Node = pydantic.PrivateAttr()
    _edges: list[process_model.Edge] = pydantic.PrivateAttr()

    def execute(self) -> None:
        self._node = self._model.get_node(self.node_id)
        self._edges = self._model.get_edges()
        self._model.delete_node(self.node_id)

    def undo(self) -> None:
        self._model.add_node(self._node)
        for edge in self._edges:
            self._model.add_edge(edge)


class MoveNodeCommand(ProcessModelCommand, UndoableCommand):
    node_id: process_model.NodeId
    x: float
    y: float
    _old_x: float = pydantic.PrivateAttr()
    _old_y: float = pydantic.PrivateAttr()

    def execute(self) -> None:
        node: process_model.Node = self._model.get_node(self.node_id)
        self._old_x = node.position.x
        self._old_y = node.position.y
        self._model.move_node(self.node_id, self.x, self.y)

    def undo(self) -> None:
        self._model.move_node(self.node_id, self._old_x, self._old_y)


class CreateEdgeCommand(ProcessModelCommand, UndoableCommand):
    start_node_id: process_model.NodeId
    end_node_id: process_model.NodeId
    edge_kwargs: dict[str, Any] = pydantic.Field(default_factory=dict)
    _edge: process_model.Edge | None = pydantic.PrivateAttr()

    def execute(self) -> process_model.EdgeT:
        self._edge = self._model.add_edge_from_values(self.start_node_id, self.end_node_id, **self.edge_kwargs)
        return self._edge

    def undo(self) -> None:
        if self._edge is not None:
            self._model.delete_edge(self._edge.id)

    def redo(self) -> Any:
        if self._edge is not None:
            self._model.add_edge(self._edge)
        return self._edge


class DeleteEdgeCommand(ProcessModelCommand, UndoableCommand):
    edge_id: process_model.EdgeId
    _edge: process_model.Edge = pydantic.PrivateAttr()

    def execute(self) -> None:
        self._edge = self._model.get_edge(self.edge_id)
        self._model.delete_edge(self.edge_id)

    def undo(self) -> None:
        self._model.add_edge(self._edge)


class UpdateInspectablesCommand(ProcessModelCommand, UndoableCommand):
    node_id: process_model.NodeId
    node_kwargs: dict[str, Any] = pydantic.Field(default_factory=dict)
    _old_kwargs: dict[str, Any] = pydantic.PrivateAttr(default_factory=dict)

    def execute(self) -> None:
        node = self._model.get_node(self.node_id)
        node: process_model.Node = self._model.get_node(self.node_id)

        for key, value in self.node_kwargs.items():
            inspectable = node.get_inspectable(key)
            if inspectable is not None:
                self._old_kwargs[key] = inspectable.value
                node.set_inspectable(key, value)

    def undo(self) -> None:
        node: process_model.Node = self._model.get_node(self.node_id)

        for key, value in self._old_kwargs.items():
            node.set_inspectable(key, value)


class ClearModelCommand(ProcessModelCommand, UndoableCommand):
    _nodes = pydantic.PrivateAttr(default_factory=list)
    _edges = pydantic.PrivateAttr(default_factory=list)

    def execute(self) -> None:
        self._nodes = self._model.get_nodes()
        self._edges = self._model.get_edges()
        self._model.clear()

    def undo(self) -> None:
        for node in self._nodes:
            self._model.add_node(node)
        for edge in self._edges:
            self._model.add_edge(edge)
