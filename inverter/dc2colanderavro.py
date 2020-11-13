import dataclasses
import json
import typing
from datetime import date, datetime, timedelta

import colander
import pytz

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
    prop: dataclasses.Field,
    schema,
    request,
    oid_prefix="deformField",
    mode=None,
    default_tzinfo=pytz.UTC,
    metadata=None,
) -> colander.SchemaNode:

    t = dataclass_get_type(prop)
    metadata = metadata or {}
    t["metadata"].update(metadata)
    field_factory = t["metadata"].get("colander.field_factory", None)
    if field_factory:
        params = colander_params(
            prop,
            oid_prefix,
            typ=field_factory(request),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)

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
            prop,
            oid_prefix,
            typ=Str(allow_empty=True),
            schema=schema,
            request=request,
            mode=mode,
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
            default_tzinfo=default_tzinfo,
            field_metadata=metadata,
        )
        return subtype()

    if t["type"] == dict:
        params = colander_params(
            prop,
            oid_prefix,
            typ=JSON(),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)

    return orig_dc2colander_node(
        prop=prop,
        schema=schema,
        request=request,
        oid_prefix=oid_prefix,
        mode=mode,
        default_tzinfo=default_tzinfo,
        metadata=metadata,
    )


def dc2colanderavro(
    schema,
    *,
    include_fields: typing.List[str] = None,
    exclude_fields: typing.List[str] = None,
    hidden_fields: typing.List[str] = None,
    readonly_fields: typing.List[str] = None,
    include_schema_validators: bool = True,
    colander_schema_type: typing.Type[colander.Schema] = colander.MappingSchema,
    oid_prefix: str = "deformField",
    request=None,
    mode="default",
    default_tzinfo=None,
    field_metadata=None,
) -> typing.Type[colander.MappingSchema]:
    """
    Converts ``dataclass`` to ``colander.Schema`` that serializes to Avro compatible
    dictionary.

    - date is serialized as number days from epoch
    - datetime is serialized as number of miliseconds from epoch
    - dictionary (JSON field) is serialized as JSON string

    Accepted parameters are the same as ``inverter.dc2colander.convert``.
    """
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
        default_tzinfo=default_tzinfo,
        field_metadata=field_metadata,
    )


convert = dc2colanderavro
