import random

import pydantic
from src import process_model as pm


class ToolbarButton(pydantic.BaseModel):
    id: str
    icon: str
    label: str
    color: str = "secondary"
    attributes: dict[str, str] = {}


_TOOLBAR_BUTTONS = {
    "clear": ToolbarButton(
        id="open-clear-modal",
        label="Clear model",
        icon="trash-fill",
        attributes={
            "data-bs-toggle": "modal",
            "data-bs-target": "#clearModal",
        },
    ),
    "delete": ToolbarButton(id="delete", label="Delete", icon="eraser-fill"),
    "connect": ToolbarButton(id="connect", label="Edge", icon="arrow-left-right"),
}


def get_toolbar_buttons(model_type: pm.ProcessModelType) -> list[ToolbarButton]:
    match model_type:
        case pm.ProcessModelType.PETRI_NET:
            return [
                ToolbarButton(id="create-transition", label="Transition", icon="plus-square-fill"),
                ToolbarButton(id="create-place", label="Place", icon="plus-circle-fill"),
                _TOOLBAR_BUTTONS["connect"],
                _TOOLBAR_BUTTONS["delete"],
                _TOOLBAR_BUTTONS["clear"],
            ]
        case pm.ProcessModelType.DCR_GRAPH:
            return [
                ToolbarButton(id="create-activity", label="Activity", icon="plus-square-fill"),
                ToolbarButton(id="create-event", label="Event", icon="plus-circle-fill"),
                ToolbarButton(id="create-case", label="Case", icon="wallet-fill"),
                _TOOLBAR_BUTTONS["connect"],
                _TOOLBAR_BUTTONS["delete"],
                _TOOLBAR_BUTTONS["clear"],
            ]
        case _:
            return []
