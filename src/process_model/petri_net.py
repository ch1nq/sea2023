import enum

from src import process_model as pm


class NodeType(str, enum.Enum):
    PLACE = "place"
    TRANSITION = "transition"


class PetriNetNode(pm.Node):
    name: str
    node_type: NodeType
    ball_count: int = 0
    accepting_state: str = ""
    hehe69420: str = "1337"


class PetriNetEdge(pm.Edge):
    ball_count: int = 0


class PetriNet(pm.ProcessModel[PetriNetNode, PetriNetEdge]):
    model_type = pm.ProcessModelType.PETRI_NET

    def node_factory(self, node_id: pm.NodeId, position: pm.Point, node_type: NodeType) -> PetriNetNode:
        return PetriNetNode(id=node_id, position=position, node_type=node_type, name=f"Node#{node_id}")

    def edge_factory(self, *args, **kwargs) -> PetriNetEdge:
        return PetriNetEdge(*args, **kwargs)

    def is_valid_edge(self, edge: PetriNetEdge) -> bool:
        """
        Check if an edge can be added to the PetriNet.

        In a PetriNet, a transition can only be connected to places,
        and a place can only be connected to transitions.
        """
        match self.nodes.get(edge.start_node_id), self.nodes.get(edge.end_node_id):
            case (None, _) | (_, None):
                return False
            case start_node, end_node:
                return (
                    edge.start_node_id != edge.end_node_id
                    and edge not in self.edges
                    and start_node.node_type != end_node.node_type
                )
