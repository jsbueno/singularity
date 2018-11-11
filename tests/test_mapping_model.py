from datetime import date

import pytest


def test_attributes_can_be_read_as_mapping_items(dog):
    assert dog["name"] == "Rex"
    assert dog["birthday"] == date(2015, 1, 1)
    assert dog["age"] == dog.d.age
    with pytest.raises(KeyError):
        dog["child"]


def test_nested_attributes_can_be_read_as_mapping_items(child):
    assert child["father"]["name"] == "João"
    assert child["father.name"] == "João"


def test_accessing_non_existent_nested_attributes_should_raise_key_error(child):
    with pytest.raises(KeyError):
        assert child["father.uncle"] == "João"
    with pytest.raises(KeyError):
        assert child["uncle.uncle"] == "João"
    with pytest.raises(KeyError):
        assert child["father.name.first_name"] == "João"


def test_nested_attributes_with_list_can_be_read_as_mapping_items(child):
    assert child["father.pets.0.name"] == "Rex"


def test_nested_attributes_with_list_raises_for_non_list_fields(child):
    with pytest.raises(KeyError):
        child["father.0.name"]


def test_nested_attributes_can_be_read_as_mapping_items_with_get(child):
    assert child.get("name") == "Bruno"
    assert child.get("father.name") == "João"
    assert child.get("uncle.name") is None
    assert child.get("father.pets.0.name") == "Rex"


def test_attributes_can_be_written_as_mapping_items(dog):
    dog["name"] = "Toto"
    assert dog["name"] == "Toto"
    assert dog.d.name == "Toto"


def test_nested_attributes_can_be_written_as_mapping_items(child):
    child["father.name"] = "Renato"
    assert child["father.name"] == "Renato"
    assert child.d.father.d.name == "Renato"


def test_nested_attributes_with_list_can_be_written_as_mapping_items(child):
    child["father.pets.0.name"] = "Toto"
    assert child["father.pets.0.name"] == "Toto"
    assert child.d.father.d.pets[0].d.name == "Toto"


def test_attributes_written_as_mapping_items_check_type(dog, child):
    with pytest.raises(TypeError):
        dog["name"] = 10
    with pytest.raises(TypeError):
        child["father.name"] = 10
    with pytest.raises(TypeError):
        child["father.pets.0.name"] = 10


def test_nested_attributes_ending_in_list_item_can_be_written_as_mapping_items(child, cat):
    child["father.pets.0"] = cat
    assert child["father.pets.0.name"] == "Marie"
    assert child.d.father.d.pets[0].d.name == "Marie"


def test_assigining_non_existent_nested_attributes_should_raise_key_error(child):
    with pytest.raises(KeyError):
        child["father.uncle"] = "João"
    with pytest.raises(KeyError):
        child["uncle.uncle"] = "João"
    with pytest.raises(KeyError):
        child["father.name.first_name"] = "João"


def test_attributes_can_be_deleted_as_mapping_items(child, dog):
    del child["name"]
    assert not hasattr(child.d, "name")
    del child["father.name"]
    assert not hasattr(child.d.father.d, "name")
    del child["father.pets.0.name"]
    assert child.get("father.pets.0.name") is None


def test_attributes_can_be_deleted_as_mapping_items_when_last_item_is_index_list(child):
    del child["father.pets.0"]
    assert not child["father.pets"]


def test_star_attribute_writting_works(child, cat):
    child["father.pets"].append(cat)
    child["father.pets.*.name"] = "Toto"
    assert len(child.d.father.d.pets) == 2
    for pet in child["father.pets"]:
        assert pet["name"] == "Toto"


@pytest.mark.skip
def test_star_deletion_works(child, cat):
    child["father.pets"].append(cat)
    del child["father.pets.*"]
    assert len(child.d.father.d.pets) == 0
    del child["father.pets"]
    with pytest.raises(AttributeError):
        child.d.father.d.pets


@pytest.mark.skip
def test_star_attribute_deletion_works(child, cat):
    child["father.pets"].append(cat)
    for pet in child["father.pets"]:
        assert hasattr(pet.d, "name")
    del child["father.pets.*.name"]
    assert len(child.d.father.d.pets) == 2
    for pet in child["father.pets"]:
        assert not hasattr(pet.d, "name")


