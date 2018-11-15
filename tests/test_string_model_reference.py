from datetime import date

import pytest

import singularity as S


class GlobalPerson(S.Base):
    name = S.StringField()
    friend = S.TypeField("GlobalPerson")

def test_globalclass_can_reference_itself():
    assert GlobalPerson
    p1 = GlobalPerson("João")
    p2 = GlobalPerson("Marcelo")
    p1.friend = p2
    assert p1.friend.name == "Marcelo"


def test_private_class_can_reference_itself():

    class Person(S.Base):
        name = S.StringField()
        friend = S.TypeField("Person")

    p1 = Person("João")
    p2 = Person("Marcelo")
    p1.friend = p2
    assert p1.friend.name == "Marcelo"


def test_class_can_reference_forward_class():
    class Person(S.Base):
        pet = S.TypeField("Pet")

    class Pet(S.Base):
        pass

    p1 = Person()
    p1.pet = Pet()


def test_listfield_can_reference_own_class():
    class Person(S.Base):
        name = S.StringField()
        friends = S.ListField("Person")

    p1 = Person("João")
    p2 = Person("Marcelo")
    p3 = Person("Priscila")
    p1.friends.append(p2)
    p1.friends.append(p3)
    assert list(p1.friends) == [p2, p3]
    with pytest.raises(TypeError):
        p1.friends.append("")


@pytest.mark.skip
def test_edgefield_reciprocrates_inclusions():
    class Person(S.Base):
        name = S.StringField()
        friends = S.EdgeField("Person")

    p1 = Person("João")
    p2 = Person("Marcelo")
    p3 = Person("Priscila")
    p1.friends.append(p2)
    p1.friends.append(p3)
    p2.friends.append(p3)

    assert p2 in p1.friends and p3 in p1.friends
    assert p1 in p2.friends and p1 in p3.friends
    assert p3 in p2.friends and p2 in p3.friends


