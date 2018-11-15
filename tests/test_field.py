from datetime import date, datetime, timedelta
import uuid

import pytest

import singularity as S


def test_field_is_descriptor():
    assert isinstance(S.Field, type) and hasattr(S.Field, '__get__')


def test_field_get_on_class_returns_self():
    class A:
        b = S.Field()
    assert isinstance(A.b, S.Field)


def test_field_name_is_set():
    class A:
        b = S.Field()
    assert A.b.name == 'b'
    assert A.b.owner is A


def test_field_stores_and_retrieves_value():
    class A:
        def __init__(self):
            self._data = {}
        b = S.Field()

    a = A()
    sentinel = object()
    a.b = sentinel
    assert a.b is sentinel
    assert a._data['b'] is sentinel


def test_field_has_base_json_serializer():
    f = S.Field()
    assert f.json(0) is 0


def test_field_derivative_asserts_value_type():
    class F(S.Field):
        type = int

    class A:
        def __init__(self):
            self._data = {}
        b = F()

    a = A()

    with pytest.raises(TypeError):
        a.b = ""

    a.b = 10
    assert a.b == 10


def test_default_value_for_fields():
    class Test(S.Base, strict=True):
        name = S.StringField()

    t = Test()
    assert not hasattr(t, "name")
    with pytest.raises(AttributeError):
        t.name

    class Test2(S.Base, strict=True):
        name = S.StringField(default="")

    t = Test2()
    assert hasattr(t.d, "name")
    assert t.d.name == ""


def test_default_callable_for_fields_builtin_function():
    class Test(S.Base, strict=True):
        timestamp = S.DateTimeField(default=datetime.now)

    t = Test()
    assert t.d.timestamp
    assert (datetime.now() - t.d.timestamp).seconds < 2


def test_default_callable_for_fields_function():
    import random
    class Test(S.Base, strict=True):
        number = S.DateTimeField(default=lambda: random.randint(0,10))

    t = Test()
    assert t.d.number
    assert isinstance(t.d.number, int)


def test_default_callable_for_fields_function():
    import random
    class Test(S.Base, strict=True):
        number = S.NumberField(default=lambda: random.randint(1,10))

    t = Test()
    assert t.d.number
    assert isinstance(t.d.number, int)


def test_default_callable_for_fields_function_receives_instance():
    class Test(S.Base, strict=True):
        name = S.StringField(default="João Bueno")
        surname = S.StringField(default=lambda instance: instance.d.name.split()[-1])

    t = Test()
    assert t.d.surname == "Bueno"


def test_default_callable_as_field_methods():
    class Test(S.Base, strict=True):
        other_id = S.UUIDField()

    t = Test()
    assert isinstance(t.d.other_id, uuid.UUID)


def test_default_callable_as_field_method_rceives_instance():
    class CustomField(S.Field):
        def default(self, instance):
            return instance.d.number * 2

    class Test(S.Base, strict=True):
            number = S.NumberField(default=2)
            double = CustomField()

    t = Test()
    assert t.d.double == 4


def test_uuid_field():
    class Test(S.Base, strict=True):
        other_id = S.UUIDField()

    t = Test()
    assert isinstance(t.d.other_id, uuid.UUID)
    t1 = Test.m.from_json(t.m.json())
    assert isinstance(t1.d.other_id, uuid.UUID)
    assert t1.d.other_id == t.d.other_id


# TODO: write more specific tests for field types
