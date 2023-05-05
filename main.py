import enum
import random
from dataclasses import dataclass

import flask
from flask import Flask, jsonify, render_template, request

from http.server import HTTPServer, BaseHTTPRequestHandler
import logging, ngrok


app = Flask(__name__)


logging.basicConfig(level=logging.INFO)
ngrok.listen(app)


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


@app.route("/", methods=["GET", "POST"])
def index() -> flask.Response:
    global nodes, edges

    return flask.make_response(
        render_template("index.html", nodes=nodes.values(), edges=edges.values())
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
    app.run(debug=True, host="0.0.0.0")
