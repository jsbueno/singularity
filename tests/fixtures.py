from datetime import date

import singularity as S


class Pet(S.Base):
    name = S.StringField()
    species = S.StringField(options="cat dog other".split())
    birthday = S.DateField()
    age = S.ComputedField(lambda self: (date.today() - self.d.birthday).days // 365)


class StrictPet(S.Base, strict=True):
    name = S.StringField()
    species = S.StringField(options="cat dog other".split())
    birthday = S.DateField()
    age = S.ComputedField(lambda self: (date.today() - self.d.birthday).days // 365)


class Person(S.Base):
    name = S.StringField()
    pets = S.ListField(Pet)


class StrictPerson(S.Base, strict=True):
    name = S.StringField()
    pets = S.ListField(StrictPet)


class Child(StrictPerson, strict=True):
    father = S.TypeField(StrictPerson)
    mother = S.TypeField(StrictPerson)
