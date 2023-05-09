let selected_node: SVGRectElement | null = null;
let offset_x = 0;
let offset_y = 0;
let global_offset_x = 0;
let global_offset_y = 0;
let global_zoom = 1;
let changesMade = false;
const nodeSize = 50;

enum State {
    Move = "move",
    CreatePlace = "create_place",
    CreateTransition = "create_transition",
    Connect = "connect",
    Delete = "delete",
    Clear = "clear",
    Save = "save",
}

enum MoveState {
    MovingNode = "moving_node",
    MovingGraph = "moving_graph",
    None = "none",
}

type GraphNodeId = {
    id: number;
};

type Position = {
    x: number;
    y: number;
};

enum NodeType {
    Place = "place",
    Transition = "transition",
}

type GraphNode = {
    id: GraphNodeId;
    node_type: NodeType;
    position: Position;
};


type Edge = {
    start_node_id: GraphNodeId;
    end_node_id: GraphNodeId;
    start_position: Position;
    end_position: Position;
};

let state: State = State.Move;
let moveState: MoveState = MoveState.None;
let model_id: string = (() => {
    const url = new URL(window.location.href);
    return url.searchParams.get("model_id")!;
})();

const state_buttons = {
    [State.Move]: document.getElementById('btn-move')!,
    [State.CreatePlace]: document.getElementById('btn-create-place')!,
    [State.CreateTransition]: document.getElementById('btn-create-transition')!,
    [State.Connect]: document.getElementById('btn-connect')!,
    [State.Delete]: document.getElementById('btn-delete')!,
    [State.Clear]: document.getElementById('btn-clear')!,
    [State.Save]: document.getElementById('btn-save')!,
};

var canvas = document.getElementById("canvas");
if (!canvas || !(canvas instanceof SVGSVGElement)) {
    throw new Error("canvas not found");
}

function madeChange() {
    changesMade = true;
    document.getElementById("btn-save")!.classList.remove("disabled");
}

function resetChanges() {
    changesMade = false;
    document.getElementById("btn-save")!.classList.add("disabled");
}

function changeState(newState: State) {
    state = newState;
    selected_node = null;
}

function toggleState(newState: State) {
    if (state === newState) {
        changeState(State.Move);
        state_buttons[newState].classList.remove("active");
    } else {
        state_buttons[state]?.classList.remove("active");
        changeState(newState);
        state_buttons[newState].classList.add("active");
    }
}

function transformCoords(x: number, y: number, screenToGraph: boolean): SVGPoint {
    const svg = document.getElementById("canvas");
    const graph = document.getElementById("graph");
    if (!(graph instanceof SVGGElement) || !(svg instanceof SVGSVGElement)) {
        throw new Error("Could not find SVGSVGElement with ID 'graph'");
    }

    const pt = svg.createSVGPoint();
    pt.x = x;
    pt.y = y;

    const screenCTM = graph.getScreenCTM();
    if (screenCTM) {
        return pt.matrixTransform(screenToGraph ? screenCTM.inverse() : screenCTM);
    }

    return pt;
}

function graphToScreenCoords(x: number, y: number): SVGPoint {
    return transformCoords(x, y, false)
}

function screenToGraphCoords(x: number, y: number): SVGPoint {
    return transformCoords(x, y, true)
}


function moveStart(event: MouseEvent) {
    if (event.target instanceof SVGRectElement) {
        selected_node = event.target;
    } else if (event.target instanceof SVGTextElement) {
        selected_node = event.target.previousElementSibling as SVGRectElement;
    } else if (event.target instanceof SVGSVGElement) {
        selected_node = null;
        offset_x = event.clientX;
        offset_y = event.clientY;
        moveState = MoveState.MovingGraph;
        return;
    } else {
        return;
    }
    const point = graphToScreenCoords(
        parseInt(selected_node.getAttribute("x")!),
        parseInt(selected_node.getAttribute("y")!)
    );
    offset_x = event.clientX - point.x;
    offset_y = event.clientY - point.y;
    moveState = MoveState.MovingNode;
}

