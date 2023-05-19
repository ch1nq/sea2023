import enum

from src import process_model as pm


class FlowchartNodeType(str, enum.Enum):
    START = "start"
    END = "end"
    TASK = "task"
    DECISION = "decision"
    SUBPROCESS = "subprocess"


class FlowchartNode(pm.Node):
    name: str
    node_type: FlowchartNodeType
    description: str = ""


class FlowchartEdge(pm.Edge):
    pass


class Flowchart(pm.ProcessModel[FlowchartNode, FlowchartEdge]):
    model_type = pm.ProcessModelType.FLOWCHART

    def node_factory(
        self, node_id: pm.NodeId, position: pm.Point, node_type: FlowchartNodeType = FlowchartNodeType.START, **kwargs
    ) -> FlowchartNode:
        return FlowchartNode(id=node_id, position=position, node_type=node_type, name=f"Epic DCR Node #{node_id}")

    def edge_factory(self, *args, **kwargs) -> FlowchartEdge:
        return FlowchartEdge(*args, **kwargs)

    def is_valid_edge(self, edge: FlowchartEdge) -> bool:
        return True
