import copy
import dataclasses
import typing
from datetime import date, datetime

from .common import dataclass_check_type, dataclass_get_type, is_dataclass_field


def dataclass_field_to_esmapping(
    prop: dataclasses.Field, schema, request, *, metadata=None
):
    t = dataclass_get_type(prop)
    metadata = metadata or {}
    meta = copy.deepcopy(t["metadata"])
    meta.update(metadata)
    index = meta.get("index", None)
    mapping_opts = meta.get("es.mapping_options", {})
    if index is not None:
        mapping_opts.setdefault("index", index)
    if t["type"] == date:
        mfield = {"type": "date"}
        mfield.update(mapping_opts)
        return mfield
    if t["type"] == datetime:
        mfield = {"type": "date"}
        mfield.update(mapping_opts)
        return mfield
    if t["type"] == str:
        fmt = meta.get("format", None)
        if fmt is None:
            mfield = {"type": "keyword"}
        elif fmt == "text" or fmt.startswith("text/"):
            mfield = {"type": "text", "fields": {"raw": {"type": "keyword"}}}
        else:
            mfield = {"type": "keyword"}
        mfield.update(mapping_opts)
        return mfield
    if t["type"] == int:
        mfield = {"type": "long"}
        mfield.update(mapping_opts)
        return mfield
    if t["type"] == float:
        mfield = {"type": "double"}
        mfield.update(mapping_opts)
        return mfield
    if t["type"] == bool:
        mfield = {"type": "boolean"}
        mfield.update(mapping_opts)
        return mfield
    if is_dataclass_field(prop):
        mfield = {"type": "object"}
        mfield.update(mapping_opts)
    if t["type"] == dict:
        mfield = {"type": "object"}
        mfield.update(mapping_opts)
        return mfield
    if t["type"] == list:
        mfield = {"type": "nested"}
        mfield.update(mapping_opts)
        return mfield
    if t["type"] == set:
        mfield = {"type": "nested"}
        mfield.update(mapping_opts)
        return mfield
    raise KeyError(prop)


def dc2esmapping(
    schema: type,
    *,
    request: typing.Any = None,
    metadata: typing.Optional[dict] = None,
    include_fields=None,
    exclude_fields=None,
):

    include_fields = include_fields or []
    exclude_fields = exclude_fields or []
    mprops = {}
    if include_fields:
        for attr, prop in schema.__dataclass_fields__.items():
            if prop.name in include_fields and prop.name not in exclude_fields:
                mprops[attr] = dataclass_field_to_esmapping(
                    prop, schema, request, metadata=metadata
                )
    else:
        for attr, prop in schema.__dataclass_fields__.items():
            if prop.name not in exclude_fields:
                mprops[attr] = dataclass_field_to_esmapping(
                    prop, schema, request, metadata=metadata
                )

    return {"mappings": {"properties": mprops}}


convert = dc2esmapping