function updateGraphTransform() {
    const graph = document.getElementById("graph")!;
    if (!(canvas instanceof SVGSVGElement) || !(graph instanceof SVGGraphicsElement)) {
        throw new Error("canvas or graph not found");
    }

    const scale = canvas.createSVGTransform();
    scale.setScale(global_zoom, global_zoom);

    // Translate to the current offset
    const translateOffset = canvas.createSVGTransform();
    translateOffset.setTranslate(global_offset_x / global_zoom, global_offset_y / global_zoom);

    const transformList = graph.transform.baseVal;
    transformList.clear();
    transformList.appendItem(scale);
    transformList.appendItem(translateOffset);
}



function move(event: MouseEvent) {
    if (moveState === MoveState.MovingNode && selected_node) {
        const point = screenToGraphCoords(event.clientX - offset_x, event.clientY - offset_y);
        selected_node.setAttribute("x", point.x.toString());
        selected_node.setAttribute("y", point.y.toString());
        updateEdges();
        const label = selected_node.nextElementSibling as SVGTextElement;
        label.setAttribute("x", point.x.toString());
        label.setAttribute("y", point.y.toString());
    } else if (moveState === MoveState.MovingGraph) {
        global_offset_x += event.clientX - offset_x;
        global_offset_y += event.clientY - offset_y;
        offset_x = event.clientX;
        offset_y = event.clientY;
        updateGraphTransform();
    }
}

function moveEnd(_event: MouseEvent) {
    if (moveState === MoveState.MovingNode) {
        var node_id = selected_node!.getAttribute("data-id")!;
        var x = parseInt(selected_node!.getAttribute("x")!);
        var y = parseInt(selected_node!.getAttribute("y")!);
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/move");
        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
        xhr.send(`model_id=${model_id}&node_id=${node_id}&x=${x}&y=${y}`);
        selected_node = null;
        madeChange();
    }
    moveState = MoveState.None;
}

function handleScroll(event: WheelEvent) {
    global_zoom = Math.min(Math.max(0.125, global_zoom + event.deltaY * -0.01), 4);
    updateGraphTransform();
    event.preventDefault();
}


function connectClick(event: MouseEvent) {
    var node: SVGRectElement;
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
        let start_pos = {
            x: parseInt(selected_node!.getAttribute("x")!),
            y: parseInt(selected_node!.getAttribute("y")!)
        };
        let end_pos = {
            x: parseInt(node.getAttribute("x")!),
            y: parseInt(node.getAttribute("y")!)
        };

        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/connect");
        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
        xhr.onreadystatechange = () => {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                var edge = JSON.parse(xhr.responseText);
                edge.start_position = start_pos;
                edge.end_position = end_pos;
                addEdgeToCanvas(edge as Edge);
                madeChange();
            }
        };
        xhr.send(`model_id=${model_id}&start_node_id=${start_node_id}&end_node_id=${end_node_id}`);

        selected_node = null;
    } else {
        selected_node = node;
    }

}

function createClick(event: MouseEvent, new_node_type: NodeType) {
    var point = screenToGraphCoords(event.clientX, event.clientY);
    var node_type = new_node_type;

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/create");
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var node = JSON.parse(xhr.responseText);
            addNodeToCanvas(node);
            madeChange();
        }
    };
    xhr.send(`model_id=${model_id}&x=${point.x}&y=${point.y}&node_type=${node_type}`);
}

function deleteClick(event: MouseEvent) {
    var node: SVGRectElement;
    if (event.target instanceof SVGRectElement) {
        node = event.target;
    } else if (event.target instanceof SVGTextElement) {
        node = event.target.previousElementSibling as SVGRectElement;
    } else {
        return;
    }
    var node_id = node.getAttribute("data-id");
    if (!node_id) {
        throw new Error("node_id not found");
    }
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/delete");
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            removeNodeFromCanvas(node_id!);
            madeChange();
        }
    };
    xhr.send(`model_id=${model_id}&node_id=${node_id}`);
}

