import logging
import os

import flask
import ngrok

from flask import Flask, jsonify, render_template, request
import pydantic
import process_model


logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

open_models: dict[str, process_model.ProcessModel] = {}


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
                current_level[file] = True
    return file_tree


def get_model(path: os.PathLike | None) -> process_model.ProcessModel | None:
    """Get mutable model from file."""
    global open_models

    if path is None:
        return None

    try:
        model = open_models.get(path, process_model.ProcessModel.load(path))
    except FileNotFoundError:
        logging.error(f"File not found {path}")
        return None
    except pydantic.error_wrappers.ValidationError:
        logging.error(f"Invalid model file {path}")
        return None

    return model


@app.route("/new_model", methods=["POST"])
def new_model() -> flask.Response:
    global open_models

    model_id = request.form["model_id"]
    model = process_model.ProcessModel(id=model_id)
    model.save(model_id)
    open_models[model_id] = model

    return flask.redirect(f"/edit?model_id={model_id}")


@app.route("/", methods=["GET"])
def index() -> flask.Response:
    return flask.redirect("/edit")


@app.route("/edit", methods=["GET"])
def edit_model() -> flask.Response:
    global open_models

    model_id = request.args.get("model_id", None)
    match get_model(model_id):
        case None:
            return flask.make_response(
                render_template(
                    "index.html",
                    nodes=[],
                    edges=[],
                    file_tree=get_file_tree("models"),
                    current_model_id="",
                )
            )
        case model:
            open_models[model_id] = model
            return flask.make_response(
                render_template(
                    "index.html",
                    nodes=model.get_nodes(),
                    edges=model.get_edges(),
                    file_tree=get_file_tree("models"),
                    current_model_id=model_id,
                )
            )


@app.route("/get_model_id", methods=["POST"])
def get_model_id() -> flask.Response:
    global open_models

    match get_model(request.form["model_id"]):
        case None:
            return flask.make_response("", 404)
        case model:
            return jsonify(model.id)


@app.route("/create", methods=["POST"])
def create_node() -> flask.Response:
    global open_models

    model_id = request.form["model_id"]
    x = float(request.form["x"])
    y = float(request.form["y"])
    node_type = process_model.NodeType(request.form["node_type"])

    match get_model(model_id):
        case None:
            return flask.make_response("", 404)
        case model:
            node = model.add_node(node_type, x, y)
            logging.info(f"Created node {node}")
            return jsonify(node)


@app.route("/delete", methods=["POST"])
def delete_node() -> flask.Response:
    global open_models

    node_id = request.form.get("node_id", type=int)

    match get_model(request.form["model_id"]):
        case None:
            return flask.make_response("", 404)
        case model:
            model.delete_node(node_id)
            return flask.make_response("", 200)


@app.route("/move", methods=["POST"])
def move_node() -> flask.Response:
    global open_models

    path = request.form["model_id"]
    node_id = request.form.get("node_id", type=int)
    x = float(request.form["x"])
    y = float(request.form["y"])

    match get_model(path):
        case None:
            return flask.make_response("", 404)
        case model:
            model.move_node(node_id, x, y)
            return flask.make_response("", 200)


@app.route("/connect", methods=["POST"])
def connect() -> flask.Response:
    global open_models

    path = request.form["model_id"]
    start_node_id = request.form.get("start_node_id", type=int)
    end_node_id = request.form.get("end_node_id", type=int)

    match get_model(path):
        case None:
            return flask.make_response("", 404)
        case model:
            edge = model.connect(start_node_id, end_node_id)
            if edge is None:
                logging.info("Invalid connection")
                return flask.make_response("", 204)

            logging.info(f"Connecting {start_node_id} to {end_node_id}")
            return jsonify(edge)


@app.route("/nodes", methods=["GET"])
def get_nodes() -> flask.Response:
    global open_models

    match get_model(request.args.get("model_id")):
        case None:
            return flask.make_response("", 404)
        case model:
            return jsonify(model.get_nodes())


@app.route("/edges", methods=["GET"])
def get_edges() -> flask.Response:
    global open_models

    match get_model(request.args.get("model_id")):
        case None:
            return flask.make_response("", 404)
        case model:
            return jsonify(model.get_edges())


@app.route("/clear", methods=["POST"])
def clear() -> flask.Response:
    global open_models

    match get_model(request.form["model_id"]):
        case None:
            return flask.make_response("", 404)
        case model:
            model.clear()
            return flask.make_response("", 200)


@app.route("/save", methods=["POST"])
def save() -> flask.Response:
    global open_models

    model_id = request.form["model_id"]
    match get_model(model_id):
        case None:
            return flask.make_response("", 404)
        case model:
            model.save(model_id)
            return flask.make_response("", 200)


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> flask.Response:
    return flask.make_response("", 204)


if __name__ == "__main__":
    if os.environ.get("NGROK_AUTH_TOKEN"):
        tunnel = ngrok.werkzeug_develop()
    app.run(debug=True)
