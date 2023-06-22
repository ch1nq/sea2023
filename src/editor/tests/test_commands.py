import pytest
from src.editor import commands
from src.editor import process_model_controller
from src.process_model import process_model
from src.process_model import petri_net


@pytest.fixture
def model():
    _model = process_model.PetriNet(id=1, model_type=process_model.ProcessModelType.PETRI_NET)
    _model.add_node(
        petri_net.PetriNetNode(
            id=process_model.NodeId(1),
            position=process_model.Point(x=0, y=0),
            name="Node#1",
            node_type=petri_net.NodeType.PLACE,
        )
    )
    _model.add_node(
        petri_net.PetriNetNode(
            id=process_model.NodeId(2),
            position=process_model.Point(x=10, y=10),
            name="Node#2",
            node_type=petri_net.NodeType.TRANSITION,
        )
    )
    _model.add_edge_from_values(
        start_node_id=process_model.NodeId(1),
        end_node_id=process_model.NodeId(2),
    )
    return _model


@pytest.mark.parametrize(
    "command",
    [
        commands.CreateNodeCommand(node_id=3, x=20, y=20, node_kwargs=dict(node_type=petri_net.NodeType.PLACE)),
        commands.CreateEdgeCommand(start_node_id=process_model.NodeId(2), end_node_id=process_model.NodeId(1)),
        commands.DeleteNodeCommand(node_id=process_model.NodeId(1)),
        commands.DeleteEdgeCommand(edge_id=process_model.EdgeId((process_model.NodeId(1), process_model.NodeId(2)))),
        commands.MoveNodeCommand(node_id=process_model.NodeId(1), x=2, y=3),
        commands.ClearModelCommand(),
        commands.UpdateInspectablesCommand(node_id=process_model.NodeId(1), node_kwargs={"name": "New Name"}),
    ],
)
def test_command_changes_model(model: process_model.ProcessModel, command: commands.ProcessModelCommand):
    command.set_model(model)

    model_pre_command = model._serialize_to_dict()
    command.execute()
    model_post_command = model._serialize_to_dict()
    assert model_pre_command != model_post_command

    command.undo()
    model_post_undo = model._serialize_to_dict()
    assert model_pre_command == model_post_undo


def test_create_node_command(model: process_model.ProcessModel):
    command = commands.CreateNodeCommand(x=20, y=20, node_kwargs=dict(node_type=petri_net.NodeType.PLACE))
    command.set_model(model)

    node = command.execute()
    node_id = node.id
    assert node.position == process_model.Point(x=20, y=20)
    assert node.node_type == petri_net.NodeType.PLACE
    assert model.get_node(node_id) is not None

    command.undo()
    assert model.get_node(node_id) is None


def test_create_edge_command(model: process_model.ProcessModel):
    command = commands.CreateEdgeCommand(start_node_id=process_model.NodeId(2), end_node_id=process_model.NodeId(1))
    command.set_model(model)

    expected_id = process_model.EdgeId((process_model.NodeId(2), process_model.NodeId(1)))
    expected_edge = petri_net.PetriNetEdge(
        id=expected_id, start_node_id=process_model.NodeId(2), end_node_id=process_model.NodeId(1), ball_count=0
    )
    assert command.execute() == expected_edge
    assert model.get_edge(expected_id) is not None

    command.undo()
    assert model.get_edge(expected_id) is None


def test_delete_node_command(model: process_model.ProcessModel):
    command = commands.DeleteNodeCommand(node_id=process_model.NodeId(1))
    command.set_model(model)

    assert command.execute() == model.get_node(process_model.NodeId(1))
    assert model.get_node(process_model.NodeId(1)) is None

    command.undo()
    assert model.get_node(process_model.NodeId(1)) is not None


def test_delete_edge_command(model: process_model.ProcessModel):
    command = commands.DeleteEdgeCommand(
        edge_id=process_model.EdgeId((process_model.NodeId(1), process_model.NodeId(2)))
    )
    command.set_model(model)

    assert command.execute() == model.get_edge(process_model.EdgeId((process_model.NodeId(1), process_model.NodeId(2))))
    assert model.get_edge(process_model.EdgeId((process_model.NodeId(1), process_model.NodeId(2)))) is None

    command.undo()
    assert model.get_edge(process_model.EdgeId((process_model.NodeId(1), process_model.NodeId(2)))) is not None


def test_move_node_command(model: process_model.ProcessModel):
    command = commands.MoveNodeCommand(node_id=process_model.NodeId(1), x=2, y=3)
    command.set_model(model)

    command.execute()
    assert model.get_node(process_model.NodeId(1)).position == process_model.Point(x=2, y=3)

    command.undo()
    assert model.get_node(process_model.NodeId(1)).position == process_model.Point(x=0, y=0)


def test_clear_model_command(model: process_model.ProcessModel):
    command = commands.ClearModelCommand()
    command.set_model(model)

    command.execute()
    assert model.get_node(process_model.NodeId(1)) is None
    assert model.get_node(process_model.NodeId(2)) is None
    assert model.get_edge(process_model.EdgeId((process_model.NodeId(1), process_model.NodeId(2)))) is None

    command.undo()
    assert model.get_node(process_model.NodeId(1)) is not None
    assert model.get_node(process_model.NodeId(2)) is not None
    assert model.get_edge(process_model.EdgeId((process_model.NodeId(1), process_model.NodeId(2)))) is not None


def test_update_inspectables_command(model: process_model.ProcessModel):
    command = commands.UpdateInspectablesCommand(node_id=process_model.NodeId(1), node_kwargs={"name": "New Name"})
    command.set_model(model)

    command.execute()
    assert model.get_node(process_model.NodeId(1)).name == "New Name"

    command.undo()
    assert model.get_node(process_model.NodeId(1)).name == "Node#1"


def test_command_history(model: process_model.ProcessModel):
    controller = process_model_controller.ProcessModelController(model)

    initial_model = model._serialize_to_dict()
    controller.execute(commands.CreateNodeCommand(x=20, y=20, node_kwargs=dict(node_type=petri_net.NodeType.PLACE)))
    controller.execute(
        commands.CreateEdgeCommand(start_node_id=process_model.NodeId(2), end_node_id=process_model.NodeId(1))
    )
    controller.execute(
        commands.DeleteEdgeCommand(edge_id=process_model.EdgeId((process_model.NodeId(2), process_model.NodeId(1))))
    )
    controller.execute(
        commands.UpdateInspectablesCommand(node_id=process_model.NodeId(1), node_kwargs={"name": "New Name"})
    )
    controller.execute(commands.MoveNodeCommand(node_id=process_model.NodeId(1), x=200, y=300))
    controller.execute(commands.DeleteNodeCommand(node_id=process_model.NodeId(1)))
    controller.execute(commands.ClearModelCommand())
    edited_model = model._serialize_to_dict()

    controller.undo()
    controller.undo()
    controller.undo()
    controller.undo()
    controller.undo()
    controller.undo()
    controller.undo()
    assert model._serialize_to_dict() == initial_model

    controller.redo()
    controller.redo()
    controller.redo()
    controller.redo()
    controller.redo()
    controller.redo()
    controller.redo()
    assert model._serialize_to_dict() == edited_model