function addEdgeToCanvas(edge: Edge) {
    const edges = document.getElementById("edges");
    if (!edges) throw new Error("edges not found");

    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", "arrow");
    marker.setAttribute("markerWidth", "10");
    marker.setAttribute("markerHeight", "10");
    marker.setAttribute("refX", "8");
    marker.setAttribute("refY", "5");
    marker.setAttribute("orient", "auto-start-reverse");

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
    path.setAttribute("fill", "black");

    marker.appendChild(path);
    edges.appendChild(marker);

    let { start_x, start_y, end_x, end_y } = computeEdgeOffsetPosition(edge, NodeType.Place, NodeType.Place);

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("class", "edge");
    line.setAttribute("x1", start_x.toString());
    line.setAttribute("y1", start_y.toString());
    line.setAttribute("x2", end_x.toString());
    line.setAttribute("y2", end_y.toString());
    line.setAttribute("data-start-node-id", edge.start_node_id.toString());
    line.setAttribute("data-end-node-id", edge.end_node_id.toString());

    edges.appendChild(line);
}

function computeEdgeOffsetPosition(edge: Edge, start_node_type: NodeType, end_node_type: NodeType) {
    const angle = Math.atan2(edge.end_position.y - edge.start_position.y, edge.end_position.x - edge.start_position.x);
    const end_offset = nodeSize / 2 + 5;
    const adjacent = end_offset / Math.abs(Math.cos(angle));
    const opposite = end_offset / Math.abs(Math.sin(angle));
    const side = Math.min(adjacent, opposite);
    const square_offset = { x: side * Math.cos(angle), y: side * Math.sin(angle) };
    const circle_offset = { x: end_offset * Math.cos(angle), y: end_offset * Math.sin(angle) };
    const { x: start_offset_x, y: start_offset_y } = start_node_type === NodeType.Place ? circle_offset : square_offset;
    const { x: end_offset_x, y: end_offset_y } = end_node_type === NodeType.Place ? circle_offset : square_offset;
    const start_x = edge.start_position.x + start_offset_x;
    const start_y = edge.start_position.y + start_offset_y;
    const end_x = edge.end_position.x - end_offset_x;
    const end_y = edge.end_position.y - end_offset_y;
    return { start_x, start_y, end_x, end_y };
}

function addNodeToCanvas(node: GraphNode) {
    var nodes = document.getElementById("nodes");
    if (!nodes) throw new Error("nodes not found");

    var node_group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    node_group.setAttribute("class", "node-group");
    node_group.setAttribute("data-id", node.id.toString());

    var rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("class", `node node-${node.node_type.toLowerCase()}`);
    rect.setAttribute("x", (node.position.x).toString());
    rect.setAttribute("y", (node.position.y).toString());
    rect.setAttribute("data-id", node.id.toString());

    var text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "node-text");
    text.setAttribute("x", (node.position.x).toString());
    text.setAttribute("y", (node.position.y).toString());
    text.setAttribute("data-id", node.id.toString());
    text.textContent = node.id.toString();

    node_group.appendChild(rect);
    node_group.appendChild(text);
    nodes.appendChild(node_group);
}

function removeNodeFromCanvas(node_id: string) {
    var nodes = document.getElementById("nodes");
    if (!nodes) {
        throw new Error("nodes not found");
    }
    var node_elements = nodes.querySelectorAll(`[data-id="${node_id}"]`);
    if (!node_elements) {
        throw new Error("node not found");
    }
    node_elements.forEach(element => { element.remove() });
    var edges = document.getElementsByClassName("edge");
    for (var i = edges.length - 1; i >= 0; i--) {
        const start_node_id = edges[i].getAttribute("data-start-node-id");
        const end_node_id = edges[i].getAttribute("data-end-node-id");
        if (start_node_id === node_id || end_node_id === node_id) {
            edges[i].remove();
        }
    }
}

