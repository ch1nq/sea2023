let selected_node: SVGRectElement | null = null;
let offset_x = 0;
let offset_y = 0;
const nodeSize = 50;

enum State {
    Drag = "drag",
    Create = "create",
    Connect = "connect",
}

let state: State = State.Drag;

function changeState(newState: State) {
    state = newState;
    selected_node = null;
    console.log(state);
    console.log(selected_node);
}

function dragStart(event: MouseEvent) {
    console.log("dragStart");
    if (event.target instanceof SVGRectElement) {
        selected_node = event.target;
    } else if (event.target instanceof SVGTextElement) {
        selected_node = event.target.previousElementSibling as SVGRectElement;
    } else {
        return;
    }
    offset_x = event.clientX - parseInt(selected_node.getAttribute("x")!);
    offset_y = event.clientY - parseInt(selected_node.getAttribute("y")!);
}

function drag(event: MouseEvent) {
    if (selected_node) {
        const x = event.clientX - offset_x;
        const y = event.clientY - offset_y;
        selected_node.setAttribute("x", x.toString());
        selected_node.setAttribute("y", y.toString());
        const node_id = selected_node.getAttribute("data-id")!;
        const node_center_x = x + nodeSize / 2;
        const node_center_y = y + nodeSize / 2;
        updateEdges(node_id, node_center_x, node_center_y);
        const label = selected_node.nextElementSibling as SVGTextElement;
        label.setAttribute("x", node_center_x.toString());
        label.setAttribute("y", node_center_y.toString());
    }
}

function dragEnd(_event: MouseEvent) {
    if (!selected_node) return;
    var node_id = selected_node!.getAttribute("data-id")!;
    var x = parseInt(selected_node!.getAttribute("x")!);
    var y = parseInt(selected_node!.getAttribute("y")!);
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/move");
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.send(`node_id=${node_id}&x=${x}&y=${y}`);
    selected_node = null;
}


function connectClick(event: MouseEvent) {
    var node: SVGRectElement;
    console.log("target", event.target);
    console.log("selected_node", selected_node);
    if (event.target instanceof SVGRectElement) {
        node = event.target;
    } else if (event.target instanceof SVGTextElement) {
        node = event.target.previousElementSibling as SVGRectElement;
    } else {
        return;
    }

    if (selected_node && selected_node !== node) {
        var start_node_id = selected_node.getAttribute("data-id");
        var end_node_id = node.getAttribute("data-id");
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/connect");
        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
        xhr.onreadystatechange = () => {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                var edge = JSON.parse(xhr.responseText);
                addEdgeToCanvas(edge);
            }
        };
        xhr.send(`start_node_id=${start_node_id}&end_node_id=${end_node_id}`);

        selected_node = null;
        changeState(State.Drag);
    } else {
        selected_node = node;
    }

}

function createNode(event: MouseEvent) {
    var x = event.clientX - nodeSize / 2;
    var y = event.clientY - nodeSize / 2;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/create");
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var node = JSON.parse(xhr.responseText);
            addNodeToCanvas(node);
        }
    };
    xhr.send(`x=${x}&y=${y}`);
}

function addEdgeToCanvas(edge: { id: string; start_node_id: string; end_node_id: string; x1: string; y1: string; x2: string; y2: string; }) {
    var edges = document.getElementById("edges");
    if (!edges) {
        throw new Error("edges not found");
    }
    var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("class", "edge");
    line.setAttribute("x1", edge.x1);
    line.setAttribute("y1", edge.y1);
    line.setAttribute("x2", edge.x2);
    line.setAttribute("y2", edge.y2);
    line.setAttribute("stroke", "black");
    line.setAttribute("data-id", edge.id);
    line.setAttribute("data-start-node-id", edge.start_node_id);
    line.setAttribute("data-end-node-id", edge.end_node_id);
    edges.appendChild(line);
}

function addNodeToCanvas(node: { id: string; x: number; y: number; }) {
    var nodes = document.getElementById("nodes");
    if (!nodes) {
        throw new Error("nodes not found");
    }
    var rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("class", "node");
    rect.setAttribute("x", (node.x - nodeSize / 2).toString());
    rect.setAttribute("y", (node.y - nodeSize / 2).toString());
    rect.setAttribute("width", nodeSize.toString());
    rect.setAttribute("height", nodeSize.toString());
    rect.setAttribute("fill", "#eee");
    rect.setAttribute("stroke", "#ccc");
    rect.setAttribute("stroke-width", "1");
    rect.setAttribute("data-id", node.id);
    nodes.appendChild(rect);
    var text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", (node.x).toString());
    text.setAttribute("y", (node.y).toString());
    text.setAttribute("font-size", "20");
    text.setAttribute("font-family", "Arial");
    text.setAttribute("text-anchor", "middle");
    text.textContent = node.id;
    nodes.appendChild(text);
}


function updateEdges(node_id: string, x: number, y: number) {
    const edges = document.getElementsByClassName("edge");
    for (let i = 0; i < edges.length; i++) {
        const start_node_id = edges[i].getAttribute("data-start-node-id");
        const end_node_id = edges[i].getAttribute("data-end-node-id");
        if (start_node_id === node_id) {
            edges[i].setAttribute("x1", (x).toString());
            edges[i].setAttribute("y1", (y).toString());
        }
        if (end_node_id === node_id) {
            edges[i].setAttribute("x2", (x).toString());
            edges[i].setAttribute("y2", (y).toString());
        }
    }
}

function renderNodes() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/nodes");
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var nodes = JSON.parse(xhr.responseText);
            for (var node of nodes) {
                addNodeToCanvas(node);
            }
        }
    };
    xhr.send();
}

function renderEdges() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/edges");
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var edges = JSON.parse(xhr.responseText);
            for (var edge of edges) {
                addEdgeToCanvas(edge);
            }
        }
    };
    xhr.send();
}


var canvas = document.getElementById("canvas");
if (!canvas) {
    throw new Error("canvas not found");
}

canvas.addEventListener("mousedown", (event: MouseEvent) => {
    switch (state) {
        case State.Drag:
            dragStart(event);
            break;
        case State.Create:
            createNode(event);
            changeState(State.Drag);
            break;
        case State.Connect:
            connectClick(event);
            break;
    }
});
canvas.addEventListener("mousemove", (event: MouseEvent) => {
    switch (state) {
        case State.Drag:
            drag(event);
            break;
        case State.Create:
            break;
        case State.Connect:
            break;
    }
});
canvas.addEventListener("mouseup", (event: MouseEvent) => {
    switch (state) {
        case State.Drag:
            dragEnd(event);
            break;
        case State.Create:
            break;
        case State.Connect:
            break;
    }
}
);

document.getElementById('btn-create')?.addEventListener('click', () => { changeState(State.Create) });
document.getElementById('btn-connect')?.addEventListener('click', () => { changeState(State.Connect); });



renderNodes();
renderEdges();