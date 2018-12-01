from collections import OrderedDict

import simple_model as SM

import singularity


def from_simple_model(sm_model):
    # TODO: use a registry to avoid recreating classes for the same
    # model in the same process.
    si_fields = OrderedDict()
    if isinstance(sm_model, type):
        sm_model = sm_model()
        input_is_type = True
    else:
        input_is_type = False
    values = {}
    breakpoint()
    for field in sm_model._get_fields():
        name, value, model_field = field
        type_ = model_field.types[0]
        values[name] = value
        si_fields[name] = get_singularity_field(type_)

    # TODO: have a better, official way, for declarative singularity types creation
    new_cls = type(sm_model.__class__.__name__, (singularity.Base,), si_fields)

    if not input_is_type:
        instance = new_cls(**values)
        return instance
    return new_cls


def get_singularity_field(type_, ):
    # TODO: create a field registry
    best_match = None, 9999
    for field_name, field in singularity.fields.__dict__.items():
        if not isinstance(field, type) or not issubclass(field, singularity.fields.Field):
            continue
        if issubclass(type_, field.type):
            try:
                distance = type_.__mro__.index(field.type)
            except ValueError:
                # Virtual subclass
                distance = 0
            if distance < best_match[1]:
                best_match = field, distance
    if best_match[0] is None:
        if isinstance(type_, SM.Model):
            type_ = get_singularity_field(type_)
        # TODO: check for sequences.
        new_field = singularity.TypeField(type_=type_)
    else:
        # TODO - add simple_model's default field value
        new_field = best_match[0]()
    return new_field



