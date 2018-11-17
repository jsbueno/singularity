from functools import lru_cache
import json
import uuid
import weakref

from .fields import Field, ComputedField, _SENTINEL, TypedSequence, IDField

class Bindable:

    _instance = None

    def __init__(self, owner, **kwargs):
        if owner:
            self._owner = weakref.proxy(owner)
        super().__init__(**kwargs)

    def _bind(self, parent_instance):
        instance = type(self)(None)
        # TODO: use a cascading dict:
        instance.__dict__ = self.__dict__.copy()
        instance._instance = weakref.proxy(parent_instance, self._parent_instance_del)
        return instance

    # @lru_cache()
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self._bind(instance)


class DataContainer(Bindable):
    def __getattr__(self, attr):
        if attr not in self._owner.m.fields:
            raise AttributeError
        attr = self._owner.f.__dict__[attr]
        return attr.__get__(self._instance, self._owner)

    def __setattr__(self, attr, value):
        if attr in ["_instance",  "_owner", "__dict__"] or attr not in self._owner.m.fields:
            return super().__setattr__(attr, value)
        attr = self._owner.f.__dict__[attr]
        attr.__set__(self._instance, value)

    def __delattr__(self, attr):
        if attr not in self._instance._data:
            raise AttributeError
        attr = self._owner.f.__dict__[attr]
        return attr.__delete__(self._instance)

    def __dir__(self):
        return list(self._instance.m.defined_fields() if self._instance else self._owner.m.defined_fields())

    def _parent_instance_del(self):
        pass


class FieldContainer:
    def __iter__(self):
        yield from self.__dict__.keys()

    def __dir__(self):
        return list(self)


class Instrumentation(Bindable):

    def json(self, serialize=False, obj=None):
        sentinel = object()
        result = {}
        for field_name, field in self.fields.items():
            value = getattr(obj.d if obj else self._instance.d, field_name, sentinel)
            if value is not sentinel:
                result[field_name] = field.json(value)
        return result if not serialize else json.dumps(result)

    def from_json(self, data, strict=False):
        if isinstance(data, str):
            data = json.loads(data)
        instance = self._owner()
        for key, value in data.items():
            field = self.fields.get(key)
            if isinstance(field, IDField):
                instance._data["id"] = field.from_json(value)
                continue
            if isinstance(field, ComputedField):
                continue
            if hasattr(field, "from_json"):
                value = field.from_json(value)
            elif hasattr(field, "m"):
                value = field.m.from_json(value)

            if strict and field is None:
                raise KeyError(f"Unknown field {key!r}")

            setattr(instance.d, key, value)
        return instance

    def defined_fields(self):
        if not self._instance:
            yield from self.fields.keys()
            return None
        for field_name, field in self.fields.items():
            if field_name in self._instance._data or field in self.computed_fields:
                yield field_name

    def parse_path(self, path):
        if "." not in path:
            yield int(path) if path.isdigit() else path, ""
            return

        comp, reminder = path.split(".", 1)
        yield (int(comp) if comp.isdigit() else comp), reminder
        yield from self.parse_path(reminder)

    def copy(self):
        if not self._instance:
            raise TypeError("Only instances of dataclasses can be copied")
        instance = self._owner()
        instance._data = self._instance._data.copy()
        return instance

    def deepcopy(self, memo=None):
        from copy import deepcopy
        if not self._instance:
            raise TypeError("Only instances of dataclasses can be deep-copied")
        instance = self._owner()
        instance._data = deepcopy(self._instance._data, memo)
        return instance

    def get_many(self, key, default=None):
        try:
            if "." not in key:
                if key == "*":
                    raise KeyError("'*' only makes sense for sequence components of the key")
                yield getattr(self._instance.d, key)
                return
            item = self._instance
            for comp, path_remainder in self.parse_path(key):
                if comp == "*":
                    if not isinstance(item, TypedSequence):
                        raise KeyError("'*' only makes sense for sequence components of the key")
                    for element in item:
                        if not path_remainder:
                            yield element
                        elif isinstance(element, Base):
                            yield from element.m.get_many(path_remainder, default)
                        else:
                            raise KeyError(f"Components are not an instance of Base after '*' in {key!r}")

                    return
                if isinstance(comp, int):
                    if isinstance(item, TypedSequence):
                        item = item[comp]
                        continue
                    raise KeyError(f"Integer {comp!r} not allowed in this part of the path")
                item = getattr(item.d, comp)
            yield item

        except (KeyError, AttributeError):
            yield default

    def get(self, path, default=None):
        if "*" in path:
            raise KeyError("Invalid '*' in item path")
        return next(self.get_many(path, default))

    def _get_inner_item(self, path):
        if "." in path:
            path_prefix, last_component = path.rsplit(".", 1)
            for inner in self.get_many(path_prefix):
                yield inner, last_component

        else:
            inner = self._instance
            last_component = path
            yield inner, last_component

    def settable_fields(self):
        for key, value in self.fields.items():
            if not isinstance(value, ComputedField) or hasattr(value, "setter"):
                yield key

    def _parent_instance_del(self, instance):
        pass


