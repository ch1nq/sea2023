from flask import Flask, jsonify, render_template, request
import random
from dataclasses import dataclass

import flask

MAX_NODES = 10000

app = Flask(__name__)


@dataclass(order=True, frozen=True)
class NodeId:
    id: int


@dataclass(eq=True, order=True)
class Point:
    x: int
    y: int


@dataclass(eq=True, order=True)
class Node:
    id: NodeId
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

    x = int(request.form["x"])
    y = int(request.form["y"])
    node_id = new_id()
    node = Node(node_id, Point(x, y))
    nodes[node_id] = node
    print(node)
    return jsonify(node)


@app.route("/delete", methods=["POST"])
def delete_node() -> flask.Response:
    global nodes, edges

    node_id = NodeId(int(request.form["node_id"]))
    nodes.pop(node_id)
    # nodes = [node for node in nodes if node["id"] != node_id]
    for other_node in nodes.keys():
        edges.pop((node_id, other_node), None)
        edges.pop((other_node, node_id), None)
    return flask.make_response("", 200)


@app.route("/move", methods=["POST"])
def move_node() -> flask.Response:
    global nodes

    node_id = NodeId(int(request.form["node_id"]))
    x = int(request.form["x"])
    y = int(request.form["y"])
    node = Node(node_id, Point(x, y))
    nodes[node_id] = node
    for (edge_start_id, edge_end_id), edge in edges.items():
        if node_id == edge_start_id:
            edge.start_position = Point(x, y)
        elif node_id == edge_end_id:
            edge.end_position = Point(x, y)
    return flask.make_response("", 204)


@app.route("/connect", methods=["POST"])
def connect() -> flask.Response:
    global edges

    start_node_id = NodeId(int(request.form["start_node_id"]))
    end_node_id = NodeId(int(request.form["end_node_id"]))
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


if __name__ == "__main__":
    app.run(debug=True)
