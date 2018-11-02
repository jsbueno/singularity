from datetime import date

import pytest

import singularity as S


def pet_cls_call():
    class Pet(S.Base):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        age = S.ComputedField(lambda self: (date.today() - self.d.birthday).days // 365)

    return Pet


def pet_strict_cls_call():
    class Pet(S.Base, strict=True):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        age = S.ComputedField(lambda self: (date.today() - self.d.birthday).days // 365)

    return Pet


@pytest.fixture
def pet_cls():
    return pet_cls_call()


@pytest.fixture
def pet_strict_cls():
    return pet_strict_cls_call()

@pytest.fixture
def dog(pet_cls):
    return pet_cls("Rex", "dog", date(2015, 1, 1))


@pytest.fixture
def person_cls(pet_cls):
    class Person(S.Base):
        name = S.StringField()
        pets = S.ListField(pet_cls)

    return Person


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
def person(person_cls, dog):
    pe = person_cls("João")
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


def test_json_serializing_incomplete_object(person_cls):
    p = person_cls()
    assert p.m.json() == {
        "pets": []
    }


def test_meta_attributes_indicate_strict_class(pet_cls, pet_strict_cls):
    assert not pet_cls.m.strict
    assert pet_strict_cls.m.strict


@pytest.mark.parametrize("Pet", [pet_cls_call(), pet_strict_cls_call()])
def test_unamed_parameters_should_work(Pet):
    p = Pet("Rex", "dog", date(2015, 1, 1))
    assert p.d.name == "Rex"
    assert p.d.species == "dog"
    assert p.d.birthday == date(2015, 1, 1)


@pytest.mark.parametrize("Pet", [pet_cls_call(), pet_strict_cls_call()])
def test_named_parameters_should_work(Pet):
    p = Pet(name="Rex", species="dog", birthday=date(2015, 1, 1))
    assert p.d.name == "Rex"
    assert p.d.species == "dog"
    assert p.d.birthday == date(2015, 1, 1)
