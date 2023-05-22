import abc
import pathlib
import random
from typing import Generic, NewType, TypeVar

import pydantic
import pydantic.generics
from src import inspector
from src import process_model


ModelId = NewType("ModelId", str)
NodeId = NewType("NodeId", int)
EdgeId = NewType("EdgeId", tuple[NodeId, NodeId])


class Point(pydantic.BaseModel):
    x: float
    y: float


class Node(pydantic.BaseModel, inspector.InspectorMixin):
    id: NodeId
    position: Point

    def field_types(self) -> dict[str, inspector.InspectableField]:
        return super().field_types | {
            "id": inspector.InfoInspectableField,
            "position": inspector.InfoInspectableField,
        }


class Edge(pydantic.BaseModel):
    start_node_id: NodeId
    end_node_id: NodeId

    class Config:
        frozen = True

    @property
    def id(self) -> EdgeId:
        return EdgeId((self.start_node_id, self.end_node_id))


NodeT = TypeVar("NodeT", bound=Node)
EdgeT = TypeVar("EdgeT", bound=Edge)


class ProcessModelBase(pydantic.BaseModel):
    model_type: process_model.ProcessModelType


class ProcessModel(ProcessModelBase, pydantic.generics.GenericModel, Generic[NodeT, EdgeT], abc.ABC):
    MAX_NODES = 10000

    id: ModelId
    nodes: dict[NodeId, NodeT] = pydantic.Field(default_factory=dict)
    edges: set[EdgeT] = pydantic.Field(default_factory=set)

    @abc.abstractmethod
    def node_factory(self, node_id: NodeId, position: Point, **kwargs) -> NodeT:
        """Node factory method."""
        ...

    @abc.abstractmethod
    def edge_factory(self, start_node_id: NodeId, end_node_id: NodeId, **kwargs) -> EdgeT:
        """Edge factory method."""
        ...

    @abc.abstractmethod
    def is_valid_edge(
        self,
        edge: EdgeT,
    ) -> bool:
        ...

    def save(self, path: pathlib.Path) -> None:
        """Save the process model to a file."""
        with open(path, "w") as f:
            f.write(self.copy(update={"edges": list(self.edges)}).json())

    @classmethod
    def load(cls, path: pathlib.Path) -> "ProcessModel":
        """Load a process model from a file."""
        return cls.parse_file(path)

    def new_node_id(self) -> NodeId:
        id = random.randint(0, self.MAX_NODES)
        while id in self.nodes.keys():
            id = random.randint(0, self.MAX_NODES)
        return NodeId(id)

    def add_node(self, x: float, y: float, **node_kwargs) -> NodeT:
        node_id = self.new_node_id()
        node = self.node_factory(node_id, Point(x=x, y=y), **node_kwargs)
        self.nodes[node_id] = node
        return node

    def delete_node(self, node_id: NodeId) -> None:
        self.nodes.pop(node_id)
        for other_node in self.nodes.keys():
            self.delete_edge(EdgeId((node_id, other_node)))
            self.delete_edge(EdgeId((other_node, node_id)))

    def move_node(self, node_id: NodeId, x: float, y: float) -> None:
        self.nodes[node_id].position = Point(x=x, y=y)

    def add_edge(self, start_node_id: NodeId, end_node_id: NodeId, **edge_kwargs) -> EdgeT | None:
        edge = self.edge_factory(start_node_id=start_node_id, end_node_id=end_node_id, **edge_kwargs)
        if not self.is_valid_edge(edge):
            return None
        self.edges.add(edge)
        return edge

    def delete_edge(self, edge_id: EdgeId) -> None:
        for edge in self.edges:
            if edge.id == edge_id:
                self.edges.discard(edge)
                return

    def clear(self) -> None:
        self.nodes = dict()
        self.edges = set()

    def get_node(self, node_id: NodeId) -> NodeT | None:
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: EdgeId) -> EdgeT | None:
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None

    def get_nodes(self) -> list[NodeT]:
        return list(self.nodes.values())

    def get_edges(self) -> list[EdgeT]:
        return list(edge for edge in self.edges)
