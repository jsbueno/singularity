from functools import lru_cache
import json

from .fields import Field, ComputedField, _SENTINEL, TypedSequence


class DataContainer2:
    def __init__(self, parent, instance, owner):
        self._parent = parent
        self._instance = instance
        self._owner = owner

    def __getattr__(self, attr):
        if attr not in self._owner.m.fields:
            raise AttributeError
        attr = self._parent.__dict__[attr]
        return attr.__get__(self._instance, self._owner)

    def __setattr__(self, attr, value):
        if attr in ["_parent",  "_instance",  "_owner"] or attr not in self._owner.m.fields:
            return super().__setattr__(attr, value)
        attr = self._parent.__dict__[attr]
        attr.__set__(self._instance, value)

    def __delattr__(self, attr):
        if attr not in self._instance._data:
            raise AttributeError
        attr = self._parent.__dict__[attr]
        return attr.__delete__(self._instance)

    def __dir__(self):
        return list(self._instance.m.defined_fields() if self._instance else self._owner.m.defined_fields())


class DataContainer:
    @lru_cache()
    def __get__(self, instance, owner):
        return DataContainer2(parent=self, instance=instance, owner=owner)


class Instrumentation:
    parent = None

    def __init__(self, owner=None):
        self.owner = owner

    def _bind(self, parent_instance):
        instance = type(self)()
        # TODO: use a cascading dict:
        instance.__dict__ = self.__dict__.copy()
        instance.parent = parent_instance
        return instance

    def json(self, serialize=False, obj=None):
        sentinel = object()
        result = {}
        for field_name, field in self.fields.items():
            value = getattr(obj.d if obj else self.parent.d, field_name, sentinel)
            if value is not sentinel:
                result[field_name] = field.json(value)
        return result if not serialize else json.dumps(result)

    def from_json(self, data, strict=False):
        if isinstance(data, str):
            data = json.loads(data)
        instance = self.owner()
        for key, value in data.items():
            field = self.fields.get(key)
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

    @lru_cache()
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self._bind(instance)

    def defined_fields(self):
        if not self.parent:
            yield from self.fields.keys()
            return None
        for field_name, field in self.fields.items():
            if field_name in self.parent._data or field in self.computed_fields:
                yield field_name

    def parse_path(self, path):
        if isinstance(path, int):
            return[path]
        return [comp if not comp.isdigit() else int(comp) for comp in path.split(".")]

    def copy(self):
        if not self.parent:
            raise TypeError("Only instances of dataclasses can be copied")
        instance = self.owner()
        instance._data = self.parent._data.copy()
        return instance

    def deepcopy(self, memo=None):
        from copy import deepcopy
        if not self.parent:
            raise TypeError("Only instances of dataclasses can be deep-copied")
        instance = self.owner()
        instance._data = deepcopy(self.parent._data, memo)
        return instance

    def get(self, key, default=None):
        try:
            # getting from '_data' would be faster, but we have to provide
            # a single mechanism for data retrieval so that
            # access control and permissions can work later on.
            if "." not in key:
                return getattr(self.parent.d, key)
            item = self.parent
            for comp in self.parse_path(key):
                if isinstance(comp, int):
                    if isinstance(item, TypedSequence):
                        item = item[comp]
                        continue
                    raise KeyError(f"Integer {comp!r} not allowed in this part of the path")
                item = getattr(item.d, comp)
            return item

        except (KeyError, AttributeError):
            return default

    def _get_inner_item(self, item):
        if "." in item:
            path_prefix, last_component = item.rsplit(".", 1)
            inner = self.get(path_prefix)
        else:
            inner = self.parent
            last_component = item
        return inner, last_component


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

        container = DataContainer()
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

        cls.d = container
        cls.m = Instrumentation(owner=cls)
        cls.m.strict = strict
        cls.m.fields = container.__dict__
        cls.m.computed_fields = computed_fields

        if strict:
            for field_name, field in cls.m.fields.items():
                field.__set_name__(cls, field_name)

        return cls


class Base(metaclass=Meta):
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        self._data = {}
        seem = set()
        for field_name, arg in zip(self.m.fields, args):
            setattr(self.d, field_name, arg)
            seem.add(field_name)

        for field_name, arg in kwargs.items():
            if field_name in seem:
                raise TypeError(f"Argument {field_name!r} passed twice")
            setattr(self.d, field_name, arg)

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
        inner_item, last_component = self.m._get_inner_item(key)

        print(type(inner_item))
        if not inner_item or not isinstance(inner_item, (Base, Field, TypedSequence)):
            raise KeyError(f"Field {key!r} is not defined for instances of {self.__class__.__name__!r}")
        if not last_component.isdigit():
            if last_component not in inner_item.m.fields:
                raise KeyError(f"Field {key!r} is not defined for instances of {self.__class__.__name__!r}")
            setattr(inner_item.d, last_component, value)
        else:
            inner_item.__setitem__(int(last_component), value)

    def __delitem__(self, key):
        inner_item, last_component = self.m._get_inner_item(key)
        if not last_component.isdigit():
            delattr(inner_item.d, last_component)
        else:
            inner_item.__delitem__(int(last_component))

    def __iter__(self):
        yield from self.m.defined_fields()

    def __len__(self):
        return len(self.m.computed_fields) + len(self._data)
