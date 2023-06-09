let selected_node: SVGRectElement | null = null;
let offset_x = 0;
let offset_y = 0;
let global_offset_x = 0;
let global_offset_y = 0;
let global_zoom = 1;
let changesMade = false;
let moveStartPosition: Position | null = null;
const nodeSize = 50;

enum State {
    Move = "move",
    CreatePlace = "create_place",
    CreateTransition = "create_transition",
    Connect = "connect",
    Delete = "delete",
    Clear = "clear",
    Save = "save",
    Undo = "undo",
    Redo = "redo",
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

type PetriNetNode = {
    id: GraphNodeId;
    node_type: NodeType;
    position: Position;
    ball_count: number;
};

type Edge = {
    start_node_id: GraphNodeId;
    end_node_id: GraphNodeId;
    start_position: Position;
    end_position: Position;
};

let state: State = State.Move;
let moveState: MoveState = MoveState.None;

const state_buttons = {
    [State.Move]: document.getElementById('btn-move')!,
    [State.CreatePlace]: document.getElementById('btn-create-place')!,
    [State.CreateTransition]: document.getElementById('btn-create-transition')!,
    [State.Connect]: document.getElementById('btn-connect')!,
    [State.Delete]: document.getElementById('btn-delete')!,
    [State.Clear]: document.getElementById('btn-clear')!,
    [State.Save]: document.getElementById('btn-save')!,
    [State.Undo]: document.getElementById('btn-undo')!,
    [State.Redo]: document.getElementById('btn-redo')!,
};


let inspector_panel = document.getElementById("inspector-panel");
let inspector_panel_content = document.getElementById("inspector-panel-content");
if (!inspector_panel || !inspector_panel_content) {
    throw new Error("inspector panel not found");
}
var model_id: string = (() => {
    const url = new URL(window.location.href);
    return url.searchParams.get("model_id")!;
})();


function madeChange() {
    changesMade = true;
    state_buttons[State.Save].classList.remove("disabled");
}

function resetChanges() {
    changesMade = false;
    state_buttons[State.Save].classList.add("disabled");
}

function changeState(newState: State, websocket: WebSocket) {
    state = newState;
    selectNode(null, websocket);
}

function toggleState(newState: State, websocket: WebSocket) {
    if (state === newState) {
        changeState(State.Move, websocket);
        state_buttons[newState].classList.remove("active");
    } else {
        state_buttons[state]?.classList.remove("active");
        changeState(newState, websocket);
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

function populateNodeInspector(node_id: GraphNodeId, websocket: WebSocket) {
    const spinner = document.getElementById("inspector-panel-spinner")!;
    spinner.classList.remove("d-none");

    websocket.send(JSON.stringify({
        request: {
            request_type: "inspector",
            node_id: node_id.id,
        }
    }));
}

function selectNode(node: SVGRectElement | null, websocket: WebSocket) {
    if (selected_node) {
        selected_node.parentElement?.classList.remove("selected");
    }
    selected_node = node;
    if (!selected_node) {
        inspector_panel?.classList.remove("show");
        return;
    }
    selected_node.parentElement?.classList.add("selected");
    inspector_panel?.classList.add("show");
    populateNodeInspector({ id: parseInt(selected_node.getAttribute("data-id")!) }, websocket);
}

function moveStart(event: MouseEvent, websocket: WebSocket) {
    if (event.target instanceof SVGRectElement) {
        selectNode(event.target, websocket);
    } else if (event.target instanceof SVGTextElement) {
        selectNode(event.target.previousElementSibling as SVGRectElement, websocket);
    } else if (event.target instanceof SVGSVGElement) {
        selectNode(null, websocket);
        offset_x = event.clientX;
        offset_y = event.clientY;
        moveState = MoveState.MovingGraph;
        return;
    } else {
        return;
    }
    const x = parseInt(selected_node!.getAttribute("x")!)
    const y = parseInt(selected_node!.getAttribute("y")!)
    const point = graphToScreenCoords(x, y);
    offset_x = event.clientX - point.x;
    offset_y = event.clientY - point.y;
    moveStartPosition = { x, y };
    moveState = MoveState.MovingNode;
}

function updateGraphTransform(canvas: SVGSVGElement) {
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

        const node_id = parseInt(selected_node.getAttribute("data-id")!);
        const edges = document.querySelectorAll(`[data-start-node-id="${node_id}"], [data-end-node-id="${node_id}"]`);
        for (var edge of edges) {
            const start_node_id = parseInt(edge.getAttribute("data-start-node-id")!);
            const end_node_id = parseInt(edge.getAttribute("data-end-node-id")!);
            const start_node = document.querySelector(`.node[data-id="${start_node_id}"]`) as SVGRectElement;
            const end_node = document.querySelector(`.node[data-id="${end_node_id}"]`) as SVGRectElement;
            updateEdgePosition({
                start_node_id: { id: start_node_id },
                end_node_id: { id: end_node_id },
                start_position: { x: parseFloat(start_node.getAttribute("x")!), y: parseFloat(start_node.getAttribute("y")!) },
                end_position: { x: parseFloat(end_node.getAttribute("x")!), y: parseFloat(end_node.getAttribute("y")!) },
            });
        }

        const label = selected_node.nextElementSibling as SVGTextElement;
        label.setAttribute("x", point.x.toString());
        label.setAttribute("y", point.y.toString());
    } else if (moveState === MoveState.MovingGraph) {
        const canvas = event.target as SVGSVGElement;
        global_offset_x += event.clientX - offset_x;
        global_offset_y += event.clientY - offset_y;
        offset_x = event.clientX;
        offset_y = event.clientY;
        updateGraphTransform(canvas);
    }
}

function moveEnd(_event: MouseEvent, websocket: WebSocket) {
    if (moveState === MoveState.MovingNode) {
        var node_id = selected_node!.getAttribute("data-id")!;
        var x = parseFloat(selected_node!.getAttribute("x")!);
        var y = parseFloat(selected_node!.getAttribute("y")!);

        // Only update the node if it has moved
        if (moveStartPosition!.x !== x || moveStartPosition!.y !== y) {
            websocket.send(JSON.stringify({
                request: {
                    request_type: "execute_command",
                    command: {
                        command_type: "move_node",
                        node_id: parseInt(node_id),
                        x: x,
                        y: y,
                    }
                }
            }));
        }
    }
    moveStartPosition = null;
    moveState = MoveState.None;
}

function handleScroll(event: WheelEvent,) {
    const canvas = event.target as SVGSVGElement;
    global_zoom = Math.min(Math.max(0.125, global_zoom + event.deltaY * -0.01), 4);
    updateGraphTransform(canvas);
    event.preventDefault();
}


function connectClick(event: MouseEvent, websocket: WebSocket) {
    var node: SVGRectElement;
    if (event.target instanceof SVGRectElement) {
        node = event.target;
    } else if (event.target instanceof SVGTextElement) {
        node = event.target.previousElementSibling as SVGRectElement;
    } else {
        return;
    }

    if (selected_node && selected_node !== node) {
        let start_node_id = selected_node.getAttribute("data-id");
        let end_node_id = node.getAttribute("data-id");

        websocket.send(JSON.stringify({
            request: {
                request_type: "execute_command",
                command: {
                    command_type: "create_edge",
                    start_node_id: parseInt(start_node_id!),
                    end_node_id: parseInt(end_node_id!),
                    edge_kwargs: {
                        ball_count: 1,
                    },
                }
            }
        }));

        selectNode(null, websocket);
    } else {
        selectNode(node, websocket);
    }

}

function createClick(event: MouseEvent, new_node_type: NodeType, websocket: WebSocket) {
    var point = screenToGraphCoords(event.clientX, event.clientY);
    websocket.send(JSON.stringify({
        request: {
            request_type: "execute_command",
            command: {
                command_type: "create_node",
                model_id: model_id,
                x: point.x,
                y: point.y,
                node_kwargs: {
                    node_type: new_node_type,
                },
            }
        }
    }));
}

function deleteClick(event: MouseEvent, websocket: WebSocket) {
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

    websocket.send(JSON.stringify({
        request: {
            request_type: "execute_command",
            command: {
                command_type: "delete_node",
                node_id: parseInt(node_id),
            }
        }
    }));
}

function addEdgeToCanvas(edge: Edge, start_node_type: NodeType, end_node_type: NodeType) {
    const edges = document.getElementById("edges");
    if (!edges) throw new Error("edges not found");

    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    // marker.classList.add("edge");
    marker.setAttribute("id", `arrow`);
    marker.setAttribute("markerWidth", "10");
    marker.setAttribute("markerHeight", "10");
    marker.setAttribute("refX", "8");
    marker.setAttribute("refY", "5");
    marker.setAttribute("orient", "auto-start-reverse");

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    // path.classList.add("edge");
    path.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");

    marker.appendChild(path);
    edges.appendChild(marker);

    let { start_x, start_y, end_x, end_y } = computeEdgeOffsetPosition(edge, start_node_type, end_node_type);

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("class", "edge");
    line.setAttribute("x1", start_x.toString());
    line.setAttribute("y1", start_y.toString());
    line.setAttribute("x2", end_x.toString());
    line.setAttribute("y2", end_y.toString());
    line.setAttribute("data-start-node-id", edge.start_node_id.id.toString());
    line.setAttribute("data-end-node-id", edge.end_node_id.id.toString());

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

function addNodeToCanvas(node: PetriNetNode) {
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
    text.textContent = node.ball_count.toString();

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

function updateNodesAndEdges(new_nodes: Map<String, PetriNetNode>, new_edges: Edge[]) {
    const old_nodes = document.getElementById("nodes")!.querySelectorAll(".node-group");
    const old_edges = document.getElementById("edges")!.querySelectorAll(".edge");

    // remove nodes that are not in new_nodes
    for (var node of old_nodes) {
        const node_id = node.getAttribute("data-id")!;
        // check if node is in new_nodes
        const new_node = new_nodes.get(node_id!);
        if (!new_node) {
            // remove node from canvas
            removeNodeFromCanvas(node_id!);
        } else {
            // update node
            const text = node.querySelector(`.node-text`)! as SVGTextElement;
            text.textContent = new_node.ball_count.toString();

            // update position
            const rect = node.querySelector(".node")!;
            rect.setAttribute("x", new_node.position.x.toString());
            rect.setAttribute("y", new_node.position.y.toString());
            text.setAttribute("x", new_node.position.x.toString());
            text.setAttribute("y", new_node.position.y.toString());
        }
    }

    // add nodes that are not in old_nodes
    for (var new_node of new_nodes.values()) {
        const node_id = new_node.id.toString();
        const old_node = Array.from(old_nodes).find(n => n.getAttribute("data-id") === node_id);
        if (!old_node) {
            addNodeToCanvas(new_node);
        }
    }


    // remove edges that are not in new_edges
    for (var edge of old_edges) {
        const start_node_id = edge.getAttribute("data-start-node-id");
        const end_node_id = edge.getAttribute("data-end-node-id");

        const new_edge = new_edges.find(e => e.start_node_id.id.toString() === start_node_id && e.end_node_id.id.toString() === end_node_id);
        if (!new_edge) {
            edge.remove();
        }
    }

    for (var new_edge of new_edges) {
        const start_node = new_nodes.get(new_edge.start_node_id.id.toString());
        const end_node = new_nodes.get(new_edge.end_node_id.id.toString());
        if (!start_node || !end_node) throw new Error("start or end node not found");
        const edge = document.querySelector(`.edge[data-start-node-id="${start_node.id}"][data-end-node-id="${end_node.id}"]`);
        if (!edge) {
            // add edge to canvas
            addEdgeToCanvas(new_edge, start_node.node_type, end_node.node_type);
        } else {
            // update edge
            updateEdgePosition(new_edge);
        }
    }
}

function updateEdgePosition(edge: Edge) {
    const nodes = document.getElementById("nodes")!;
    const edges = document.getElementById("edges")!;
    const start_node = nodes.querySelector(`.node[data-id="${edge.start_node_id.id}"]`)!;
    const end_node = nodes.querySelector(`.node[data-id="${edge.end_node_id.id}"]`)!;
    const start_node_type = start_node.classList.contains("node-place") ? NodeType.Place : NodeType.Transition;
    const end_node_type = end_node.classList.contains("node-place") ? NodeType.Place : NodeType.Transition;
    const { start_x, start_y, end_x, end_y } = computeEdgeOffsetPosition(edge, start_node_type, end_node_type);
    const edge_element = edges.querySelector(`.edge[data-start-node-id="${edge.start_node_id.id}"][data-end-node-id="${edge.end_node_id.id}"]`)!;

    edge_element.setAttribute("x1", start_x.toString());
    edge_element.setAttribute("y1", start_y.toString());
    edge_element.setAttribute("x2", end_x.toString());
    edge_element.setAttribute("y2", end_y.toString());

}

function clearAll(websocket: WebSocket) {
    websocket.send(JSON.stringify({
        request: {
            request_type: "execute_command", command: {
                command_type: "clear_model"
            }
        }
    }));
}

function save(websocket: WebSocket) {
    websocket.send(JSON.stringify({
        request: {
            request_type: "execute_command", command: {
                command_type: "save_model",
                path: model_id
            }
        }
    }));
}

function undo(websocket: WebSocket) {
    websocket.send(JSON.stringify({ request: { request_type: "undo" } }));
}

function redo(websocket: WebSocket) {
    websocket.send(JSON.stringify({ request: { request_type: "redo" } }));
}

function updateCollaborators(collaborators: string[]) {
    let icon_factory = (collaborator_id: string) => {
        const collaborator_icon = document.createElement("i");
        collaborator_icon.classList.add("collaborator-icon");
        collaborator_icon.classList.add("bi");
        collaborator_icon.classList.add("bi-person-circle");
        collaborator_icon.classList.add("text-primary");
        collaborator_icon.setAttribute("data-bs-toggle", "tooltip");
        collaborator_icon.setAttribute("data-bs-placement", "bottom");
        collaborator_icon.setAttribute("title", collaborator_id);
        collaborator_icon.setAttribute("data-collaborator-id", collaborator_id);
        return collaborator_icon;
    };
    const collaborator_wrapper = document.getElementById("collaborators")!;
    collaborator_wrapper.innerHTML = "";

    if (collaborators.length > 0) {
        const collaborator_icon = icon_factory("You");
        collaborator_icon.classList.remove("text-primary");
        collaborator_icon.classList.add("text-secondary");
        collaborator_wrapper.appendChild(collaborator_icon);

        for (var collaborator of collaborators) {
            const collaborator_icon = icon_factory(collaborator);
            collaborator_wrapper.appendChild(collaborator_icon);
        }
    } else {
        collaborator_wrapper.innerHTML = "<div class='badge text-muted'>None</div>";
    }
}

const scheme = window.location.protocol === "https:" ? "wss" : "ws";
const port = window.location.port ? `:${window.location.port}` : "";
const ws_url = `${scheme}://${window.location.hostname}${port}/ws`;
const ws = new WebSocket(ws_url);
ws.addEventListener("message", (event: MessageEvent) => {
    const message = JSON.parse(event.data);
    switch (message.event_type) {
        case "update_model":
            const nodes: Map<string, PetriNetNode> = new Map(Object.entries(message.model.nodes));
            const edges: Edge[] = message.model.edges.map((edge: any) => {
                return {
                    start_node_id: { id: edge.start_node_id },
                    end_node_id: { id: edge.end_node_id },
                    start_position: nodes.get(edge.start_node_id.toString())!.position,
                    end_position: nodes.get(edge.end_node_id.toString())!.position,
                };
            });
            selectNode(selected_node, ws);
            updateNodesAndEdges(nodes, edges);
            madeChange();
            break;
        case "update_undo_redo":
            state_buttons[State.Undo].toggleAttribute("disabled", !message.can_undo);
            state_buttons[State.Redo].toggleAttribute("disabled", !message.can_redo);
            break;
        case "close_inspector":
            selectNode(null, ws);
            break;
        case "saved_success":
            const alert = document.getElementById("save-success-alert")!;
            alert.classList.add("show");
            setTimeout(() => { alert.classList.remove("show") }, 2000);
            resetChanges();
            break;
        case "update_inspector":
            inspector_panel_content!.innerHTML = message.inspector_html;
            document.getElementById("inspector-panel-spinner")!.classList.add("d-none");
            break;
        case "update_collaborators":
            updateCollaborators(message.collaborator_ids);
            break;
    }
});
ws.addEventListener("open", () => {
    ws!.send(JSON.stringify({
        request: {
            request_type: "join_session",
            model_id: model_id,
        }
    }));
});
ws.addEventListener("close", () => {
    document.getElementById('openDisconnedtedModalButton')!.click();
});


let canvas = document.getElementById("canvas");
if (!canvas || !(canvas instanceof SVGSVGElement)) {
    throw new Error("canvas not found");
}

canvas.addEventListener("mousedown", (event: MouseEvent) => {
    switch (state) {
        case State.Move:
            moveStart(event, ws);
            break;
        case State.CreatePlace:
            createClick(event, NodeType.Place, ws);
            break;
        case State.CreateTransition:
            createClick(event, NodeType.Transition, ws);
            break;
        case State.Connect:
            connectClick(event, ws);
            break;
        case State.Delete:
            deleteClick(event, ws);
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
            moveEnd(event, ws);
            break;
        default:
            break;
    }
}
);
canvas.addEventListener("mouseleave", (event: MouseEvent) => {
    switch (state) {
        case State.Move:
            moveEnd(event, ws);
            break;
        default:
            break;
    }
});
canvas.addEventListener("wheel", (event: WheelEvent) => { handleScroll(event) });
document.getElementById("update-node-properties")?.addEventListener("click", () => {
    let formData = new FormData(document.getElementById("node-inspector-form") as HTMLFormElement);

    const data = Object.fromEntries(formData);

    ws.send(JSON.stringify({
        request: {
            request_type: "execute_command", command: {
                command_type: "update_inspectables",
                node_id: data.node_id,
                node_kwargs: data,
            }
        }
    }));
});

state_buttons.create_place.addEventListener("click", () => { toggleState(State.CreatePlace, ws) });
state_buttons.create_transition.addEventListener("click", () => { toggleState(State.CreateTransition, ws) });
state_buttons.connect.addEventListener("click", () => { toggleState(State.Connect, ws) });
state_buttons.delete.addEventListener("click", () => { toggleState(State.Delete, ws) });
state_buttons.clear.addEventListener("click", () => { clearAll(ws) });
state_buttons.save.addEventListener("click", () => { save(ws) });
state_buttons.undo.addEventListener("click", () => { undo(ws) });
state_buttons.redo.addEventListener("click", () => { redo(ws) });

