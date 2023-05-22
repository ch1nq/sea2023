import random
import abc
import enum
import datetime
import pydantic

from src import process_model


SimulationId = int


class SimulationStatus(enum.Enum):
    QUEUED = enum.auto()
    RUNNING = enum.auto()
    FINISHED = enum.auto()
    FAILED = enum.auto()


class SimulationParameters(pydantic.BaseModel):
    pass


class SimulationResult(pydantic.BaseModel):
    pass


class SimulationBase(pydantic.BaseModel, abc.ABC):
    id: SimulationId
    model_id: process_model.ModelId
    parameters: SimulationParameters

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

    @property
    @abc.abstractmethod
    def status(self) -> SimulationStatus:
        ...


class QueuedSimulation(SimulationBase):
    def start(self) -> "RunningSimulation":
        return RunningSimulation(
            id=self.id,
            model_id=self.model_id,
            parameters=self.parameters,
            start_time=datetime.datetime.now(),
        )

    def status(self) -> SimulationStatus:
        return SimulationStatus.QUEUED


class RunningSimulation(SimulationBase):
    start_time: datetime.datetime

    def finish(self, result: SimulationResult) -> "FinishedSimulation":
        return FinishedSimulation(
            id=self.id,
            model_id=self.model_id,
            parameters=self.parameters,
            start_time=self.start_time,
            end_time=datetime.datetime.now(),
            result=result,
        )

    def status(self) -> SimulationStatus:
        return SimulationStatus.RUNNING


class FinishedSimulation(RunningSimulation):
    end_time: datetime.datetime
    result: SimulationResult | None = None

    def status(self) -> SimulationStatus:
        if self.result is None:
            return SimulationStatus.FAILED
        else:
            return SimulationStatus.FINISHED


Simulation = QueuedSimulation | RunningSimulation | FinishedSimulation


class Simulator:
    QUEUE_MAX_LENGTH = 1000
    queued_simulations: list[QueuedSimulation] = []
    running_simulations: list[RunningSimulation] = []
    finished_simulations: list[FinishedSimulation] = []

    def new_id(self) -> int:
        id = random.randint(0, self.QUEUE_MAX_LENGTH)
        while id in self.queued_simulations or id in self.running_simulations or id in self.finished_simulations:
            id = random.randint(0, self.QUEUE_MAX_LENGTH)
        return id

    def queue_simulation(
        self, model_id: process_model.ModelId, simulation_parameters: SimulationParameters
    ) -> QueuedSimulation:
        simulation = QueuedSimulation(id=self.new_id(), model_id=model_id, parameters=simulation_parameters)
        self.queued_simulations.append(simulation)
        return simulation

    def start_simulation(self, simulation: QueuedSimulation) -> RunningSimulation:
        self.queued_simulations.remove(simulation)
        running_simulation = simulation.start()
        self.running_simulations.append(running_simulation)
        return running_simulation

    def finish_simulation(self, simulation: RunningSimulation, result: SimulationResult) -> FinishedSimulation:
        self.running_simulations.remove(simulation)
        finished_simulation = simulation.finish(result)
        self.finished_simulations.append(finished_simulation)
        return finished_simulation
