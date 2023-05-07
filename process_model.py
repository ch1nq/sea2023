import os
import pydantic
import random
import enum


@pydantic.dataclasses.dataclass(order=True, frozen=True)
class NodeId:
    id: int


@pydantic.dataclasses.dataclass(eq=True, order=True)
class Point:
    x: float
    y: float


class NodeType(str, enum.Enum):
    PLACE = "place"
    TRANSITION = "transition"


@pydantic.dataclasses.dataclass(eq=True, order=True)
class Node:
    id: NodeId
    node_type: NodeType
    position: Point


@pydantic.dataclasses.dataclass(eq=True, order=True)
class Edge:
    start_node_id: NodeId
    end_node_id: NodeId
    start_position: Point
    end_position: Point


@pydantic.dataclasses.dataclass(eq=True, order=True)
class Graph:
    nodes: dict[NodeId, Node]
    edges: dict[tuple[NodeId, NodeId], Edge]


class ProcessModel(pydantic.BaseModel):
    MAX_NODES = 10000

    id: str
    nodes: dict[NodeId, Node] = {}
    edges: dict[tuple[NodeId, NodeId], Edge] = {}

    def save(self, path: os.PathLike) -> None:
        """Save the process model to a file."""
        with open(path, "w") as f:
            f.write(self.json())

    @classmethod
    def load(cls, path: os.PathLike) -> "ProcessModel":
        """Load a process model from a file."""
        with open(path, "r") as f:
            return cls.parse_raw(f.read())

    def new_node_id(self) -> NodeId:
        id = random.randint(0, self.MAX_NODES)
        while id in self.nodes.keys():
            id = random.randint(0, self.MAX_NODES)
        return NodeId(id)

    def add_node(self, node_type: NodeType, x: float, y: float) -> Node:
        node_id = self.new_node_id()
        node = Node(node_id, node_type, Point(x, y))
        self.nodes[node_id] = node
        return node

    def delete_node(self, node_id: NodeId) -> None:
        self.nodes.pop(node_id)
        for other_node in self.nodes.keys():
            self.edges.pop((node_id, other_node), None)
            self.edges.pop((other_node, node_id), None)

    def move_node(self, node_id: NodeId, x: float, y: float) -> None:
        self.nodes[node_id].position = Point(x, y)

        for (edge_start_id, edge_end_id), edge in self.edges.items():
            if node_id == edge_start_id:
                edge.start_position = Point(x, y)
            elif node_id == edge_end_id:
                edge.end_position = Point(x, y)

    def connect(self, start_node_id: NodeId, end_node_id: NodeId) -> Edge | None:
        if (
            start_node_id == end_node_id
            or (start_node_id, end_node_id) in self.edges.keys()
            # Ensure valid connection in process model
            or self.nodes[start_node_id].node_type == self.nodes[end_node_id].node_type
        ):
            return None

        edge = Edge(
            start_node_id,
            end_node_id,
            self.nodes[start_node_id].position,
            self.nodes[end_node_id].position,
        )
        self.edges[(start_node_id, end_node_id)] = edge
        return edge

    def clear(self) -> None:
        self.nodes = {}
        self.edges = {}

    def get_nodes(self) -> list[Node]:
        return list(self.nodes.values())

    def get_edges(self) -> list[Edge]:
        return list(self.edges.values())
