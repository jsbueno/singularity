from datetime import date

import pytest

import singularity as S

from fixtures import Pet, StrictPet, Person, StrictPerson, Child


@pytest.fixture
def pet_cls():
    return Pet


@pytest.fixture
def pet_strict_cls():
    return StrictPet


@pytest.fixture
def dog(pet_cls):
    return pet_cls("Rex", "dog", date(2015, 1, 1))


@pytest.fixture
def strict_dog(pet_strict_cls):
    return pet_strict_cls("Rex", "dog", date(2015, 1, 1))


@pytest.fixture
def cat(pet_strict_cls):
    return pet_strict_cls("Marie", "cat", date(2016, 1, 1))


@pytest.fixture
def person_cls():
    return Person


@pytest.fixture
def person_strict_cls():
    return StrictPerson


@pytest.fixture
def person(person_cls, dog):
    pe = person_cls("João")
    pe.d.pets.append(dog)
    return pe


@pytest.fixture
def strict_person(person_strict_cls, strict_dog):
    pe = person_strict_cls("João")
    pe.d.pets.append(strict_dog)
    return pe


@pytest.fixture
def dog_json():
    return {
        'name': 'Rex',
        'species': 'dog',
        'birthday': '2015-01-01',
        'age': 3
    }


@pytest.fixture
def child(strict_person):
    m = StrictPerson("Beatriz")
    return Child("Bruno", father=strict_person, mother=m)


