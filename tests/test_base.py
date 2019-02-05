from datetime import date
from unittest import mock
import gc
import uuid

import pytest

import singularity as S

from fixtures import Pet, StrictPet, Person, StrictPerson, Child


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


@pytest.mark.parametrize("Pet", [Pet, StrictPet])
def test_unamed_parameters_should_work(Pet):
    p = Pet("Rex", "dog", date(2015, 1, 1))
    assert p.d.name == "Rex"
    assert p.d.species == "dog"
    assert p.d.birthday == date(2015, 1, 1)


@pytest.mark.parametrize("Pet", [Pet, StrictPet])
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
    assert list(pet_cls()) == ["id", "age"]
    assert list(pet_cls("Rex")) == ["id", "name", "age"]
    assert list(pet_cls("Rex", "dog")) == ["id", "name", "species", "age"]
    assert list(pet_cls("Rex", "dog", date(2015, 1, 1))) == ["id", "name", "species", "birthday", "age"]


def test_dir_on_data_namespace_for_class_should_return_fields(pet_cls):
    assert dir(pet_cls.d) == sorted(["id", "name", "species", "birthday", "age"])


def test_dir_on_fields_namespace_should_return_fields(pet_cls):
    assert dir(pet_cls.f) == sorted(["id", "name", "species", "birthday", "age"])
    assert dir(pet_cls().f) == sorted(["id", "name", "species", "birthday", "age"])
    assert all(isinstance(getattr(pet_cls().f, name), S.Field) for name in pet_cls.f)


def test_dir_on_container_namespace_should_return_existing_fields(pet_cls):
    # TODO: maybe be able to customize whether a computed field should show up?
    # An attribute could be set on the field to indicate the pre-requisite fields
    # for it to "exist".
    assert dir(pet_cls().d) == sorted(["id", "age"])
    assert dir(pet_cls("Rex").d) == sorted(["id", "name", "age"])
    assert dir(pet_cls("Rex", "dog").d) == sorted(["id", "name", "species", "age"])
    assert dir(pet_cls("Rex", "dog", date(2015, 1, 1)).d) == sorted(["id", "name", "species", "birthday", "age"])


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
    new_person._data['pets'] = S.fields.TypedSequence(pet_cls, [new_dog])

    assert new_person == person


def test_list_field_accept_appending(strict_person, cat):
    strict_person.d.pets.append(cat)
    assert len(strict_person.d.pets) == 2


def test_empty_object_is_truthy(person_strict_cls):
    assert person_strict_cls()


def test_json_serializing(dog, person, dog_json):
    original_dt = date
    class FakeDate:
        @staticmethod
        def today():
            return original_dt(2018, 11, 1)

    with mock.patch('datetime.date', FakeDate):
        assert dog.m.json() == dog_json
        serialized = person.m.json()
        serialized.pop("id")
        assert serialized == {
            "name": "João",
            "pets": [dog_json]
        }


def test_json_serializing_incomplete_object(person_cls):
    p = person_cls()
    serialized = p.m.json()
    serialized.pop("id")
    assert serialized == {
        "pets": []
    }


def test_json_desserializing(pet_cls, dog, dog_json):
    new_dog = pet_cls.m.from_json(dog_json)
    assert new_dog == dog


def test_json_desserializing_with_listfield(person_cls, person, dog_json):
    person_json = {
        "id": str(person.id),
        "name": "João",
        "pets": [dog_json]
    }

    new_person = person_cls.m.from_json(person_json)

    assert new_person == person


def test_shallow_copy_works_for_non_strict(dog, person):
    from copy import copy
    new_dog = copy(dog)
    assert dog == new_dog
    assert dog is not new_dog

    new_person = copy(person)
    assert person == new_person
    assert person is not new_person
    assert person.pets[0] is new_person.pets[0]


def test_deepcopy_works_for_non_strict_instance(person):
    from copy import deepcopy

    for new_person in (deepcopy(person), person.m.deepcopy()):
        assert person == new_person
        assert person is not new_person
        assert person.d.pets == new_person.d.pets
        assert person.d.pets[0] is not new_person.d.pets[0]


def test_deepcopy_works_for_strict_instance(strict_dog, strict_person):
    from copy import deepcopy

    for new_person in (deepcopy(strict_person), strict_person.m.deepcopy()):
        assert strict_person == new_person
        assert strict_person is not new_person
        assert strict_person.d.pets == new_person.d.pets
        assert strict_person.d.pets[0] is not new_person.d.pets[0]


def test_instances_can_be_pickled(strict_dog, strict_person):
    import pickle
    pickle.dumps(strict_dog)
    pickle.dumps(strict_person)


def test_instances_can_be_unpickled(strict_dog, strict_person):
    import pickle
    new_dog = pickle.loads(pickle.dumps(strict_dog))
    new_person = pickle.loads(pickle.dumps(strict_person))

    assert new_dog == strict_dog
    assert new_person == strict_person


def test_typefield_works(strict_person):
    m = StrictPerson("Beatriz")
    c = Child("Bruno", father=strict_person, mother=m)
    assert c.d.father == strict_person
    assert c.d.mother == m


def test_json_serialize_desserialize_with_typefield(child):
    child_json = {
        'name': 'Bruno',
        'pets': [],
        'father': {
            'name': 'João',
            'pets': [{
                'age': 3,
                'birthday': '2015-01-01',
                'name': 'Rex',
                'species': 'dog'
            }]
        },
        'mother': {'name': 'Beatriz', 'pets': []},
    }

    data = child.m.json()
    new_child = Child.m.from_json(data)
    del data["id"]
    del data["father"]["id"]
    del data["mother"]["id"]
    del data["father"]["pets"][0]["id"]
    assert data == child_json
    assert child == new_child


# WEAKEREF usage test

@pytest.mark.parametrize("namespace", ("m", "d"))
def test_instrumentation_class_hold_weakrefs_to_owner(namespace):
    class Test(S.Base):
        pass
    assert getattr(Test, namespace)._owner.__name__ == "Test"
    test_m = getattr(Test, namespace)
    gc.collect()
    # breakpoint()
    # print(gc.get_referrers(Test))
    del Test
    gc.collect()
    with pytest.raises(ReferenceError):
        assert test_m._owner.__name__ == "Test"


def test_bound_instrumentation_class_hold_weakrefs_to_owner_instance():
    class Test(S.Base):
        pass
    t = Test()
    assert t.m._instance()
    t_m = t.m
    del t
    gc.collect()

    assert t_m._instance() is None


def test_creating_user_weakrefs_for_instances_dont_break_namespace_caching():
    import weakref
    class Test(S.Base):
        pass
    t = Test()
    wt = weakref.ref(t)
    t_m = t.m
    del t


def test_instances_have_intrinsc_id_field():
    class Test(S.Base):
        pass
    t = Test()
    assert t.id
    assert isinstance(t.id, uuid.UUID)
    assert t.d.id


def test_id_field_directly_on_instance_even_for_strict_classes():
    class Test(S.Base, strict=True):
        name = S.StringField(default='bla')
    t = Test()
    assert t.id
    with pytest.raises(AttributeError):
        assert t.name


def test_bound_metadata_instance(person_cls):
    Person = person_cls
    p1 = Person()
    assert p1.m._instance
    assert not Person.m._instance


@pytest.mark.skip
def test_bound_metadata_instance_is_same_instance(person_cls):
    # ok -a distant dream, this won't work. We will have bound and unbound instances!
    Person = person_cls
    p1 = Person()
    assert p1.m.parent
    assert not Person.m.parent
    # Add some magic

    assert p1.m.parent is Person.m.parent

