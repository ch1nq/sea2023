from flask import Flask, jsonify, render_template, request
import random

MAX_NODES = 10000

app = Flask(__name__)

nodes = {}
edges = {}


def new_id() -> int:
    id = random.randint(0, MAX_NODES)
    while id in nodes.keys():
        id = random.randint(0, MAX_NODES)
    return id


@app.route("/", methods=["GET", "POST"])
def index():
    global nodes, edges

    return render_template("index.html", nodes=nodes.values(), edges=edges.values())


@app.route("/create", methods=["POST"])
def create_node():
    global nodes

    x = int(request.form["x"])
    y = int(request.form["y"])
    node_id = new_id()
    node = {"id": node_id, "x": x, "y": y}
    nodes[node_id] = node
    return jsonify(node)


@app.route("/delete", methods=["POST"])
def delete_node():
    global nodes, edges

    node_id = int(request.form["node_id"])
    nodes.pop(node_id)
    # nodes = [node for node in nodes if node["id"] != node_id]
    for other_node in nodes.keys():
        edges.pop((node_id, other_node), None)
        edges.pop((other_node, node_id), None)
    return "", 200


@app.route("/move", methods=["POST"])
def move_node():
    global nodes

    node_id = int(request.form["node_id"])
    x = int(request.form["x"])
    y = int(request.form["y"])
    node = {"id": node_id, "x": x, "y": y}
    nodes[node_id] = node
    for (edge_start_id, edge_end_id), edge in edges.items():
        if node_id == edge_start_id:
            edge["x1"] = x
            edge["y1"] = y
        elif node_id == edge_end_id:
            edge["x2"] = x
            edge["y2"] = y
    return "", 204


@app.route("/connect", methods=["POST"])
def connect():
    global edges

    start_node_id = int(request.form["start_node_id"])
    end_node_id = int(request.form["end_node_id"])
    edge = {
        "start_node_id": start_node_id,
        "end_node_id": end_node_id,
        "x1": nodes[start_node_id]["x"],
        "y1": nodes[start_node_id]["y"],
        "x2": nodes[end_node_id]["x"],
        "y2": nodes[end_node_id]["y"],
    }
    edges[(start_node_id, end_node_id)] = edge
    return jsonify(edge)


@app.route("/nodes", methods=["GET"])
def get_nodes():
    global nodes

    return jsonify(list(nodes.values()))


@app.route("/edges", methods=["GET"])
def get_edges():
    global edges

    return jsonify(list(edges.values()))


if __name__ == "__main__":
    app.run(debug=True)
