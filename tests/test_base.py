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
    assert p.d.name == "Rex"
    assert p.d.species == "dog"
    assert p.d.birthday == date(2015, 1, 1)
    assert p.name == "Rex"
    assert p.species == "dog"
    assert p.birthday == date(2015, 1, 1)


def test_declare_strict_dataclass():
    class Pet(S.Base, strict=True):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        # age = S.ComputedField(lambda self: (date.today() - self.birthday).days // 365)

    p = Pet("Rex", "dog", date(2015, 1, 1))

    assert p.d.name == "Rex"
    assert p.d.species == "dog"
    assert p.d.birthday == date(2015, 1, 1)

    with pytest.raises(AttributeError):
        assert p.name == "Rex"
    with pytest.raises(AttributeError):
        assert p.species == "dog"
    with pytest.raises(AttributeError):
        assert p.birthday == date(2015, 1, 1)


@pytest.fixture
def dog():
    class Pet(S.Base):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        age = S.ComputedField(lambda self: (date.today() - self.d.birthday).days // 365)

    return Pet("Rex", "dog", date(2015, 1, 1))

@pytest.fixture
def person(dog):
    class Person(S.Base):
        name = S.StringField()
        pets = S.ListField(type(dog))

    pe = Person("João")
    pe.d.pets.append(dog)

    return pe


def test_computed_field(dog):
    assert dog.d.age == (date.today().year - 2015)


def test_str_field_with_options_error_on_unknown_option(dog):
    with pytest.raises(ValueError):
        dog.d.species = "lemur"


def test_declare_nested_dataclass(dog):

    class Person(S.Base):
        name = S.StringField()
        pets = S.ListField(type(dog))

    pe = Person("João")
    pe.d.pets.append(dog)

    assert pe.d.pets[0].name == 'Rex'


def test_list_field_dont_accept_wrong_type(person):
    with pytest.raises(TypeError):
        person.d.pets.append(1)


def test_json_serializing(dog, person):
    dog_json = {
        'name': 'Rex',
        'species': 'dog',
        'birthday': '2015-01-01',
        'age': 3   # FIXME: this will break on 2019-01-01 - insert meta values to select which fields are serializable
    }
    person_json = {

    }
    assert dog.m.json() == dog_json
    assert person.m.json() == {
        "name": "João",
        "pets": [dog_json]
    }
