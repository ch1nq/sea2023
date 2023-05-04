from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

nodes = []
edges = []


@app.route("/", methods=["GET", "POST"])
def index():
    global nodes, edges

    return render_template("index.html", nodes=nodes, edges=edges)


@app.route("/create", methods=["POST"])
def create_node():
    global nodes

    x = int(request.form["x"])
    y = int(request.form["y"])
    node_id = len(nodes)
    node = {"id": node_id, "x": x, "y": y}
    nodes.append(node)
    return jsonify(node)


@app.route("/move", methods=["POST"])
def move_node():
    global nodes

    node_id = int(request.form["node_id"])
    x = int(request.form["x"])
    y = int(request.form["y"])
    node = {"id": node_id, "x": x, "y": y}
    nodes[node_id] = node
    for edge in edges:
        if node_id in [edge["start_node_id"], edge["end_node_id"]]:
            if edge["start_node_id"] == node_id:
                edge["x1"] = x
                edge["y1"] = y
            else:
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
    edges.append(edge)
    return jsonify(edge)


@app.route("/nodes", methods=["GET"])
def get_nodes():
    global nodes
    print(nodes)
    return jsonify(nodes)


@app.route("/edges", methods=["GET"])
def get_edges():
    global edges

    return jsonify(edges)


if __name__ == "__main__":
    app.run(debug=True)
