from collections.abc import Sequence, MutableSequence
from types import SimpleNamespace
import datetime
import numbers



class Field:
    name = ""
    type = object

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance._data[self.name]

    def __set__(self, instance, value):
        if not isinstance(value, self.type):
            raise TypeError(f"Field '{self.name}' of '{type(instance).__name__}' instances must be set to an instance of '{self.type.__name__}'")
        instance._data[self.name] = value

    def __set_name__(self, owner, name):
        self.owner = owner
        self.name = name


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


class DateTimeField(Field):
    type = datetime.datetime


class TypedSequence(MutableSequence):
    def __init__(self, type_, initial_values=None):
        self.type = type_
        self._data = []
        if initial_values:
            self.extend(initial_values)

    def _check(self, value):
        if not isinstance(value, self.type):
            raise TypeError(f"Only values of type '{type.__name__}' can be inserted!")

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

    def insert(self, index, value):
        self._check(value)
        self._data.insert(index, value)

    def __repr__(self):
        return repr(self._data)


class ListField(Field):
    def __init__(self, type_=object, **kwargs):
        self.type = type_
        super().__init__(**kwargs)

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance._data.setdefault(self.name, TypedSequence(self.type))

    def __set__(self, instance, value):
        raise TypeError(f"ListFields can't be set!")


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


class DataContainer:
    def __get__(self, instance, owner):
        return DataContainer2(parent=self, instance=instance, owner=owner)


def mro_list(cls):
    for supercls in cls.__mro__[::-1]:
        for attr_name in supercls.__dict__.keys():
            if attr_name[:2] == "__" and attr_name[-2:] == "__":
                continue
            yield attr_name


class Base:
    def __init__(self, *args, **kwargs):
        self._data = {}
        for field_name, arg in zip(self.m.fields, args):
            setattr(self, field_name, arg)

        for field_name, arg in kwargs.items():
            setattr(self, field_name, arg)


    def __init_subclass__(cls, strict=False, **kwargs):
        super().__init_subclass__(**kwargs)

        fields = []
        cls.d = DataContainer()
        for attr_name in mro_list(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, Field) and not attr_name in fields:
                fields.append(attr_name)
                cls.__dict__["d"].__dict__[attr_name] = attr
                if strict:
                    try:
                        pass
                        # del cls.__dict__[attr_name]
                    except AttributeError:
                        pass

        cls.m = SimpleNamespace()
        cls.m.fields = fields

    def __repr__(self):
        return "{0}({1})".format(
            self.__class__.__name__,
            ', '.join(f"{name}={value}" for name, value in self._data.items())
        )




