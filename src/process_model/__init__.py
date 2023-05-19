import enum


class ProcessModelType(str, enum.Enum):
    PETRI_NET = "petri_net"
    DCR_GRAPH = "dcr_graph"
    FLOWCHART = "flowchart"


from .process_model import *
from .petri_net import *
from .dcr_graph import *
from .flowchart import *


def model_type_to_class(model_type: ProcessModelType) -> type[ProcessModel]:
    match model_type:
        case ProcessModelType.PETRI_NET:
            return PetriNet
        case ProcessModelType.DCR_GRAPH:
            return DcrGraph
        case ProcessModelType.FLOWCHART:
            return Flowchart
        case _:
            raise NotImplementedError("Model type is not yet implemented")
