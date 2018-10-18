from datetime import date

import pytest

import singularity as S

def test_declare_dataclass():
    class Pet(S.Base):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        # age = S.ComputedField(lambda self: (date.today() - self.birthday).days // 365)

    p = Pet("Rex", "dog", date(2015, 1, 1))
    assert p.name == "Rex"
    assert p.species == "dog"
    assert p.birthday == date(2015, 1, 1)


@pytest.fixture
def dog():
    class Pet(S.Base):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        age = S.ComputedField(lambda self: (date.today() - self.birthday).days // 365)

    return Pet("Rex", "dog", date(2015, 1, 1))


def test_computed_field(dog):
    assert dog.age == (date.today().year - 2015)


def test_declare_nested_dataclass(dog):

    class Person(S.Base):
        name = S.StringField()
        pets = S.ListField(type(dog))

    pe = Person("João")
    pe.pets.append(dog)

    assert pe.pets[0].name == 'Rex'


