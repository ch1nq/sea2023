import enum
import logging
import os
import random
from dataclasses import dataclass

import flask
import ngrok
from flask import Flask, jsonify, render_template, request


logging.basicConfig(level=logging.INFO)
# tunnel = ngrok.werkzeug_develop()
app = Flask(__name__)

MAX_NODES = 10000


@dataclass(order=True, frozen=True)
class NodeId:
    id: int


@dataclass(eq=True, order=True)
class Point:
    x: float
    y: float


class NodeType(str, enum.Enum):
    PLACE = "place"
    TRANSITION = "transition"


@dataclass(eq=True, order=True)
class Node:
    id: NodeId
    node_type: NodeType
    position: Point


@dataclass(eq=True, order=True)
class Edge:
    start_node_id: NodeId
    end_node_id: NodeId
    start_position: Point
    end_position: Point


@dataclass(eq=True, order=True)
class Graph:
    nodes: dict[NodeId, Node]
    edges: dict[tuple[NodeId, NodeId], Edge]


nodes: dict[NodeId, Node] = {}
edges: dict[tuple[NodeId, NodeId], Edge] = {}


def new_id() -> NodeId:
    id = random.randint(0, MAX_NODES)
    while id in nodes.keys():
        id = random.randint(0, MAX_NODES)
    return NodeId(id)


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
            current_level[file] = True
    return file_tree


@app.route("/", methods=["GET", "POST"])
def index() -> flask.Response:
    global nodes, edges

    file_tree = get_file_tree("models")

    return flask.make_response(
        render_template(
            "index.html",
            nodes=nodes.values(),
            edges=edges.values(),
            file_tree=file_tree,
        )
    )


@app.route("/create", methods=["POST"])
def create_node() -> flask.Response:
    global nodes

    x = float(request.form["x"])
    y = float(request.form["y"])
    node_type = NodeType(request.form["node_type"])
    node_id = new_id()
    node = Node(node_id, node_type, Point(x, y))
    nodes[node_id] = node
    print(node)
    return jsonify(node)


@app.route("/delete", methods=["POST"])
def delete_node() -> flask.Response:
    global nodes, edges

    node_id = NodeId(float(request.form["node_id"]))
    nodes.pop(node_id)
    # nodes = [node for node in nodes if node["id"] != node_id]
    for other_node in nodes.keys():
        edges.pop((node_id, other_node), None)
        edges.pop((other_node, node_id), None)
    return flask.make_response("", 200)


@app.route("/move", methods=["POST"])
def move_node() -> flask.Response:
    global nodes

    node_id = NodeId(float(request.form["node_id"]))
    x = float(request.form["x"])
    y = float(request.form["y"])
    nodes[node_id].position = Point(x, y)

    for (edge_start_id, edge_end_id), edge in edges.items():
        if node_id == edge_start_id:
            edge.start_position = Point(x, y)
        elif node_id == edge_end_id:
            edge.end_position = Point(x, y)
    return flask.make_response("", 204)


@app.route("/connect", methods=["POST"])
def connect() -> flask.Response:
    global edges

    start_node_id = NodeId(float(request.form["start_node_id"]))
    end_node_id = NodeId(float(request.form["end_node_id"]))
    edge = Edge(
        start_node_id,
        end_node_id,
        Point(nodes[start_node_id].position.x, nodes[start_node_id].position.y),
        Point(nodes[end_node_id].position.x, nodes[end_node_id].position.y),
    )
    edges[(start_node_id, end_node_id)] = edge
    return jsonify(edge)


@app.route("/nodes", methods=["GET"])
def get_nodes() -> flask.Response:
    global nodes

    return jsonify(list(nodes.values()))


@app.route("/edges", methods=["GET"])
def get_edges() -> flask.Response:
    global edges

    return jsonify(list(edges.values()))


@app.route("/clear", methods=["POST"])
def clear() -> flask.Response:
    global nodes, edges

    nodes = {}
    edges = {}
    return flask.make_response("", 200)


@app.route("/favicon.ico", methods=["GET"])
def favicon() -> flask.Response:
    return flask.make_response("", 204)


if __name__ == "__main__":
    app.run(debug=True)
