from datetime import date

import pytest

import singularity as S

def test_declare_dataclass_():
    class Pet(S.Base):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        # age = S.ComputedField(lambda self: (date.today() - self.birthday).days // 365)


    p = Pet("Rex", "dog", date(2015, 1, 1))
    assert p.name == "Rex"
    assert p.species == "dog"
    assert p.birthday == date(2015, 1, 1)
    # assert p.age == (date.today().year - 2015)


@pytest.mark.skip
def test_declare_nested_dataclass():
    class Pet(S.Base):
        name = S.StringField()
        species = S.StringField(options="cat dog other".split())
        birthday = S.DateField()
        age = S.ComputedField(lambda self: (date.today() - self.birthday).days // 365)

    class Person(S.Base):
        name = S.StringField()
        pets = S.ListField(Pet)

    p = Pet("Rex", "dog", date(2015, 1, 1))


