from abc import ABCMeta
from collections.abc import MutableSequence
import datetime
import numbers
import types
import uuid

import dateparser


_SENTINEL = object()


def deferred_type_factory(name):
    module_name = ""
    if "." in name and not module_name:
        name, module_name = name.rsplit(".", 1)

    class DeferredType(metaclass=ABCMeta):

        singularity_deferred_type = True

        @classmethod
        def register(cls, owner):
            if not cls.module_name:
                cls.module_name = owner.__module__
            cls.qualname = owner.__qualname__
            # cls.owner = owner

        @classmethod
        def __subclasshook__(cls, subcls):
            if subcls.__module__ == cls.module_name and subcls.__name__ == cls.__name__:
                # FIXME: here lies the possibility of replacing the reference to this class
                # in the owner type for the target class.  This would bind the type of the
                # first assigned field to the actual type.

                # self.owner.type = subcls
                return True
            for supercls in subcls.__mro__[1:-2]:
                if cls.__subclasshook__(supercls):
                    return True
            return False

    DeferredType.__name__ = name
    DeferredType.module_name = module_name

    return DeferredType


def _wraptype(type_):
    if isinstance(type_, type):
        return type_
    if not isinstance(type_, str):
        raise TypeError("Field types must be either a type or a string")

    return deferred_type_factory(type_)


class Field:
    name = ""
    type = object

    def __init__(self, default=_SENTINEL):
        if default is not _SENTINEL:
            self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return instance._data[self.name]
        except KeyError as error:
            if not hasattr(self, "default"):
                raise AttributeError from error
            return self.setdefault(instance=instance)

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

    def setdefault(self, default=_SENTINEL, instance=None):
        if default is _SENTINEL:
            default = self.default

        if callable(default):
            # Optionally pass instance as argument to
            # a default method or function:
            default_func = default
            if ( # not a builtin method:
                not isinstance(default_func,(types.BuiltinFunctionType, types.MethodWrapperType))
                    ) and (( # is method expecting instance
                        isinstance(default_func, types.MethodType) and
                        default_func.__code__.co_argcount >= 2
                    ) or ( # is function expecting instance
                        isinstance(default_func, types.FunctionType) and
                        default_func.__code__.co_argcount >= 1
                    ) or ( # Other callable object expecting instance
                        hasattr(default_func.__call__, '__code__') and
                        default_func.__call__.__code__.co_argcount >= 2
                    )):
                default = default_func(instance=instance)
            else:
                default = default_func()

        # ATTENTION: when workflow permissions are in place, this might trigger
        # permission problems - but remember - default parameter
        # setting is an action of the field creator (be it in code, or dynamic class creation)
        # not from the one querying the system right now
        self.__set__(instance, default)
        return default

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


class UUIDField(Field):
    type = uuid.UUID

    def json(self, value):
        return str(value)

    @classmethod
    def from_json(cls, value):
        return uuid.UUID(value)

    def default(self, instance=None):
        return uuid.uuid4()


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
        return f"<{self.type.__name__}>{self._data!r}"

"""
# TODO: Postponned until we have rich-object fields .
class SmartSequence(TypedSequence):
    def __init__(self, type_, owner_type, reciprocal_field=None, initial_values=None):
        self.type = type_
        self.owner_type = owner_type

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
        return f"<{self.type.__name__}>{self._data!r}"
"""

class DeferrableTypeMixin:
    def __init__(self, type_=object, **kwargs):
        self.type = _wraptype(type_)
        super().__init__(**kwargs)

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        if hasattr(self.type, "singularity_deferred_type"):
            self.type.register(owner)


class TypeField(DeferrableTypeMixin, Field):

    def json(self, value):
        return self.type.m.json(obj=value)

    def from_json(self, value):
        return self.type.m.from_json(value)

# TODO
class EdgeField(DeferrableTypeMixin, Field):
    pass
"""
    def __init__(self, reciprocal_field=None, **kwargs):
        self.reciprocal_field = reciprocal_field
        super().__init__(**kwargs)

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        if issubclass(owner, self.type):
            self.reciprocal_field = name
        elif not self.reciprocal_field:
            raise TypeError("EdgeFields must have a reciprocal_field name to connect different classes")
        self.owner = owner

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if self.name not in instance._data:
            instance._data[self.name] = SmartSequence(self.type, owner, self.reciprocal_field)
        return instance._data[self.name]

    def __set__(self, instance, value):
        super().__set__(
            instance, SmartSequence(self.type, self.owner, self.reciprocal_field, value)
        )

    def json(self, value):
        return self.type.m.json(obj=value)

    def from_json(self, value):
        return self.type.m.from_json(value)
"""

class ListField(DeferrableTypeMixin, Field):
    def _check(self, owner, value):
        if not isinstance(value, TypedSequence) or value.type != self.type:
            raise TypeError(f"Values for field '{owner.__name__}.{self.name!r}' "
                            f"must be a TypeSequence of {self.type!r}")

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance._data.setdefault(self.name, TypedSequence(self.type))

    def __set__(self, instance, value):
        super().__set__(instance, TypedSequence(self.type, value))

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
    def __init__(self, getter=None, setter=None, **kwargs):
        super().__init__(**kwargs)
        if getter:
            self.getter = getter
        elif not hasattr(self, "getter"):
            raise TypeError("A 'getter' callable must be passed in, or defined as method")
        self.setter_func = setter

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.getter(instance)

    def __set__(self, instance, value):
        if not self.setter:
            raise TypeError("Attribute not setable")
        self.setter_func(instance, value)


class IDField(ComputedField, UUIDField):
    # UUIDField Inheritance is here to get the serializer methods.

    def getter(self, instance):
        # ID value is set at Base object __init__
        return instance.__dict__["id"]

    def __set_name__(self, owner, name):
        if name != "id":
            raise TypeError("IDField is reserved to unique instance IDs. Use UUIDField instead")
        super().__set_name__(owner, name)
