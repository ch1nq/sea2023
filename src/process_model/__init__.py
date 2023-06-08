import enum
import pydantic
import pathlib


class ProcessModelBase(pydantic.BaseModel):
    model_type: "ProcessModelType"


class ProcessModelType(str, enum.Enum):
    PETRI_NET = "petri_net"
    DCR_GRAPH = "dcr_graph"
    FLOWCHART = "flowchart"

    @classmethod
    def from_path(cls, path: pathlib.Path) -> "ProcessModelType":
        return process_model.ProcessModelBase.parse_file(str(path)).model_type


ProcessModelBase.update_forward_refs()

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
