from datetime import date

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


# TODO: write specific tests for field types
