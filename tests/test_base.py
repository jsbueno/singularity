from datetime import date
from unittest import mock

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


@pytest.fixture
def person(person_cls, dog):
    pe = person_cls("João")
    pe.d.pets.append(dog)
    return pe


@pytest.fixture
def dog_json():
    return {
        'name': 'Rex',
        'species': 'dog',
        'birthday': '2015-01-01',
        'age': 3
    }


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


def test_computed_field(dog):
    assert dog.d.age == (date.today().year - 2015)


def test_str_field_with_options_error_on_unknown_option(dog):
    with pytest.raises(ValueError):
        dog.d.species = "lemur"


def test_class_with_listfield(dog):

    class Person(S.Base):
        name = S.StringField()
        pets = S.ListField(type(dog))

    pe = Person("João")
    pe.d.pets.append(dog)

    assert pe.d.pets[0].name == 'Rex'


def test_list_field_dont_accept_wrong_type(person):
    with pytest.raises(TypeError):
        person.d.pets.append(1)


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


def test_strict_classes_should_not_allow_attribute_setting(pet_strict_cls):
    p = pet_strict_cls()
    with pytest.raises(AttributeError):
        p.name = "Rex"
    p.d.name = "Rex"


def test_iterating_on_object_should_yield_defined_fields(pet_cls):
    # TODO: maybe be able to customize whether a computed field should show up?
    # An attribute could be set on the field to indicate the pre-requisite fields
    # for it to "exist".
    assert list(pet_cls()) == ["age"]
    assert list(pet_cls("Rex")) == ["name", "age"]
    assert list(pet_cls("Rex", "dog")) == ["name", "species", "age"]
    assert list(pet_cls("Rex", "dog", date(2015, 1, 1))) == ["name", "species", "birthday", "age"]


def test_dir_on_container_namespace_for_class_should_return_fields(pet_cls):
    assert dir(pet_cls.d) == sorted(["name", "species", "birthday", "age"])


def test_dir_on_container_namespace_should_return_existing_fields(pet_cls):
    # TODO: maybe be able to customize whether a computed field should show up?
    # An attribute could be set on the field to indicate the pre-requisite fields
    # for it to "exist".
    assert dir(pet_cls().d) == ["age"]
    assert dir(pet_cls("Rex").d) == sorted(["name", "age"])
    assert dir(pet_cls("Rex", "dog").d) == sorted(["name", "species", "age"])
    assert dir(pet_cls("Rex", "dog", date(2015, 1, 1)).d) == sorted(["name", "species", "birthday", "age"])


def test_attribute_values_can_be_deleted(dog):
    with pytest.raises(TypeError):
        dog.d.name = None

    del dog.d.name

    with pytest.raises(AttributeError):
        del dog.d.name

    assert not hasattr(dog.d, 'name')


def test_attribute_values_can_be_deleted_in_body(pet_strict_cls, pet_cls):
    # For non-strict classes:
    d1 = pet_cls("Rex")
    del d1.name
    with pytest.raises(AttributeError):
        assert d1.name
    d2 = pet_strict_cls("Rex")
    with pytest.raises(AttributeError):
        del d2.name


def test_equal_fields_imply_equality(pet_cls, dog):
    new_dog = pet_cls()
    new_dog._data.update(dog._data)

    assert new_dog == dog
    del new_dog.birthday
    assert new_dog != dog
    del dog.birthday
    assert new_dog == dog
    del new_dog.name
    assert new_dog != dog


def test_equal_fields_imply_equality_with_listfield(pet_cls, person_cls, dog, person):
    new_dog = pet_cls()
    new_dog._data.update(dog._data)
    new_person = person_cls()
    new_person._data.update(person._data)
    new_person._data['pets'] = S.TypedSequence(pet_cls, [new_dog])

    assert new_person == person



def test_json_serializing(dog, person, dog_json):
    original_dt = date
    class FakeDate:
        @staticmethod
        def today():
            return original_dt(2018, 11, 1)

    with mock.patch('datetime.date', FakeDate):
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


@pytest.mark.skip
def test_json_desserializing(pet_cls, dog):
    dog_json = {
        'name': 'Rex',
        'species': 'dog',
        'birthday': '2015-01-01',
    }

    new_dog = pet_cls.m.from_json(dog_json)

    assert new_dog == dog

        #assert dog.m.json() == dog_json
        #assert person.m.json() == {
            #"name": "João",
            #"pets": [dog_json]
        #}
