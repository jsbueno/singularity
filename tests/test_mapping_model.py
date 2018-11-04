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


@pytest.mark.skip
def test_nested_attributes_can_be_read_as_mapping_items_with_get(child):
    assert child.get("name") == "Bruno"
    assert child.get("father.name") == "João"
    assert child.get("uncle.name") is None
    assert child.get("father.pets.0.name") == "Rex"

@pytest.mark.skip
def test_nested_attributes_with_list_can_be_read_as_mapping_items(child):
    assert child["father.pets.0.name"] == "Rex"


@pytest.mark.skip
def test_attributes_can_be_written_as_mapping_items(dog):
    dog["name"] = "Toto"
    assert dog["name"] == "Toto"
    assert dog.d.name == "Toto"


@pytest.mark.skip
def test_nested_attributes_can_be_written_as_mapping_items(child):
    child["father.name"] = "Renato"
    assert child["father.name"] == "Renato"
    assert child.d.father.d.name == "Renato"


@pytest.mark.skip
def test_nested_attributes_with_list_can_be_written_as_mapping_items(child):
    child["father.pets.0.name"] = "Toto"
    assert child["father.pets.0.name"] == "Toto"
    assert child.d.father.d.pets[0].d.name == "Toto"


@pytest.mark.skip
def test_attributes_can_be_deleted_as_mapping_items(child, dog):
    del child["name"]
    assert not hasattr(child.d, "name")
    del child["father.name"]
    assert not hasattr(child.d.father.d, "name")
    del child["father.pets.0.name"]
    assert child.get("father.pets.0.name") is None


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


@pytest.mark.skip
def test_star_attribute_writting_works(child, cat):
    child["father.pets"].append(cat)
    child["father.pets.*.name"] = "Toto"
    assert len(child.d.father.d.pets) == 2
    for pet in child["father.pets"]:
        assert pet["name"] == "Toto"

