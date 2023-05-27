import datetime
import logging
import os
import pathlib
import random

import flask
import flask.wrappers

from src import editor
from src import process_model
from src import ui
from src import simulation_engine


app = flask.Flask(__name__, template_folder="../templates", static_folder="../static")
open_models: dict[str, editor.ProcessModelController] = {}
simulator = simulation_engine.Simulator()

for _ in range(10):
    simulation = simulator.queue_simulation(
        model_id=process_model.ModelId("models/petri_net_1"),
        simulation_parameters=simulation_engine.SimulationParameters(),
    )
    if random.random() < 0.3:
        simulation = simulator.start_simulation(simulation)
        if random.random() < 0.5:
            simulator.finish_simulation(simulation, simulation_engine.SimulationResult())


def get_model_type(path: pathlib.Path) -> process_model.ProcessModelType:
    return process_model.ProcessModelBase.parse_file(str(path)).model_type


def get_file_tree(root_dir: pathlib.Path) -> dict[str, dict[str, bool]]:
    file_tree = {}
    for root, _dirs, files in os.walk(root_dir):
        current_level = file_tree
        path = root.split(os.sep)
        for dir in path:
            if dir not in current_level:
                current_level[dir] = {}
            current_level = current_level[dir]
        for file in files:
            if file.endswith(".pm"):
                model_type = get_model_type(pathlib.Path(root) / file)
                current_level[file] = model_type.name.replace("_", " ").capitalize()
    return file_tree


def get_model_controller(path: str | None) -> editor.ProcessModelController:
    """Get mutable model from file."""
    global open_models

    if path is None:
        raise ValueError("Path is None")

    with open(path, "r") as f:
        model_type = get_model_type(pathlib.Path(path))
        model_class = process_model.model_type_to_class(model_type)

    try:
        model_controller = open_models.get(path, editor.ProcessModelController(model_class.load(pathlib.Path(path))))
    except FileNotFoundError as error:
        logging.error(f"File not found {path}")
        raise error

    return model_controller


@app.route("/new_model", methods=["POST"])
def new_model() -> flask.Response:
    global open_models

    model_id = "models/" + flask.request.form["model_id"]
    model_type = process_model.ProcessModelType(flask.request.form["model_type"])
    model_factory = process_model.model_type_to_class(model_type)
    model = model_factory(id=process_model.ModelId(model_id), model_type=model_type)

    model.save(pathlib.Path(model_id))
    open_models[model_id] = model

    return flask.redirect(f"/edit?model_id={model_id}")  # type: ignore


@app.route("/", methods=["GET"])
def index() -> flask.Response:
    return flask.make_response(
        flask.render_template(
            "pages/welcome_page.html",
            file_tree=get_file_tree(pathlib.Path("models")),
            model_types=[
                (model_type.name.replace("_", " "), model_type.value) for model_type in process_model.ProcessModelType
            ],
        )
    )


@app.route("/edit", methods=["GET"])
def edit_model() -> flask.Response:
    global open_models, simulation_queue

    model_id = flask.request.args["model_id"]
    model_controller = get_model_controller(model_id)
    open_models[model_id] = model_controller
    model = model_controller.model
    return flask.make_response(
        flask.render_template(
            "pages/editor_page.html",
            nodes=model.get_nodes(),
            edges=model.get_edges(),
            file_tree=get_file_tree(pathlib.Path("models")),
            current_model_id=model_id,
            properties=[],
            model_type=model.model_type.name.replace("_", " "),
            toolbar_buttons=ui.get_toolbar_buttons(model.model_type),
            model_types=[
                (model_type.name.replace("_", " "), model_type.value) for model_type in process_model.ProcessModelType
            ],
            simulation_queue=map(
                ui.SimulationQueueListItem.from_simulation,
                simulator.finished_simulations + simulator.running_simulations + simulator.queued_simulations,
            ),
        )
    )


@app.route("/get_model_id", methods=["POST"])
def get_model_id() -> flask.Response:
    global open_models

    model_contoller = get_model_controller(flask.request.form["model_id"])
    return flask.jsonify(model_contoller.model.id)


@app.route("/create", methods=["POST"])
def create_node() -> flask.Response:
    global open_models

    model_id = flask.request.form["model_id"]
    x = flask.request.form.get("x", type=float)
    y = flask.request.form.get("y", type=float)

    model_controller = get_model_controller(model_id)
    match model_controller.model.model_type:
        case process_model.ProcessModelType.PETRI_NET:
            node_type = process_model.petri_net.NodeType(flask.request.form["node_type"])
            node_kwargs = dict(node_type=node_type)
        case _:
            node_kwargs = {}
    node: process_model.Node = model_controller.execute(editor.CreateNodeCommand(x=x, y=y, node_kwargs=node_kwargs))
    logging.info(f"Created node {node}")
    return flask.jsonify(node.dict())


@app.route("/delete", methods=["POST"])
def delete_node() -> flask.Response:
    global open_models

    node_id = flask.request.form.get("node_id", type=int)

    if node_id is None:
        raise ValueError("Node id is None")

    model_controller = get_model_controller(flask.request.form["model_id"])
    model_controller.execute(editor.DeleteNodeCommand(node_id=process_model.NodeId(node_id)))
    return flask.make_response("", 200)