function updateEdges() {
    const edges = document.getElementsByClassName("edge");

    for (var i = edges.length - 1; i >= 0; i--) {
        const start_node_id = edges[i].getAttribute("data-start-node-id");
        const end_node_id = edges[i].getAttribute("data-end-node-id");
        let start_node = canvas!.querySelector(`rect[data-id="${start_node_id}"]`);
        let end_node = canvas!.querySelector(`rect[data-id="${end_node_id}"]`);

        let start_position = { x: Number(start_node?.getAttribute("x")), y: Number(start_node?.getAttribute("y")) };
        let end_position = { x: Number(end_node?.getAttribute("x")), y: Number(end_node?.getAttribute("y")) };

        let { start_x, start_y, end_x, end_y } = computeEdgeOffsetPosition(
            {
                start_position: start_position,
                end_position: end_position,
                end_node_id: { id: parseInt(end_node_id!) },
                start_node_id: { id: parseInt(end_node_id!) }
            },
            start_node?.classList.contains("node-place") ? NodeType.Place : NodeType.Transition,
            end_node?.classList.contains("node-place") ? NodeType.Place : NodeType.Transition,
        );

        edges[i].setAttribute("x1", (start_x).toString());
        edges[i].setAttribute("y1", (start_y).toString());
        edges[i].setAttribute("x2", (end_x).toString());
        edges[i].setAttribute("y2", (end_y).toString());
    }
}


function renderNodesAndEdges() {

    var xhr_edges = new XMLHttpRequest();
    xhr_edges.open("GET", `/edges?model_id=${model_id}`);
    xhr_edges.onreadystatechange = () => {
        if (xhr_edges.readyState === XMLHttpRequest.DONE && xhr_edges.status === 200) {
            var edges = JSON.parse(xhr_edges.responseText);
            for (var edge of edges) {
                edge.start_position = { x: 0, y: 0 };
                edge.end_position = { x: 0, y: 0 };
                addEdgeToCanvas(edge as Edge);
            }
            updateEdges();
        }
    };

    var xhr_nodes = new XMLHttpRequest();
    xhr_nodes.open("GET", `/nodes?model_id=${model_id}`);
    xhr_nodes.onreadystatechange = () => {
        if (xhr_nodes.readyState === XMLHttpRequest.DONE && xhr_nodes.status === 200) {
            var nodes = JSON.parse(xhr_nodes.responseText);
            for (var node of nodes) {
                addNodeToCanvas(node);
            }
            xhr_edges.send();
        }
    };


    xhr_nodes.send();

}

function clearAll() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/clear");
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var nodes = document.getElementById("nodes");
            if (!nodes) throw new Error("nodes not found");
            while (nodes.firstChild) {
                nodes.removeChild(nodes.firstChild);
            }
            var edges = document.getElementById("edges");
            if (!edges) throw new Error("edges not found");
            while (edges.firstChild) {
                edges.removeChild(edges.firstChild);
            }
            madeChange();
        }
    };
    xhr.send(`model_id=${model_id}`);
}

function save() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/save");
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
            var alert = document.getElementById("save-success-alert")!;
            alert.classList.add("show");
            setTimeout(() => { alert.classList.remove("show") }, 2000);
            resetChanges();
        }
    };
    xhr.send(`model_id=${model_id}`);
}

canvas.addEventListener("mousedown", (event: MouseEvent) => {
    switch (state) {
        case State.Move:
            moveStart(event);
            break;
        case State.CreatePlace:
            createClick(event, NodeType.Place);
            break;
        case State.CreateTransition:
            createClick(event, NodeType.Transition);
            break;
        case State.Connect:
            connectClick(event);
            break;
        case State.Delete:
            deleteClick(event);
            break;
    }
});
canvas.addEventListener("mousemove", (event: MouseEvent) => {
    switch (state) {
        case State.Move:
            move(event);
            break;
        default:
            break;
    }
});
canvas.addEventListener("mouseup", (event: MouseEvent) => {
    switch (state) {
        case State.Move:
            moveEnd(event);
            break;
        default:
            break;
    }
}
);
canvas.addEventListener("mouseleave", (event: MouseEvent) => {
    switch (state) {
        case State.Move:
            moveEnd(event);
            break;
        default:
            break;
    }
});
canvas.addEventListener("wheel", (event: WheelEvent) => { handleScroll(event) });

state_buttons.create_place.addEventListener("click", () => { toggleState(State.CreatePlace) });
state_buttons.create_transition.addEventListener("click", () => { toggleState(State.CreateTransition) });
state_buttons.connect.addEventListener("click", () => { toggleState(State.Connect) });
state_buttons.delete.addEventListener("click", () => { toggleState(State.Delete) });
state_buttons.clear.addEventListener("click", () => { clearAll() });
state_buttons.save.addEventListener("click", () => { save() });


renderNodesAndEdges();
