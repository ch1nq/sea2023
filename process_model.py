import enum
import os
import random
import pydantic

from typing import NewType

NodeId = NewType("NodeId", int)


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


@pydantic.dataclasses.dataclass(eq=True, order=True, frozen=True)
class Edge:
    start_node_id: NodeId
    end_node_id: NodeId


class ProcessModel(pydantic.BaseModel):
    MAX_NODES = 10000

    id: str
    nodes: dict[NodeId, Node] = pydantic.Field(default_factory=dict)
    edges: set[Edge] = pydantic.Field(default_factory=set)

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
            self.edges.discard(Edge(node_id, other_node))
            self.edges.discard(Edge(other_node, node_id))

    def move_node(self, node_id: NodeId, x: float, y: float) -> None:
        self.nodes[node_id].position = Point(x, y)

    def connect(self, start_node_id: NodeId, end_node_id: NodeId) -> Edge | None:
        if (
            start_node_id == end_node_id
            or Edge(start_node_id, end_node_id) in self.edges
            # Ensure valid connection in process model
            or self.nodes[start_node_id].node_type == self.nodes[end_node_id].node_type
        ):
            return None

        edge = Edge(start_node_id, end_node_id)
        self.edges.add(edge)
        return edge

    def clear(self) -> None:
        self.nodes = dict()
        self.edges = set()

    def get_nodes(self) -> list[Node]:
        return list(self.nodes.values())

    def get_edges(self) -> list[Edge]:
        return list(edge for edge in self.edges)
