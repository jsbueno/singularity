from collections import OrderedDict

import uuid
import sqlite3
import datetime
import numbers
import uuid


try:
    import psycopg2
except ImportError:
    psycopg2 = None

engines = {
    "sqlite": sqlite3
}

ENGINE = "sqlite"

class BaseField:
    counter = 0
    type_ = object
    auto_commit = False
    def __init__(self, *args, **kw):
        self.counter = __class__.counter = __class__.counter + 1

    def __get__(self, instance,  owner):
        if instance is None:
            return self
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if not isinstance(value, self.type_):
            raise TypeError("{} is not an instance of {}".format(value, self.type_))
        instance.__dict__[self.name] = value

    def __delete__(self, instance):
        del instance.__dict__[self.name]

    def serialize(self, instance):
        return self.__get__(instance, instance.__class__)


class Field(BaseField):
    def __set__(self, instance, value):
        super().__set__(instance, value)
        if self.auto_commit:
            self.owner.commit()


class TextField(Field):
    type_ = str


class NumberField(Field):
    type_ = numbers.Number


class DateField(Field):
    type_ = datetime.date


class DateTimeField(Field):
    type_=  datetime.datetime

class UUIDField(Field):
    type_ = uuid.UUID

    def __set__(self, instance, value):
        if isinstance(value, str):
            value = uuid.UUID(value)
        return super().__set__(instance, value)

    def serialize(self, instance):
        value = super().serialize(instance)
        return str(value)

class Engine:
    def __init__(self, backend):
        self.backend = backend

    def create_table(self, model):
        raise NotImplementedError

    def upsert(self, instance):
        pass


class Meta(type):
    registry = {}
    def __new__(metacls, name, bases, dct):
        for name, value in dct.items():
            if isinstance(value, Field):
                value.name = name
        cls = type.__new__(metacls, name, bases, dct)
        cls._manager = SingularityManager(cls)
        registry.setdefault(name, []).append(cls)
        return cls



class SingularityManager:

    def __init__(self, owner):
        self.owner = owner

    @property
    def schema(self):
        schema = OrderedDict()
        for field in sorted((f for f in self.owner.__dict__.values() if isinstance(f, Field)), key=lambda f: f.counter):
            schema[field.name] = field.type_
        return schema


class Base(metaclass=Meta):

    _manager = None


