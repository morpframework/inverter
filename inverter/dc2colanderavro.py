import dataclasses
import json
import typing
from datetime import date, datetime, timedelta

import pytz

import colander

from .common import dataclass_check_type, dataclass_get_type, is_dataclass_field
from .dc2colander import SchemaNode, colander_params
from .dc2colander import dataclass_field_to_colander_schemanode as orig_dc2colander_node
from .dc2colander import dc2colander
from .dc2colanderjson import Boolean, Date, DateTime, Float, Int, Str


class JSON(Str):
    def serialize(self, node, appstruct):
        if appstruct:
            appstruct = json.dumps(appstruct, indent=2)
        return super().serialize(node, appstruct)

    def deserialize(self, node, cstruct):
        if cstruct and cstruct.strip():
            cstruct = json.loads(cstruct)
        return super().deserialize(node, cstruct)


def dataclass_field_to_colander_schemanode(
    prop: dataclasses.Field, schema, request, oid_prefix="deformField", mode=None,
) -> colander.SchemaNode:

    t = dataclass_get_type(prop)
    if t["type"] == date:
        params = colander_params(
            prop, oid_prefix, typ=Date(), schema=schema, request=request, mode=mode
        )
        return SchemaNode(**params)
    if t["type"] == datetime:
        params = colander_params(
            prop, oid_prefix, typ=DateTime(), schema=schema, request=request, mode=mode
        )
        return SchemaNode(**params)
    if t["type"] == str:
        params = colander_params(
            prop, oid_prefix, typ=Str(), schema=schema, request=request, mode=mode
        )
        return SchemaNode(**params)
    if t["type"] == int:
        params = colander_params(
            prop, oid_prefix, typ=Int(), schema=schema, request=request, mode=mode
        )
        return SchemaNode(**params)
    if t["type"] == float:
        params = colander_params(
            prop, oid_prefix, typ=Float(), schema=schema, request=request, mode=mode
        )
        return SchemaNode(**params)
    if t["type"] == bool:
        params = colander_params(
            prop, oid_prefix, typ=Boolean(), schema=schema, request=request, mode=mode
        )
        return SchemaNode(**params)

    if is_dataclass_field(prop):
        subtype = dc2colanderavro(
            prop,
            colander_schema_type=colander.MappingSchema,
            request=request,
            mode=mode,
        )
        return subtype()

    if t["type"] == dict:
        params = colander_params(
            prop, oid_prefix, typ=JSON(), schema=schema, request=request, mode=mode,
        )
        return SchemaNode(**params)

    return orig_dc2colander_node(prop, oid_prefix, request)


def dc2colanderavro(
    schema,
    include_fields: typing.List[str] = None,
    exclude_fields: typing.List[str] = None,
    hidden_fields: typing.List[str] = None,
    readonly_fields: typing.List[str] = None,
    include_schema_validators: bool = True,
    colander_schema_type: typing.Type[colander.Schema] = colander.MappingSchema,
    oid_prefix: str = "deformField",
    request=None,
    mode="default",
) -> typing.Type[colander.MappingSchema]:
    return dc2colander(
        schema,
        request=request,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
        hidden_fields=hidden_fields,
        readonly_fields=readonly_fields,
        include_schema_validators=include_schema_validators,
        colander_schema_type=colander_schema_type,
        oid_prefix=oid_prefix,
        dataclass_field_to_colander_schemanode=dataclass_field_to_colander_schemanode,
        mode=mode,
    )


convert = dc2colanderavro
