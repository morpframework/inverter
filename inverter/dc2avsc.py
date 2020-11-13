import datetime
import typing

from .common import dataclass_check_type, dataclass_get_type, is_dataclass_field


def dataclass_field_to_avsc_field(prop, schema, request, ignore_required=False):
    """
    Converts ``dataclass.Field`` to Avro schema field dictionary.

    :param prop: ``dataclass.Field`` object
    :param schema: ``dataclass`` class
    :param request: request object, accepts any.
    :param ignore_required: if ``True``, force all fields as non-required
    :type ignore_required: bool
    """

    t = dataclass_get_type(prop)
    field = {"name": prop.name}

    if not ignore_required:
        required = prop.metadata.get("required", False)
    else:
        required = False

    if t["type"] == str and prop.metadata.get("format", None) == "uuid":
        field["type"] = [{"type": "string", "logicalType": "uuid"}]
        if not required:
            field["type"].append("null")
        return field

    if t["type"] == str:
        field["type"] = ["string"]
        if not required:
            field["type"].append("null")
        return field

    if t["type"] == int:
        field["type"] = ["int"]
        if not required:
            field["type"].append("null")
        return field

    if t["type"] == float:
        field["type"] = ["double"]
        if not required:
            field["type"].append("null")
        return field

    if t["type"] == bool:
        field["type"] = ["boolean"]
        if not required:
            field["type"].append("null")
        return field

    if t["type"] == datetime.datetime:
        field["type"] = [
            {
                "type": "long",
                "logicalType": "timestamp-millis",
            },
        ]
        if not required:
            field["type"].append("null")
        return field

    if t["type"] == datetime.date:
        field["type"] = [
            {
                "type": "int",
                "logicalType": "date",
            }
        ]
        if not required:
            field["type"].append("null")
        return field

    if is_dataclass_field(prop):
        subtype = dc2avsc(prop, request=request)
        return subtype

    if t["type"] == dict:
        # FIXME: dictionary field are expected to be
        # encoded as string for now.
        # ideally it should be schemaless dict, but
        # it is unclear how to achieve this with
        # avro
        field["type"] = ["string"]
        if not required:
            field["type"].append("null")
        return field
    raise TypeError("Unknown Avro type for %s" % t["type"])


def dc2avsc(
    schema,
    *,
    request=None,
    include_fields: typing.List[str] = None,
    exclude_fields: typing.List[str] = None,
    namespace="inverter",
    ignore_required=True,
):
    """
    Converts ``dataclass`` to Avro Schema JSON dictionary

    :param schema: ``dataclass`` class
    :param request: request object, accepts Any
    :param include_fields: List of field names to include
    :type include_fields: typing.List[str]
    :param exclude_fields: List of field names to exclude
    :type exclude_fields: typing.List[str]
    :param namespace: Avro schema namespace, defaults to 'inverter'
    :param ignore_required: if True, force all fields to be non-required
    :type ignore_required: bool

    :return: dictionary representing Avro Schema.
    """
    result = {
        "namespace": namespace,
        "type": "record",
        "name": str(schema.__name__),
        "fields": [],
    }
    for attr, prop in schema.__dataclass_fields__.items():
        field = dataclass_field_to_avsc_field(
            prop, schema=schema, request=request, ignore_required=ignore_required
        )
        result["fields"].append(field)

    return result


convert = dc2avsc
