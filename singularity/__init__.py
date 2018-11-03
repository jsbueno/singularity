from collections.abc import Sequence, MutableSequence
from functools import lru_cache
from types import SimpleNamespace
import datetime
import json
import numbers

import dateparser



class Field:
    name = ""
    type = object

    def __get__(self, instance, owner):
        if not instance:
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
            raise TypeError(f"Field '{self.name}' of '{owner.__name__}' instances must be set to an instance of '{self.type.__name__}'")

    def json(self, value):
        return value


class StringField(Field):
    type = str
    def __init__(self, options=None, **kwargs):
        self.options = options
        super().__init__(**kwargs)

    def __set__(self, instance, value):
        if self.options and not value in self.options:
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

    def __repr__(self):
        return repr(self._data)


class ListField(Field):
    def __init__(self, type_=object,**kwargs):
        self.type = type_
        super().__init__(**kwargs)

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance._data.setdefault(self.name, TypedSequence(self.type))

    def __set__(self, instance, value):
        super().__set__(instance, TypedSequence(self.type, value))

    def _check(self, owner, value):
        if not isinstance(value, TypedSequence) or value.type != self.type:
            raise TypeError(f"Values for field '{owner.__name__}.{self.name!r}' must be a TypeSequence of {self.type!r}")

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
    def __init__(self, getter, setter=None, **kwargs):
        super().__init__(**kwargs)
        self.getter = getter
        self.setter = setter

    def __get__(self, instance, owner):
        if not instance:
            return self
        return self.getter(instance)

    def __set__(self, instance, value):
        if not self.setter:
            raise TypeError("Attribute not setable")
        self.setter(instance, value)


class DataContainer2:
    def __init__(self, parent, instance, owner):
        self._parent = parent
        self._instance = instance
        self._owner = owner

    def __getattr__(self, attr):
        if attr not in self._owner.m.fields:
            raise AttributeError
        attr = self._parent.__dict__[attr]
        return attr.__get__(self._instance, self._owner)

    def __setattr__(self, attr, value):
        if attr in ["_parent",  "_instance",  "_owner"] or attr not in self._owner.m.fields:
            return super().__setattr__(attr, value)
        attr = self._parent.__dict__[attr]
        attr.__set__(self._instance, value)

    def __delattr__(self, attr):
        if attr not in self._instance._data:
            raise AttributeError
        attr = self._parent.__dict__[attr]
        return attr.__delete__(self._instance)

    def __dir__(self):
        return list(self._instance.m.defined_fields() if self._instance else self._owner.m.defined_fields())



class DataContainer:
    @lru_cache()
    def __get__(self, instance, owner):
        return DataContainer2(parent=self, instance=instance, owner=owner)


class Instrumentation:
    parent = None

    def __init__(self, owner=None):
        self.owner = owner

    def _bind(self, parent_instance):
        instance = type(self)()
        # TODO: use a cascading dict:
        instance.__dict__ = self.__dict__.copy()
        instance.parent = parent_instance
        return instance

    def json(self, serialize=False):
        sentinel = object()
        result = {}
        for field_name, field in self.fields.items():
            value = getattr(self.parent.d, field_name, sentinel)
            if value is not sentinel:
                result[field_name] = field.json(value)
        return result if not serialize else json.dumps(result)

    def from_json(self, data, strict=False):
        if isinstance(data, str):
            data = json.loads(data)
        instance = self.owner()
        for key, value in data.items():
            field = self.fields.get(key)
            if isinstance(field, ComputedField):
                continue
            if hasattr(field, "from_json"):
                value = field.from_json(value)
            elif hasattr(field, "m"):
                value = field.m.from_json(value)

            if strict and field is None:
                raise KeyError(f"Unknown field {key!r}")

            setattr(instance.d, key, value)
        return instance

    @lru_cache()
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self._bind(instance)

    def defined_fields(self):
        if not self.parent:
            yield from self.fields.keys()
            return None
        for field_name, field in self.fields.items():
            if field_name in self.parent._data or isinstance(field, ComputedField):
                yield field_name

    def copy(self):
        if not self.parent:
            raise TypeError("Only instances of dataclasses can be copied")
        instance = self.owner()
        instance._data = self.parent._data.copy()
        return instance

    def deepcopy(self, memo=None):
        from copy import deepcopy
        if not self.parent:
            raise TypeError("Only instances of dataclasses can be deep-copied")
        instance = self.owner()
        instance._data = deepcopy(self.parent._data, memo)
        return instance


def parent_field_list(bases):
    for base in bases:
        if not isinstance(base, Meta):
            continue
        for field_name, field in base.m.fields:
            yield field_name, field


class Meta(type):

    # There is no '__prepare__' method, as in Python 3.6+,
    # class attributes are ordered by default.
    # otherwise, __prepare__ should return an OrderedDict

    def __new__(metacls, name, bases, attrs, strict=False, **kwargs):

        container = DataContainer()
        for field_name, field in parent_field_list(bases):
            fields[field_name] = field
            # Avoid triggering descriptor mechanisms
            container.__dict__[field_name] = field

        for attr_name, value in list(attrs.items()):
            if isinstance(value, Field):
                container.__dict__[attr_name] = value
                if strict:
                    del attrs[attr_name]

        if strict:
            slots = set(attrs.get("__slots__", ()))
            slots.update({"m", "d", "_data"})
            attrs["__slots__"] = tuple(slots)

        cls = super().__new__(metacls, name, bases, attrs, **kwargs)

        cls.d = container
        cls.m = Instrumentation(owner=cls)
        cls.m.strict = strict
        cls.m.fields = container.__dict__

        if strict:
            for field_name, field in cls.m.fields.items():
                field.__set_name__(cls, field_name)

        return cls


class Base(metaclass=Meta):
    __slots__ = ()
    def __init__(self, *args, **kwargs):
        self._data = {}
        seem = set()
        for field_name, arg in zip(self.m.fields, args):
            setattr(self.d, field_name, arg)
            seem.add(field_name)

        for field_name, arg in kwargs.items():
            if field_name in seem:
                raise TypeError(f"Argument {field_name!r} passed twice")
            setattr(self.d, field_name, arg)

    def __iter__(self):
        yield from self.m.defined_fields()

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        sentinel = object()
        return all(
            getattr(self.d, field_name, sentinel) == getattr(other.d, field_name, sentinel)
            for field_name, field in self.m.fields.items()
            if not isinstance(field, ComputedField)
        )

    def __hash__(self):
        # Needed for caching the container object.
        return hash(id(self))

    def __repr__(self):
        return "{0}({1})".format(
            self.__class__.__name__,
            ', '.join(f"{name}={value}" for name, value in self._data.items())
        )

    def __copy__(self):
        return self.m.copy()

    def __deepcopy__(self, memo=None):
        return self.m.deepcopy(memo)

    def __getstate__(self):
        return self._data

    def __setstate__(self, state):
        self._data = state



