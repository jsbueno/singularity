from collections.abc import MutableSequence
import datetime
import numbers

import dateparser


_SENTINEL = object()


class Field:
    name = ""
    type = object

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return instance._data[self.name]
        except KeyError as error:
            raise AttributeError from error

    def __set__(self, instance, value):
        self._check(type(instance), value)
        instance._data[self.name] = value

    def __delete__(self, instance):
        del instance._data[self.name]

    def __set_name__(self, owner, name):
        self.owner = owner
        self.name = name

    def _check(self, owner, value):
        if not isinstance(value, self.type):
            raise TypeError(f"Field '{self.name}' of '{owner.__name__}' "
                            f"instances must be set to an instance of '{self.type.__name__}'")

    def json(self, value):
        return value


class StringField(Field):

    type = str

    def __init__(self, options=None, **kwargs):
        self.options = options
        super().__init__(**kwargs)

    def __set__(self, instance, value):
        if self.options and value not in self.options:
            raise ValueError(f"Value must be set to one of {self.options!r}")
        return super().__set__(instance, value)


class NumberField(Field):
    type = numbers.Number


class DateField(Field):
    type = datetime.date

    def json(self, value):
        return value.isoformat()

    @classmethod
    def from_json(cls, value):
        try:
            year, day, month = map(int, value.split('-'))
            return datetime.date(year, day, month)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid date string {value!r}")


class DateTimeField(Field):
    type = datetime.datetime

    def json(self, value):
        return value.isoformat()

    @classmethod
    def from_json(cls, value):
        try:
            return dateparser.parse(value)
        except ValueError:
            raise ValueError(f"Invalid datetime string {value!r}")


class TypedSequence(MutableSequence):
    def __init__(self, type_, initial_values=None):
        self.type = type_
        self._data = []
        if initial_values:
            self.extend(initial_values)

    def _check(self, value):
        if not isinstance(value, self.type):
            raise TypeError(f"Only values of type '{self.type.__name__}' can be inserted!")

    def __getitem__(self, index):
        return self._data.__getitem__(index)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            for item in value:
                self._check(item)
            return self._data.__setitem__(index, value)
        self._check(value)
        self._data[index] = value

    def __delitem__(self, index):
        self._data.__delitem__(index)

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if not isinstance(other, TypedSequence) or self.type != other.type or len(self) != len(other):
            return False
        return all(self_item == other_item for self_item, other_item in zip(self, other))

    def insert(self, index, value):
        self._check(value)
        self._data.insert(index, value)

    def clear(self):
        self._data.clear()

    def __repr__(self):
        return repr(self._data)


class TypeField(Field):
    def __init__(self, type_=object, **kwargs):
        self.type = type_
        super().__init__(**kwargs)

    def json(self, value):
        return self.type.m.json(obj=value)

    def from_json(self, value):
        return self.type.m.from_json(value)


class ListField(Field):
    def __init__(self, type_=object, **kwargs):
        self.type = type_
        super().__init__(**kwargs)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance._data.setdefault(self.name, TypedSequence(self.type))

    def __set__(self, instance, value):
        super().__set__(instance, TypedSequence(self.type, value))

    def _check(self, owner, value):
        if not isinstance(value, TypedSequence) or value.type != self.type:
            raise TypeError(f"Values for field '{owner.__name__}.{self.name!r}' "
                            f"must be a TypeSequence of {self.type!r}")

    def json(self, value):
        if hasattr(self.type, "json"):
            value = [self.type.json(item) for item in value]
        elif hasattr(self.type, "m"):
            value = [item.m.json() for item in value]
        return value

    def from_json(self, value):
        if hasattr(self.type, "from_json"):
            value = [self.type.from_json(item) for item in value]
        elif hasattr(self.type, "m"):
            value = [self.type.m.from_json(item) for item in value]
        return value


class ComputedField(Field):
    # Can be used as a decorator for the getter method.
    def __init__(self, getter, setter=None, **kwargs):
        super().__init__(**kwargs)
        self.getter = getter
        self.setter_func = setter

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.getter(instance)

    def __set__(self, instance, value):
        if not self.setter:
            raise TypeError("Attribute not setable")
        self.setter_func(instance, value)
