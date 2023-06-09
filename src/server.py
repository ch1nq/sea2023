import os
import pathlib
import random

import flask
import flask.wrappers

from src import process_model
from src import ui
from src import simulation_engine


app = flask.Flask(__name__, template_folder="../templates", static_folder="../static")
app.config.from_prefixed_env()
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
                model_type = process_model.ProcessModelType.from_path(pathlib.Path(root) / file)
                current_level[file] = model_type.name.replace("_", " ").capitalize()
    return file_tree


@app.route("/new_model", methods=["POST"])
def new_model() -> flask.Response:
    model_id = "data/models/" + flask.request.form["model_id"]
    model_type = process_model.ProcessModelType(flask.request.form["model_type"])
    model_factory = process_model.model_type_to_class(model_type)
    model = model_factory(id=process_model.ModelId(model_id), model_type=model_type)
    model.save(pathlib.Path(model_id))

    return flask.redirect(f"/edit?model_id={model_id}")  # type: ignore


@app.route("/", methods=["GET"])
def index() -> flask.Response:
    return flask.make_response(
        flask.render_template(
            "pages/welcome_page.html",
            file_tree=get_file_tree(pathlib.Path("data/models")),
            model_types=[
                (model_type.name.replace("_", " "), model_type.value) for model_type in process_model.ProcessModelType
            ],
        )
    )


@app.route("/edit", methods=["GET"])
def edit_model() -> flask.Response:
    global simulation_queue

    model_id = flask.request.args["model_id"]
    model_type = process_model.ProcessModelType.from_path(pathlib.Path(model_id))

    return flask.make_response(
        flask.render_template(
            "pages/editor_page.html",
            file_tree=get_file_tree(pathlib.Path("data/models")),
            current_model_id=model_id,
            model_type=model_type.name.replace("_", " "),
            toolbar_buttons=ui.get_toolbar_buttons(model_type),
            model_types=[
                (model_type.name.replace("_", " "), model_type.value) for model_type in process_model.ProcessModelType
            ],
            simulation_queue=map(
                ui.SimulationQueueListItem.from_simulation,
                simulator.finished_simulations + simulator.running_simulations + simulator.queued_simulations,
            ),
        )
    )


@app.route("/queue_simulation", methods=["POST"])
def queue_simulation() -> flask.Response:
    model_id = flask.request.form["model_id"]
    simulator.queue_simulation(process_model.ModelId(model_id), simulation_engine.SimulationParameters())
    return flask.make_response("", 200)


@app.route("/healthz", methods=["GET"])
def healthz() -> flask.Response:
    return flask.make_response("OK\n", 200)


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> flask.Response:
    return flask.make_response("", 204)


@app.errorhandler(404)
def page_not_found(error: Exception | None = None) -> flask.Response:
    print(error)
    return flask.make_response(flask.render_template("pages/404_page.html", error=error), 404)
