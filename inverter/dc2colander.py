import copy
import dataclasses
import typing
from dataclasses import _MISSING_TYPE, field
from datetime import date, datetime
from importlib import import_module

from pkg_resources import resource_filename

import colander
import deform
from deform.schema import default_widget_makers
from deform.widget import HiddenWidget, TextAreaWidget, TextInputWidget

from .common import (dataclass_check_type, dataclass_get_type,
                     is_dataclass_field)


def replace_colander_null(appstruct, value=None):
    out = {}
    for k, v in appstruct.items():
        if isinstance(v, dict):
            out[k] = replace_colander_null(v)
        elif isinstance(v, list):
            out[k] = list(map(lambda x: x if x != colander.null else value, v))
        else:
            out[k] = v if v != colander.null else value
    return out


class ValidatorsWrapper(object):
    def __init__(self, validators, request, schema, mode=None):
        self.request = request
        self.schema = schema
        self.mode = mode
        self.validators = validators

    def __call__(self, node, value):
        for validator in self.validators:
            error = validator(
                request=self.request,
                schema=self.schema,
                field=node.name,
                value=value,
                mode=self.mode,
            )
            if error:
                raise colander.Invalid(node, error)


class PreparersWrapper(object):
    def __init__(self, preparers, request, schema, mode=None):
        self.preparers = preparers
        self.request = request
        self.schema = schema
        self.mode = mode

    def __call__(self, value):
        if value is colander.null:
            value = None
        for preparer in self.preparers:
            value = preparer(
                request=self.request, schema=self.schema, value=value, mode=self.mode
            )
        return value


class SchemaNode(colander.SchemaNode):
    def serialize(self, appstruct=colander.null):
        # workaround with deform serialization issue with colander.drop
        if appstruct is colander.null:
            appstruct = self.default
        if appstruct is colander.drop:
            appstruct = colander.null
        # if isinstance(appstruct, colander.deferred):
        #    appstruct = colander.null
        cstruct = self.typ.serialize(self, appstruct)
        return cstruct


def colander_params(prop, oid_prefix, schema, request, mode=None, **kwargs):
    t = dataclass_get_type(prop)

    default_value = None
    if t["type"] == dict:
        default_value = {}
    elif t["type"] == list:
        default_value = []
    elif t["type"] == set:
        default_value = set()

    if (
        not isinstance(prop.default, dataclasses._MISSING_TYPE)
        and prop.default is not None
    ):
        default_value = prop.default
    elif (
        not isinstance(prop.default_factory, dataclasses._MISSING_TYPE)
        and prop.default_factory is not None
    ):
        default_value = prop.default_factory()

    params = {
        "name": prop.name,
        "oid": "%s-%s" % (oid_prefix, prop.name),
        "missing": colander.required if t["required"] else default_value,
        "default": default_value,
    }

    if "deform.widget" in prop.metadata.keys():
        params["widget"] = copy.copy(prop.metadata["deform.widget"])
    elif "deform.widget_factory" in prop.metadata.keys():
        params["widget"] = prop.metadata["deform.widget_factory"](request)

    validators = prop.metadata.get("validators", None)
    if validators:
        params["validator"] = ValidatorsWrapper(
            validators, schema=schema, request=request, mode=mode
        )

    preparers = prop.metadata.get("preparers", None)
    if preparers:
        params["preparer"] = PreparersWrapper(
            preparers, schema=schema, request=request, mode=mode
        )

    title = prop.metadata.get("title", None)

    if title:
        params["title"] = title

    description = prop.metadata.get("description", None)
    if description:
        params["description"] = description

    params.update(kwargs)
    return params


class String(colander.String):
    def __init__(self, encoding=None, allow_empty=True):
        super().__init__(encoding=encoding, allow_empty=allow_empty)

    def serialize(self, node, appstruct):
        if appstruct is None:
            return colander.null
        return super().serialize(node, appstruct)

    def deserialize(self, node, cstruct):
        res = super().deserialize(node, cstruct)
        return res


class Mapping(colander.Mapping):
    def serialize(self, node, appstruct):
        if appstruct is None:
            appstruct = {}
        return super().serialize(node, appstruct)


class Boolean(colander.Boolean):
    def serialize(self, node, appstruct):
        if appstruct is None:
            return colander.null
        return super().serialize(node, appstruct)

    def deserialize(self, node, appstruct):
        if appstruct is None:
            appstruct = colander.null
        return super().deserialize(node, appstruct)


