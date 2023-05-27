from src.editor import ProcessModelCommand, UndoableCommand, CommandOutputT


class CommandHistory:
    def __init__(self) -> None:
        self._commands: list[ProcessModelCommand] = []
        self._index: int = -1

    def execute(self, command: ProcessModelCommand[CommandOutputT]) -> CommandOutputT:
        output = command.execute()
        if isinstance(command, UndoableCommand):
            self._commands = self._commands[: self._index + 1] + [command]
            self._index += 1
        return output

    def undo(self) -> None:
        if self.can_undo:
            self._commands[self._index].undo()
            self._index -= 1

    def redo(self) -> None:
        if self.can_redo:
            self._index += 1
            self._commands[self._index].redo()

    def clear(self) -> None:
        self._commands = []
        self._index = -1

    @property
    def can_undo(self) -> bool:
        return self._index >= 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._commands) - 1

    @property
    def index(self) -> int:
        return self._index

    @property
    def commands(self) -> list[ProcessModelCommand]:
        return self._commands

    @property
    def current_command(self) -> ProcessModelCommand:
        return self._commands[self._index]
