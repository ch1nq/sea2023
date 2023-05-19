import abc
import enum
from functools import partial
from typing import Any, Generic, TypeVar

import pydantic


FieldType = TypeVar("FieldType")


class InspectableField(pydantic.generics.GenericModel, Generic[FieldType], abc.ABC):
    name: str
    value: FieldType
    inspector_type: str | None = None
    mutable: bool = True

    @property
    def label(self):
        return self.name.replace("_", " ").capitalize()

    def set_value(self, value: FieldType) -> FieldType:
        self.value = value
        setattr(self.__class__, self.name, value)
        return value


class TextInspectableField(InspectableField[str]):
    inspector_type = "text"


class HiddenInspectableField(InspectableField[FieldType]):
    inspector_type: None = None
    mutable: bool = False


class InfoInspectableField(InspectableField[Any]):
    inspector_type = "info"
    mutable: bool = False


class NumberInspectableField(InspectableField[int | float]):
    inspector_type = "number"


class EnumInspectableField(InspectableField[enum.Enum]):
    inspector_type = "select"
    options: list[tuple[str, Any]] = pydantic.Field(default_factory=list)
    enum_type: type[enum.Enum] = pydantic.Field(default=enum.Enum)

    @property
    def options(self):
        return [(option.name, option.value) for option in self.enum_type]

    def set_value(self, value: enum.Enum):
        return super().set_value(self.enum_type(value))


class InspectorMixin:
    @property
    def inspectables(self) -> dict[str, InspectableField]:
        field_types = self.field_types()
        excluded_fields = [field_name for field_name, field in field_types.items() if field is HiddenInspectableField]
        inspectables = dict()
        for field in self.__fields__.values():
            if field.name not in excluded_fields:
                factory = field_types.get(field.name, self.default_field_factory(field.type_))
                inspectables[field.name] = factory(name=field.name, value=getattr(self, field.name))
        return inspectables

    @property
    def field_types(self) -> dict[str, InspectableField]:
        return {}

    def default_field_factory(self, field_type: type) -> type[InspectableField]:
        if issubclass(field_type, enum.Enum):
            return partial(EnumInspectableField, enum_type=field_type)
        if issubclass(field_type, str):
            return TextInspectableField
        if issubclass(field_type, (int, float)):
            return NumberInspectableField
        else:
            return InfoInspectableField

    def get_inspectables(self) -> list[InspectableField]:
        return self.inspectables.values()

    def set_inspectable(self, name: str, value: Any) -> None:
        inspectable = self.inspectables[name]
        if inspectable.mutable:
            value = self.inspectables[name].set_value(value)
            self.__setattr__(name, value)