def dataclass_field_to_colander_schemanode(
    prop: dataclasses.Field, schema, request, oid_prefix="deformField", mode=None
) -> colander.SchemaNode:

    t = dataclass_get_type(prop)
    if t["type"] == date:
        params = colander_params(
            prop,
            oid_prefix,
            typ=colander.Date(),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
    if t["type"] == datetime:
        params = colander_params(
            prop,
            oid_prefix,
            typ=colander.DateTime(),
            schema=schema,
            request=request,
            mode=mode,
        )

        return SchemaNode(**params)
    if t["type"] == str:
        params = colander_params(
            prop, oid_prefix, typ=String(allow_empty=True), schema=schema, request=request, mode=mode,
        )
        return SchemaNode(**params)
    if t["type"] == int:
        params = colander_params(
            prop,
            oid_prefix,
            typ=colander.Integer(),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
    if t["type"] == float:
        params = colander_params(
            prop,
            oid_prefix,
            typ=colander.Float(),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
    if t["type"] == bool:
        params = colander_params(
            prop, oid_prefix, typ=Boolean(), schema=schema, request=request, mode=mode,
        )
        return SchemaNode(**params)

    if is_dataclass_field(prop):
        subtype = dc2colander(
            t["type"],
            request=request,
            colander_schema_type=colander.MappingSchema,
            mode=mode,
        )

        return subtype()
    if t["type"] == dict:
        params = colander_params(
            prop,
            oid_prefix,
            typ=Mapping(unknown="preserve"),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
    if t["type"] == list:
        params = colander_params(
            prop,
            oid_prefix,
            typ=colander.List(),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
    if t["type"] == deform.FileData:
        params = colander_params(
            prop,
            oid_prefix,
            typ=deform.FileData(),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
    if t["type"] == set:
        params = colander_params(
            prop,
            oid_prefix,
            typ=colander.Set(),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
    raise KeyError(prop)


def dc2colander(
    schema,
    request,
    mode="default",
    include_fields: typing.List[str] = None,
    exclude_fields: typing.List[str] = None,
    hidden_fields: typing.List[str] = None,
    readonly_fields: typing.List[str] = None,
    include_schema_validators: bool = True,
    colander_schema_type: typing.Type[colander.Schema] = colander.MappingSchema,
    oid_prefix: str = "deformField",
    dataclass_field_to_colander_schemanode=dataclass_field_to_colander_schemanode,
) -> typing.Type[colander.MappingSchema]:
    # output colander schema from dataclass schema
    attrs = {}

    include_fields = include_fields or []
    exclude_fields = exclude_fields or []
    hidden_fields = hidden_fields or []
    readonly_fields = readonly_fields or []

    if mode == "edit":
        readonly_fields += [
            attr
            for attr, prop in schema.__dataclass_fields__.items()
            if (
                not prop.metadata.get("editable", True)
                or prop.metadata.get("readonly", False)
            )
        ]
    elif mode == "edit-process":
        exclude_fields += [
            attr
            for attr, prop in schema.__dataclass_fields__.items()
            if (
                not prop.metadata.get("editable", True)
                or prop.metadata.get("readonly", False)
            )
        ]
    else:
        readonly_fields += [
            attr
            for attr, prop in schema.__dataclass_fields__.items()
            if (prop.metadata.get("readonly", False))
        ]

    if include_fields:
        for attr, prop in schema.__dataclass_fields__.items():
            if prop.name in include_fields and prop.name not in exclude_fields:
                prop = dataclass_field_to_colander_schemanode(
                    prop,
                    oid_prefix=oid_prefix,
                    schema=schema,
                    request=request,
                    mode=mode,
                )
                attrs[attr] = prop
    else:
        for attr, prop in schema.__dataclass_fields__.items():
            if prop.name not in exclude_fields:
                prop = dataclass_field_to_colander_schemanode(
                    prop,
                    oid_prefix=oid_prefix,
                    schema=schema,
                    request=request,
                    mode=mode,
                )
                attrs[attr] = prop

    for attr, prop in attrs.items():
        dcprop = schema.__dataclass_fields__[attr]

        t = dataclass_get_type(dcprop)
        if attr in hidden_fields:
            if prop.widget is None:
                prop.widget = HiddenWidget()
            else:
                prop.widget.hidden = True

        if attr in readonly_fields:
            if prop.widget is None:
                prop_widget = default_widget_makers.get(prop.typ.__class__, None)
                if prop_widget is None:
                    prop_widget = TextInputWidget
                prop.widget = prop_widget()

            prop.widget.readonly = True

        if t["type"] == str:
            if dcprop.metadata.get("format", None) == "text":
                if prop.widget is None:
                    prop.widget = TextAreaWidget()

    if include_schema_validators:

        def validator(self, node, appstruct):
            vdata = replace_colander_null(appstruct)
            form_validators = getattr(schema, "__validators__", [])
            form_validators += request.app.get_formvalidators(schema)

            for form_validator in form_validators:
                required_binds = getattr(form_validator, "__required_binds__", [])
                kwargs = {}
                for k in required_binds:
                    if self.bindings is None or (k not in self.bindings.keys()):
                        raise AssertionError(
                            "Required bind variable '{}' is not set on '{}'".format(
                                k, self
                            )
                        )
                    else:
                        kwargs[k] = self.bindings[k]

                fe = form_validator(
                    schema=schema,
                    data=vdata,
                    mode=mode,
                    **(self.bindings or {"request": request}),
                )
                if fe:
                    if fe.get("field", None):
                        raise colander.Invalid(node[fe["field"]], fe["message"])
                    raise colander.Invalid(node, fe["message"])

        attrs["validator"] = validator

    Schema = type("Schema", (colander_schema_type,), attrs)

    return Schema


convert = dc2colander
