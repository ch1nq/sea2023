import logging
import os

import flask

from flask import Flask, jsonify, render_template, request
from src import process_model
from src import ui


app = Flask(__name__, template_folder="../templates", static_folder="../static")
open_models: dict[str, process_model.ProcessModel] = {}


def get_model_type(path: os.PathLike) -> process_model.ProcessModelType:
    return process_model.ProcessModelBase.parse_file(str(path)).model_type


def get_file_tree(root_dir: os.PathLike) -> dict[str, dict[str, bool]]:
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
                model_type = get_model_type(os.path.join(root, file))
                current_level[file] = model_type.name.replace("_", " ").capitalize()
    return file_tree


def get_model(path: os.PathLike | None) -> process_model.ProcessModel:
    """Get mutable model from file."""
    global open_models

    if path is None:
        raise ValueError("Path is None")

    with open(path, "r") as f:
        model_type = get_model_type(path)
        model_class = process_model.model_type_to_class(model_type)

    try:
        model = open_models.get(path, model_class.load(path))
    except FileNotFoundError as error:
        logging.error(f"File not found {path}")
        raise error

    return model


@app.route("/new_model", methods=["POST"])
def new_model() -> flask.Response:
    global open_models

    model_id = "models/" + request.form["model_id"]
    model_type = process_model.ProcessModelType(request.form["model_type"])
    model_factory = process_model.model_type_to_class(model_type)
    model = model_factory(id=model_id)

    model.save(model_id)
    open_models[model_id] = model

    return flask.redirect(f"/edit?model_id={model_id}")


@app.route("/", methods=["GET"])
def index() -> flask.Response:
    return flask.make_response(
        render_template(
            "pages/welcome_page.html",
            file_tree=get_file_tree("models"),
            model_types=[
                (model_type.name.replace("_", " "), model_type.value) for model_type in process_model.ProcessModelType
            ],
        )
    )


@app.route("/edit", methods=["GET"])
def edit_model() -> flask.Response:
    global open_models

    model_id = request.args["model_id"]
    model = get_model(model_id)
    open_models[model_id] = model
    return flask.make_response(
        render_template(
            "pages/editor_page.html",
            nodes=model.get_nodes(),
            edges=model.get_edges(),
            file_tree=get_file_tree("models"),
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

    model = get_model(request.form["model_id"])
    return jsonify(model.id)


@app.route("/create", methods=["POST"])
def create_node() -> flask.Response:
    global open_models

    model_id = request.form["model_id"]
    x = float(request.form["x"])
    y = float(request.form["y"])
    node_type = process_model.NodeType(request.form["node_type"])

    model = get_model(model_id)
    match model.model_type:
        case process_model.ProcessModelType.PETRI_NET:
            node_kwargs = dict(node_type=node_type)
        case _:
            node_kwargs = {}
    node = model.add_node(x, y, **node_kwargs)
    logging.info(f"Created node {node}")
    return jsonify(node.dict())


@app.route("/delete", methods=["POST"])
def delete_node() -> flask.Response:
    global open_models

    node_id = request.form.get("node_id", type=int)

    model = get_model(request.form["model_id"])
    model.delete_node(node_id)
    return flask.make_response("", 200)


@app.route("/move", methods=["POST"])
def move_node() -> flask.Response:
    global open_models

    path = request.form["model_id"]
    node_id = request.form.get("node_id", type=int)
    x = float(request.form["x"])
    y = float(request.form["y"])

    model = get_model(path)
    model.move_node(node_id, x, y)
    return flask.make_response("", 200)


@app.route("/connect", methods=["POST"])
def connect() -> flask.Response:
    global open_models

    path = request.form["model_id"]
    start_node_id = request.form.get("start_node_id", type=int)
    end_node_id = request.form.get("end_node_id", type=int)

    model = get_model(path)
    edge = model.add_edge(start_node_id, end_node_id)
    if edge is None:
        logging.info("Invalid connection")
        return flask.make_response("", 204)

    logging.info(f"Connecting {start_node_id} to {end_node_id}")
    return jsonify(edge.dict())


@app.route("/nodes", methods=["GET"])
def get_nodes() -> flask.Response:
    global open_models

    model = get_model(request.args.get("model_id"))
    return jsonify([node.dict() for node in model.get_nodes()])


@app.route("/edges", methods=["GET"])
def get_edges() -> flask.Response:
    global open_models

    model = get_model(request.args.get("model_id"))
    return jsonify([edge.dict() for edge in model.get_edges()])


@app.route("/clear", methods=["POST"])
def clear() -> flask.Response:
    global open_models

    model = get_model(request.form["model_id"])
    model.clear()
    return flask.make_response("", 200)


@app.route("/save", methods=["POST"])
def save() -> flask.Response:
    global open_models

    model_id = request.form["model_id"]
    model = get_model(model_id)
    model.save(model_id)
    return flask.make_response("", 200)


@app.route("/inspect", methods=["GET"])
def inspector_content() -> flask.Response:
    model_id = request.args.get("model_id")
    model = get_model(model_id)
    node_id = request.args.get("node_id", type=int)
    node = model.get_node(node_id)
    return flask.make_response(
        render_template(
            "inspector_content.html",
            properties=node.get_inspectables(),
            node_id=node_id,
            model_id=model_id,
        )
    )


@app.route("/update_properties", methods=["POST"])
def update_properties() -> flask.Response:
    model = get_model(request.form["model_id"])
    node_id = request.form.get("node_id", type=int)

    node = model.get_node(node_id)
    for key in [inspectable.name for inspectable in node.get_inspectables()]:
        if key in request.form:
            node.set_inspectable(key, request.form[key])

    return flask.make_response("", 200)


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> flask.Response:
    return flask.make_response("", 204)


@app.errorhandler(404)
def page_not_found(error: Exception | None = None) -> flask.Response:
    print(error)
    return flask.make_response(flask.render_template("pages/404_page.html", error=error), 404)
