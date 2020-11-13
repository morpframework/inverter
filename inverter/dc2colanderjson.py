import dataclasses
import typing
from datetime import date, datetime, timedelta

import colander
import pytz

from .common import dataclass_check_type, dataclass_get_type, is_dataclass_field
from .dc2colander import Mapping, SchemaNode, colander_params
from .dc2colander import dataclass_field_to_colander_schemanode as orig_dc2colander_node
from .dc2colander import dc2colander

epoch_date = date(1970, 1, 1)


class Boolean(colander.Boolean):
    def deserialize(self, node, appstruct):
        if appstruct is True:
            appstruct = "true"
        elif appstruct is False:
            appstruct = "false"
        elif appstruct is None:
            appstruct = colander.null
        return super(Boolean, self).deserialize(node, appstruct)

    def serialize(self, node, appstruct):
        result = super(Boolean, self).serialize(node, appstruct)
        if result is colander.null:
            return None
        if result is not colander.null:
            if result.lower() == "true":
                result = True
            else:
                result = False
        return result


class Float(colander.Float):
    def deserialize(self, node, cstruct):
        if cstruct is None:
            return colander.null
        if cstruct is not colander.null:
            cstruct = float(cstruct)
        return super(Float, self).deserialize(node, cstruct)

    def serialize(self, node, appstruct):
        result = super(Float, self).serialize(node, appstruct)
        if result is colander.null:
            return None
        if result is not colander.null:
            result = float(result)
        return result


class Int(colander.Int):
    def deserialize(self, node, cstruct):
        if cstruct is None:
            return colander.null

        if cstruct is not colander.null:
            cstruct = int(cstruct)
        return super(Int, self).deserialize(node, cstruct)

    def serialize(self, node, appstruct):
        result = super(Int, self).serialize(node, appstruct)
        if result is colander.null:
            return None

        if result is not colander.null:
            result = int(result)
        return result


class Str(colander.Str):
    def deserialize(self, node, cstruct):
        if cstruct is None:
            return colander.null
        return super(Str, self).deserialize(node, cstruct)

    def serialize(self, node, appstruct):
        if appstruct is None:
            return None
        result = super(Str, self).serialize(node, appstruct)
        if result is colander.null:
            return None
        return result


class Date(colander.Date):
    def serialize(self, node, appstruct):
        result = super(Date, self).serialize(node, appstruct)
        if result is colander.null:
            return None

        return (appstruct - epoch_date).days

    def deserialize(self, node, cstruct):
        if cstruct and not (isinstance(cstruct, int) or isinstance(cstruct, str)):
            raise colander.Invalid(
                node,
                (
                    "Date is expected to be number of days after 1970-01-01, "
                    "or in ISO formatted date string"
                ),
            )

        if cstruct and isinstance(cstruct, int):
            cstruct = (epoch_date + timedelta(days=cstruct)).strftime(r"%Y-%m-%d")
        return super().deserialize(node, cstruct)


class DateTime(colander.DateTime):
    def serialize(self, node, appstruct):
        if appstruct:
            appstruct = appstruct.astimezone(pytz.UTC)
        result = super(DateTime, self).serialize(node, appstruct)
        if result is colander.null:
            return None

        return int(appstruct.timestamp() * 1000)

    def deserialize(self, node, cstruct):
        if cstruct and not (isinstance(cstruct, int) or isinstance(cstruct, str)):
            raise colander.Invalid(
                node,
                (
                    "DateTime is expected to in Unix timestamp "
                    "in miliseconds in UTC, or in ISO formatted date string"
                ),
            )
        if cstruct and isinstance(cstruct, int):
            cstruct = datetime.fromtimestamp(
                int(cstruct) / 1000, tz=pytz.UTC
            ).isoformat()
        result = super().deserialize(node, cstruct)
        if result:
            return result.astimezone(self.default_tzinfo)
        return result


def dataclass_field_to_colander_schemanode(
    prop: dataclasses.Field,
    schema,
    request,
    oid_prefix="deformField",
    mode=None,
    metadata=None,
    default_tzinfo=pytz.UTC,
) -> colander.SchemaNode:

    t = dataclass_get_type(prop)
    metadata = metadata or {}
    t["metadata"].update(metadata)
    json_field_factory = t["metadata"].get("colanderjson.field_factory", None)
    if json_field_factory:
        params = colander_params(
            prop,
            oid_prefix,
            typ=json_field_factory(request),
            schema=schema,
            request=request,
            mode=mode,
        )
        return SchemaNode(**params)
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
            prop,
            oid_prefix,
            typ=DateTime(default_tzinfo=default_tzinfo),
            schema=schema,
            request=request,
            mode=mode,
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
        subtype = dc2colanderjson(
            t["type"],
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
            typ=Mapping(unknown="preserve"),
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


def dc2colanderjson(
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
    default_tzinfo=pytz.UTC,
    field_metadata=None,
) -> typing.Type[colander.MappingSchema]:

    """
    Converts ``dataclass`` to ``colander.Schema`` that serializes to JSON.

    - date is serialized as number days from epoch
    - datetime is serialized as number of miliseconds from epoch

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
        field_metadata=field_metadata,
        default_tzinfo=default_tzinfo,
    )


convert = dc2colanderjson
