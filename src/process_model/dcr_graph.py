import enum

from src import process_model as pm


class DcrGraphNode(pm.Node):
    name: str
    description: str = ""


class DcrGraphEdge(pm.Edge):
    pass


class DcrGraph(pm.ProcessModel[DcrGraphNode, DcrGraphEdge]):
    model_type = pm.ProcessModelType.DCR_GRAPH

    def node_factory(self, node_id: pm.NodeId, position: pm.Point, **kwargs) -> DcrGraphNode:
        return DcrGraphNode(id=node_id, position=position, name=f"Epic DCR Node #{node_id}")

    def edge_factory(self, *args, **kwargs) -> DcrGraphEdge:
        return DcrGraphEdge(*args, **kwargs)

    def is_valid_edge(self, edge: DcrGraphEdge) -> bool:
        """Check if an edge can be added to the DCR graph."""
        return True
