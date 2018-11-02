[WIP] Singularity
++++++++++++++++++

To become a transparent  Object Persistence, Schma verifier, plugable
data engine, allwoing multiple backe-ends.


DataFields
============

For now, Singularity offers an advanced "dataclass" functionality that allows easy separation of
data fields and other class methods and attributes that are in place to manipulate those fields.

So, a class body created with Singularity Field instances is not unlike a similar declarationg using SQLAlchemy ORM, Django Models or Python dataclasses:

```
import singularity as S

class Person(S.Base):
    name = S.StringField()
    age = S.NumberField()
```

Singularity automatically creates a `.d` namespace on instances of this class - this namespace's only
attributes are those fields. Data manipulation and serialization methods are provided on the `.m` namespace.

So that:

```
>>> p = Person("João", 44)
>>> p.d.name
'João'

>>> p.d.age
44

>>> p.d.age = None
(...)
TypeError: Field 'age' of 'Person' instances must be set to an instance of 'Number'
```

The fields as descriptors are available to inspection/direct access on the `.m` namespace:
>>> p.m.fields.keys()
dict_keys(['name', 'age'])
>>> p.m.json()                                                                                              {'name': 'joao', 'age': 19}

>>> p.m.json(serialize=True)
'{"name": "joao", "age": 19}'


Currently, the fields are, by default, mirrored on the normal class namespaces - but one can pass
the keyword argument `strict=True` when creating the class to avoid having the fields in the class namespace itself.

Special Fields
===============

Unlike Json, which only knows about dicts, lists, strings, numbers and None types, Singularity can make use of rich data types. Date, DateTime fields , and typed lists (which can be any Json type, or another Singularity Data Class) work by default.

You are invited to create your own field types, and enjoy the mechanism to serialize and de-serialize it in a seamless way to JSON (and soon, other formats as well)