def parent_field_list(bases):
    for base in bases:
        if not isinstance(base, Meta):
            continue
        for field_name, field in base.m.fields.items():
            yield field_name, field


class Meta(type):

    # There is no '__prepare__' method, as in Python 3.6+,
    # class attributes are ordered by default.
    # otherwise, __prepare__ should return an OrderedDict

    def __new__(metacls, name, bases, attrs, strict=False, **kwargs):

        container = FieldContainer()
        for field_name, field in parent_field_list(bases):
            # Avoid triggering descriptor mechanisms
            container.__dict__[field_name] = field

        computed_fields = set()
        for attr_name, value in list(attrs.items()):
            if not isinstance(value, Field):
                continue
            container.__dict__[attr_name] = value
            if strict:
                del attrs[attr_name]
            if isinstance(value, ComputedField):
                computed_fields.add(value)

        if strict:
            slots = set(attrs.get("__slots__", ()))
            slots.update({"m", "d", "_data"})
            attrs["__slots__"] = tuple(slots)

        cls = super().__new__(metacls, name, bases, attrs, **kwargs)

        cls.f = container
        cls.d = DataContainer(cls)
        cls.m = Instrumentation(owner=cls)
        cls.m.strict = strict
        cls.m.fields = container.__dict__
        cls.m.computed_fields = computed_fields

        if strict:
            for field_name, field in cls.m.fields.items():
                field.__set_name__(cls, field_name)

        return cls


class Base(metaclass=Meta):
    __slots__ = ("__weakref__",)

    def __init__(self, *args, **kwargs):
        self._data = {}
        seem = set()
        for field_name, arg in zip(self.m.settable_fields(), args):
            setattr(self.d, field_name, arg)
            seem.add(field_name)

        id_ = None

        for field_name, arg in kwargs.items():
            if field_name in seem:
                raise TypeError(f"Argument {field_name!r} passed twice")
            if field_name == "id":
                id_ = uuid.UUID(arg) if not isinstance(arg, uuid.UUID) else arg
                self._data["id"] = id_

            setattr(self.d, field_name, arg)
        if not id_:
            self._data["id"] = uuid.uuid4()

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        sentinel = object()
        return all(
            getattr(self.d, field_name, sentinel) == getattr(other.d, field_name, sentinel)
            for field_name, field in self.m.fields.items()
            if field not in self.m.computed_fields
        )

    def __hash__(self):
        # Needed for caching the container object.
        return hash(id(self))

    def __bool__(self):
        # otherwise __len__ is used.
        return True

    def __repr__(self):
        return "{0}({1})".format(
            self.__class__.__name__,
            ', '.join(f"{name}={value}" for name, value in self._data.items())
        )

    def __copy__(self):
        return self.m.copy()

    def __deepcopy__(self, memo=None):
        return self.m.deepcopy(memo)

    def __getstate__(self):
        return self._data

    def __setstate__(self, state):
        self._data = state

    # Mapping Methods

    def get(self, key, default=None):
        return self.m.get(key, default)

    def __getitem__(self, key):
        item = self.get(key, default=_SENTINEL)
        if item is _SENTINEL:
            raise KeyError(key)
        return item

    def __setitem__(self, key, value):
        for inner_item, last_component in self.m._get_inner_item(key):

            if not inner_item or not isinstance(inner_item, (Base, Field, TypedSequence)):
                raise KeyError(f"Field {key!r} is not defined for instances of {self.__class__.__name__!r}")
            if not last_component.isdigit():
                if last_component == "*":
                    for index in range(len(inner_item)):
                        inner_item[index] = value
                    continue
                if last_component not in inner_item.m.fields:
                    raise KeyError(f"Field {key!r} is not defined for instances of {self.__class__.__name__!r}")
                setattr(inner_item.d, last_component, value)
            else:
                inner_item.__setitem__(int(last_component), value)

    def __delitem__(self, key):
        for inner_item, last_component in self.m._get_inner_item(key):
            if not isinstance(inner_item, TypedSequence):
                delattr(inner_item.d, last_component)
            else:
                if last_component == "*":
                    inner_item.clear()
                else:
                    inner_item.__delitem__(int(last_component))

    def __iter__(self):
        yield from self.m.defined_fields()

    def __len__(self):
        return len(self.m.computed_fields) + len(self._data)

    # Default field:

    id = IDField()
