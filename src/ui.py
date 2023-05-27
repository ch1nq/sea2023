import pydantic
from src import simulation_engine
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
    "undo": ToolbarButton(id="undo", label="Undo", icon="arrow-counterclockwise", attributes={"disabled": "true"}),
    "redo": ToolbarButton(id="redo", label="Redo", icon="arrow-clockwise", attributes={"disabled": "true"}),
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
                _TOOLBAR_BUTTONS["undo"],
                _TOOLBAR_BUTTONS["redo"],
            ]
        case pm.ProcessModelType.DCR_GRAPH:
            return [
                ToolbarButton(id="create-activity", label="Activity", icon="plus-square-fill"),
                ToolbarButton(id="create-event", label="Event", icon="plus-circle-fill"),
                ToolbarButton(id="create-case", label="Case", icon="wallet-fill"),
                _TOOLBAR_BUTTONS["connect"],
                _TOOLBAR_BUTTONS["delete"],
                _TOOLBAR_BUTTONS["clear"],
                _TOOLBAR_BUTTONS["undo"],
                _TOOLBAR_BUTTONS["redo"],
            ]
        case _:
            return []


class SimulationQueueListItem(pydantic.BaseModel):
    simulation: simulation_engine.Simulation
    color: str
    icon: str
    status: str
    label: str

    @classmethod
    def from_simulation(cls, simulation: simulation_engine.Simulation) -> "SimulationQueueListItem":
        match simulation.status():
            case simulation_engine.SimulationStatus.QUEUED:
                color = "secondary"
            case simulation_engine.SimulationStatus.RUNNING:
                color = "info"
            case simulation_engine.SimulationStatus.FINISHED:
                color = "success"
            case simulation_engine.SimulationStatus.FAILED:
                color = "danger"

        return cls(
            simulation=simulation,
            color=color,
            icon="database-fill-gear",
            status=simulation.status().name,  # type: ignore
            label=str(simulation.id),
        )
