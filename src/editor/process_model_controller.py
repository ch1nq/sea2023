from src import process_model
from src.editor import command_history, commands


class ProcessModelController:
    def __init__(self, model: process_model.ProcessModel) -> None:
        self.model = model
        self.history = command_history.CommandHistory()

    def execute(self, command: commands.ProcessModelCommand[commands.CommandOutputT]) -> commands.CommandOutputT:
        command.set_model(self.model)
        return self.history.execute(command)

    def undo(self) -> None:
        self.history.undo()

    def redo(self) -> None:
        self.history.redo()

    def clear(self) -> None:
        self.history.clear()
