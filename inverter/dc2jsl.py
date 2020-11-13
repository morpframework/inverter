import dataclasses
import typing
from datetime import date, datetime

import jsl

from .common import dataclass_check_type, dataclass_get_type, is_dataclass_field


def _set_nullable(prop):
    if not prop.required:
        return jsl.OneOfField([prop, jsl.NullField(name=prop.name)])
    return prop


def dc2jsl(
    schema, *, ignore_required=False, additional_properties=False, mode="default"
):
    """
    Convert ``dataclass`` to ``jsl`` JSON Schema.

    :param schema: ``dataclass`` class
    :param ignore_required: if ``True``, set all fields as nullable
    :param additional_properties: Allow ``additional_properties`` in JSON Schema
    :param mode: mode flag

    :return: ``jsl.Document`` class
    """

    nullable = ignore_required
    attrs = {}

    _additional_properties = additional_properties

    class Options(object):
        additional_properties = _additional_properties

    for attr, prop in schema.__dataclass_fields__.items():
        prop = dataclass_field_to_jsl_field(prop, nullable=nullable, mode=mode)
        if nullable:
            attrs[attr] = _set_nullable(prop)
        else:
            if not prop.required:
                attrs[attr] = prop
            else:
                if isinstance(prop, jsl.StringField):
                    if not prop.pattern:
                        prop.pattern = ".+"
                attrs[attr] = prop

    attrs["Options"] = Options
    Schema = type("Schema", (jsl.Document,), attrs)

    return Schema


def dataclass_field_to_jsl_field(
    prop: dataclasses.Field, nullable=False, mode="default"
) -> jsl.BaseField:

    if mode in ["edit", "edit-process"]:
        update_mode = True
    else:
        update_mode = False
    t = dataclass_check_type(prop, date)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.DateTimeField(name=prop.name, required=t["required"])

    t = dataclass_check_type(prop, datetime)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.DateTimeField(name=prop.name, required=t["required"])

    t = dataclass_check_type(prop, str)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.StringField(name=prop.name, required=t["required"])

    t = dataclass_check_type(prop, int)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.IntField(name=prop.name, required=t["required"])

    t = dataclass_check_type(prop, float)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.NumberField(name=prop.name, required=t["required"])

    t = dataclass_check_type(prop, bool)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.BooleanField(name=prop.name, required=t["required"])

    t = dataclass_check_type(prop, dict)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.DictField(name=prop.name, required=t["required"])

    t = is_dataclass_field(prop)
    if t:
        if update_mode:
            t["required"] = False
        subtype = dc2jsl(t["schema"], nullable=nullable)
        return jsl.DocumentField(
            name=prop.name, document_cls=subtype, required=t["required"]
        )

    t = dataclass_check_type(prop, list)
    if t:
        if update_mode:
            t["required"] = False
        return jsl.ArrayField(name=prop.name, required=t["required"])

    t = dataclass_check_type(prop, typing.List)
    if t:
        if update_mode:
            t["required"] = False

        if "schema" not in t.keys():
            return jsl.ArrayField(name=prop.name, required=t["required"])

        if dataclasses.is_dataclass(t["schema"]):
            subtype = jsl.DocumentField(
                document_cls=dc2jsl(t["schema"], nullable=nullable)
            )
        elif t["schema"] == str:
            subtype = jsl.StringField(name=prop.name)
        elif t["schema"] == int:
            subtype = jsl.IntField(name=prop.name)
        elif t["schema"] == float:
            subtype = jsl.NumberField(name=prop.name)
        elif t["schema"] == dict:
            subtype = jsl.DictField(name=prop.name)
        else:
            raise KeyError(t["schema"])
        return jsl.ArrayField(items=subtype, required=t["required"])

    raise KeyError(prop)


convert = dc2jsl