@app.route("/move", methods=["POST"])
def move_node() -> flask.Response:
    global open_models

    path = flask.request.form["model_id"]
    node_id = flask.request.form.get("node_id", type=int)
    x = flask.request.form.get("x", type=float)
    y = flask.request.form.get("y", type=float)

    if node_id is None:
        raise ValueError("Node id is None")

    model_controller = get_model_controller(path)
    model_controller.execute(editor.MoveNodeCommand(node_id=process_model.NodeId(node_id), x=x, y=y))
    return flask.make_response("", 200)


@app.route("/connect", methods=["POST"])
def connect() -> flask.Response:
    global open_models

    path = flask.request.form["model_id"]
    start_node_id = flask.request.form.get("start_node_id", type=int)
    end_node_id = flask.request.form.get("end_node_id", type=int)

    if start_node_id is None or end_node_id is None:
        raise ValueError("Node id is None")

    model_controller = get_model_controller(path)
    edge = model_controller.execute(
        editor.CreateEdgeCommand(
            start_node_id=process_model.NodeId(start_node_id), end_node_id=process_model.NodeId(end_node_id)
        )
    )
    if edge is None:
        logging.info("Invalid connection")
        return flask.make_response("", 204)

    logging.info(f"Connecting {start_node_id} to {end_node_id}")
    return flask.jsonify(edge.dict())


@app.route("/nodes", methods=["GET"])
def get_nodes() -> flask.Response:
    global open_models

    model_controller = get_model_controller(flask.request.args.get("model_id"))
    return flask.jsonify([node.dict() for node in model_controller.model.get_nodes()])


@app.route("/edges", methods=["GET"])
def get_edges() -> flask.Response:
    global open_models

    model_controller = get_model_controller(flask.request.args.get("model_id"))
    return flask.jsonify([edge.dict() for edge in model_controller.model.get_edges()])


@app.route("/clear", methods=["POST"])
def clear() -> flask.Response:
    global open_models

    model_controller = get_model_controller(flask.request.form["model_id"])
    model_controller.execute(editor.ClearModelCommand())
    return flask.make_response("", 200)


@app.route("/save", methods=["POST"])
def save() -> flask.Response:
    global open_models

    model_id = flask.request.form["model_id"]
    model_controller = get_model_controller(model_id)
    model_controller.execute(editor.SaveModelCommand(path=pathlib.Path(model_id)))
    return flask.make_response("", 200)


@app.route("/inspect", methods=["GET"])
def inspector_content() -> flask.Response:
    model_id = flask.request.args.get("model_id")
    model_controller = get_model_controller(model_id)

    node_id = flask.request.args.get("node_id", type=int)
    if node_id is None:
        return flask.make_response("", 204)

    node = model_controller.model.get_node(process_model.NodeId(node_id))
    if node is None:
        return flask.make_response("", 204)

    return flask.make_response(
        flask.render_template(
            "inspector_content.html",
            properties=node.get_inspectables(),
            node_id=node_id,
            model_id=model_id,
        )
    )


@app.route("/update_properties", methods=["POST"])
def update_properties() -> flask.Response:
    model_controller = get_model_controller(flask.request.form["model_id"])
    node_id = process_model.NodeId(flask.request.form.get("node_id", type=int))

    if node_id is None or model_controller.model.get_node(process_model.NodeId(node_id)) is None:
        return flask.make_response("", 204)
    else:
        model_controller.execute(editor.UpdateInspectablesCommand(node_id=node_id, node_kwargs=flask.request.form))
        return flask.make_response("", 200)


@app.route("/undo", methods=["POST"])
def undo() -> flask.Response:
    model_controller = get_model_controller(flask.request.form["model_id"])
    model_controller.undo()
    can_undo = model_controller.history.can_undo
    return flask.make_response(str(can_undo).lower(), 200)


@app.route("/redo", methods=["POST"])
def redo() -> flask.Response:
    model_controller = get_model_controller(flask.request.form["model_id"])
    model_controller.redo()
    can_redo = model_controller.history.can_redo
    return flask.make_response(str(can_redo).lower(), 200)


@app.route("/can_undo_redo", methods=["GET"])
def can_undo_and_redo() -> flask.Response:
    model_controller = get_model_controller(flask.request.args.get("model_id"))
    can_undo = model_controller.history.can_undo
    can_redo = model_controller.history.can_redo
    return flask.jsonify({"can_undo": can_undo, "can_redo": can_redo})


@app.route("/queue_simulation", methods=["POST"])
def queue_simulation() -> flask.Response:
    model_id = flask.request.form["model_id"]
    model_controller = get_model_controller(model_id)
    simulator.queue_simulation(
        process_model.ModelId(model_controller.model.id), simulation_engine.SimulationParameters()
    )
    return flask.make_response("", 200)


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> flask.Response:
    return flask.make_response("", 204)


@app.errorhandler(404)
def page_not_found(error: Exception | None = None) -> flask.Response:
    print(error)
    return flask.make_response(flask.render_template("pages/404_page.html", error=error), 404)
