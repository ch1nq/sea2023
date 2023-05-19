import logging
import os
import pathlib

import flask
import flask.wrappers

from src import process_model
from src import ui


app = flask.Flask(__name__, template_folder="../templates", static_folder="../static")
open_models: dict[str, process_model.ProcessModel] = {}


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


def get_model(path: str | None) -> process_model.ProcessModel:
    """Get mutable model from file."""
    global open_models

    if path is None:
        raise ValueError("Path is None")

    with open(path, "r") as f:
        model_type = get_model_type(pathlib.Path(path))
        model_class = process_model.model_type_to_class(model_type)

    try:
        model = open_models.get(path, model_class.load(pathlib.Path(path)))
    except FileNotFoundError as error:
        logging.error(f"File not found {path}")
        raise error

    return model


@app.route("/new_model", methods=["POST"])
def new_model() -> flask.Response:
    global open_models

    model_id = "models/" + flask.request.form["model_id"]
    model_type = process_model.ProcessModelType(flask.request.form["model_type"])
    model_factory = process_model.model_type_to_class(model_type)
    model = model_factory(id=model_id, model_type=model_type)

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
    global open_models

    model_id = flask.request.args["model_id"]
    model = get_model(model_id)
    open_models[model_id] = model
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
        )
    )


@app.route("/get_model_id", methods=["POST"])
def get_model_id() -> flask.Response:
    global open_models

    model = get_model(flask.request.form["model_id"])
    return flask.jsonify(model.id)


@app.route("/create", methods=["POST"])
def create_node() -> flask.Response:
    global open_models

    model_id = flask.request.form["model_id"]
    x = flask.request.form.get("x", type=float)
    y = flask.request.form.get("y", type=float)
    node_type = process_model.NodeType(flask.request.form["node_type"])

    model = get_model(model_id)
    match model.model_type:
        case process_model.ProcessModelType.PETRI_NET:
            node_kwargs = dict(node_type=node_type)
        case _:
            node_kwargs = {}
    node = model.add_node(x, y, **node_kwargs)
    logging.info(f"Created node {node}")
    return flask.jsonify(node.dict())


@app.route("/delete", methods=["POST"])
def delete_node() -> flask.Response:
    global open_models

    node_id = flask.request.form.get("node_id", type=int)

    if node_id is None:
        raise ValueError("Node id is None")

    model = get_model(flask.request.form["model_id"])
    model.delete_node(process_model.NodeId(node_id))
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

    model = get_model(path)
    model.move_node(process_model.NodeId(node_id), x, y)
    return flask.make_response("", 200)


@app.route("/connect", methods=["POST"])
def connect() -> flask.Response:
    global open_models

    path = flask.request.form["model_id"]
    start_node_id = flask.request.form.get("start_node_id", type=int)
    end_node_id = flask.request.form.get("end_node_id", type=int)

    if start_node_id is None or end_node_id is None:
        raise ValueError("Node id is None")

    model = get_model(path)
    edge = model.add_edge(process_model.NodeId(start_node_id), process_model.NodeId(end_node_id))
    if edge is None:
        logging.info("Invalid connection")
        return flask.make_response("", 204)

    logging.info(f"Connecting {start_node_id} to {end_node_id}")
    return flask.jsonify(edge.dict())


@app.route("/nodes", methods=["GET"])
def get_nodes() -> flask.Response:
    global open_models

    model = get_model(flask.request.args.get("model_id"))
    return flask.jsonify([node.dict() for node in model.get_nodes()])


@app.route("/edges", methods=["GET"])
def get_edges() -> flask.Response:
    global open_models

    model = get_model(flask.request.args.get("model_id"))
    return flask.jsonify([edge.dict() for edge in model.get_edges()])


@app.route("/clear", methods=["POST"])
def clear() -> flask.Response:
    global open_models

    model = get_model(flask.request.form["model_id"])
    model.clear()
    return flask.make_response("", 200)


@app.route("/save", methods=["POST"])
def save() -> flask.Response:
    global open_models

    model_id = flask.request.form["model_id"]
    model = get_model(model_id)
    model.save(pathlib.Path(model_id))
    return flask.make_response("", 200)


@app.route("/inspect", methods=["GET"])
def inspector_content() -> flask.Response:
    model_id = flask.request.args.get("model_id")
    model = get_model(model_id)

    node_id = flask.request.args.get("node_id", type=int)
    if node_id is None:
        return flask.make_response("", 204)

    node = model.get_node(process_model.NodeId(node_id))
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
    model = get_model(flask.request.form["model_id"])
    node_id = flask.request.form.get("node_id", type=int)

    if node_id is None:
        return flask.make_response("", 204)

    node = model.get_node(process_model.NodeId(node_id))
    if not node:
        return flask.make_response("", 204)

    for key in [inspectable.name for inspectable in node.get_inspectables()]:
        if key in flask.request.form:
            node.set_inspectable(key, flask.request.form[key])

    return flask.make_response("", 200)


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> flask.Response:
    return flask.make_response("", 204)


@app.errorhandler(404)
def page_not_found(error: Exception | None = None) -> flask.Response:
    print(error)
    return flask.make_response(flask.render_template("pages/404_page.html", error=error), 404)
