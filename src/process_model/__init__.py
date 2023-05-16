from .process_model import *
from .petri_net import *


def model_type_to_class(model_type: ProcessModelType) -> ProcessModel:
    match model_type:
        case ProcessModelType.PETRI_NET:
            return PetriNet
        case _:
            raise NotImplementedError("Model type is not yet implemented")
