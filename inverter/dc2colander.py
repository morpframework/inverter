import copy
import dataclasses
import typing
from dataclasses import _MISSING_TYPE, field
from datetime import date, datetime
from importlib import import_module

import colander
import deform
import pytz
from deform.schema import default_widget_makers
from deform.widget import HiddenWidget, TextAreaWidget, TextInputWidget
from pkg_resources import resource_filename

from .common import dataclass_check_type, dataclass_get_type, is_dataclass_field


def replace_colander_null(appstruct, value=None):
    """
    Replace ``colander.null`` with default value

    :param appstruct: colander ``appstruct`` dictionary
    :type appstruct: ``dict``
    :param value: value to replace ``colander.null`` with, defaults to ``None``

    :return: ``appstruct`` dictionary that have been replaced
    :rtype: ``dict``
    """
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
    """
    This wrapper is used internally to validate data using multiple validators
    """

    def __init__(
        self,
        validators: typing.List[typing.Callable],
        request: typing.Any,
        schema,
        mode=None,
    ):
        """
        :param validators: list of validator callables that accept following parameters:
                           - ``request`` - request object
                           - ``schema`` - dataclass schema
                           - ``field`` - field name
                           - ``value`` - value to be validated
                           - ``mode`` - one of the following: ``'default'``, ``'edit'``, ``'edit-process'``

        :param request: request object that is passed to the schema converter. Accept any.
        :param schema: dataclass schema
        :param mode:  one of the following: ``default``, ``'edit'``, ``'edit-process'``

        """
        self.request = request
        self.schema = schema
        self.mode = mode
        self.validators = validators

    def __call__(self, node, value):
        """
        Execute validators and raise errors

        :param node: ``colander`` field node
        :param value: value to be validated

        :raises colander.Invalid: raised when invalid data is found
        """
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
    """
    This wrapper is used internally to prepare data using multiple preparers
    """

    def __init__(
        self, preparers: typing.List[typing.Callable], request, schema, mode=None
    ):
        """
        :param preparers: list of validator callables that accept following parameters:
                           - ``request`` - request object
                           - ``schema`` - dataclass schema
                           - ``value`` - value to be validated
                           - ``mode`` - one of the following: ``'default'``, ``'edit'``, ``'edit-process'``

        :param request: request object that is passed to the schema converter. Accept any.
        :param schema: dataclass schema
        :param mode:  one of the following: ``'default'``, ``'edit'``, ``'edit-process'``

        """
        self.preparers = preparers
        self.request = request
        self.schema = schema
        self.mode = mode

    def __call__(self, value: typing.Any) -> typing.Any:
        """

        Execute preparers against ``value``

        :param value: data value
        :return: prepared value

        """
        if value is colander.null:
            value = None
        for preparer in self.preparers:
            value = preparer(
                request=self.request, schema=self.schema, value=value, mode=self.mode
            )
        return value


class SchemaNode(colander.SchemaNode):
    """
    Replace the way SchemaNode handles serialization

    :meta private:
    """

    def serialize(self, appstruct=colander.null):
        """
        If ``colander.drop`` is used, ``deform`` seems to output ``colander.drop``
        as the default value in the forms. This fixes that.

        :meta private:
        """
        # workaround with deform serialization issue with colander.drop
        if appstruct is colander.null:
            appstruct = self.default
        if appstruct is colander.drop:
            appstruct = colander.null
        # if isinstance(appstruct, colander.deferred):
        #    appstruct = colander.null
        cstruct = self.typ.serialize(self, appstruct)
        return cstruct


def colander_params(
    prop: dataclasses.Field,
    oid_prefix: str,
    schema: type,
    request: typing.Any,
    mode=None,
    **kwargs,
) -> dict:
    """
    Get parameters for ``colander.SchemaNode`` constructor from ``dataclass.Field``

    :param prop: ``dataclass.Field`` object
    :param oid_prefix: string prefix for use as field oid
    :param schema: ``dataclass`` based class
    :param request: ``request`` object. Accepts anything, as it is merely passed to validators
    :param mode: one of the following: ``'default'``, ``'edit'``, ``'edit-process'``
    :param kwargs: additional parameters to be included into output. Will override derived parameters.

    :return: dictionary of parameters for ``colander.SchemaNode``

    """
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
    prop: dataclasses.Field,
    schema,
    request,
    oid_prefix="deformField",
    mode=None,
    default_tzinfo=pytz.UTC,
    metadata=None,
) -> colander.SchemaNode:

    """
    Converts ``dataclass.Field`` to ``colander.SchemaNode``

    :param prop: ``dataclass.Field`` object
    :param schema: ``dataclass`` class
    :param request: request object
    :param oid_prefix: prefix for field OID, defaults to 'deformField'
    :param mode: One of the following: ``'default'``, ``'edit'``, ``'edit-process'``
    :param default_tzinfo: Default timezone to use for ``datetime`` handling, defaults to ``pytz.UTC``
    :param metadata: additional metadata override

    :return: converted ``colander.SchemaNode``
    """
    metadata = metadata or {}

    t = dataclass_get_type(prop)
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
            typ=colander.DateTime(default_tzinfo=default_tzinfo),
            schema=schema,
            request=request,
            mode=mode,
        )

        return SchemaNode(**params)
    if t["type"] == str:
        params = colander_params(
            prop,
            oid_prefix,
            typ=String(allow_empty=True),
            schema=schema,
            request=request,
            mode=mode,
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
    schema: type,
    *,
    request: typing.Any = None,
    mode="default",
    include_fields: typing.List[str] = None,
    exclude_fields: typing.List[str] = None,
    hidden_fields: typing.List[str] = None,
    readonly_fields: typing.List[str] = None,
    include_schema_validators: bool = True,
    colander_schema_type: typing.Type[colander.Schema] = colander.MappingSchema,
    oid_prefix: str = "deformField",
    default_tzinfo=pytz.UTC,
    field_metadata=None,
    dataclass_field_to_colander_schemanode=dataclass_field_to_colander_schemanode,
) -> typing.Type[colander.MappingSchema]:
    """
    Converts ``dataclass`` to ``colander.Schema``

    :param schema: ``dataclass`` class to be used as schema
    :param request: a request object. This is mainly be passed down to downstream factories, accepts anything.
    :param mode: this flag is used to affect the decision on how validators validate data. accepts one of the following:
                 - ``'default'``
                 - ``'edit'`` - flag used when generating edit form
                 - ``'edit-process'`` - flag used when generating edit processing form
    :param include_fields: List of field names to include
    :type include_fields: typing.List[str]
    :param exclude_fields: List of field names to exclude
    :type exclude_fields: typing.List[str]
    :param hidden_fields: List of field names to hide
    :type hidden_fields: typing.List[str]
    :param readonly_fields: List of field names to made readonly
    :type readonly_fields: typing.List[str]
    :param include_schema_validators: Set whether to include ``__validators__`` from ``dataclass`` during convertion
    :type include_schema_validators: bool
    :param colander_schema_type: base class to use as created output, defaults to colander.MappingSchema.
    :param oid_prefix: string to use as deform OID prefix
    :param default_tzinfo: default timezone for ``datetime`` handling, defaults to ``pytz.UTC``
    :param field_metadata: a dictionary for overriding field metadata. Structure: ``{'<fieldname>': {'metadatakey': 'metadataval'}}``
    :param dataclass_field_to_colander_schemanode: ``colander.SchemaNode`` factory function.

    :return: ``colander.Schema`` class

    **Field metadata handling**

    This function will read several metadata from fields and use it to derive the parameters.

    - ``required: bool`` - flag field as required
    - ``title: str`` - field title
    - ``description: str`` - field description
    - ``validators: typing.List[typing.Callable]`` - a list of validator callables
    - ``preparers: typing.List[typing.Callable]`` - a list of preparer callables
    - ``deform.widget: deform.widget.Widget`` - ``deform.widget.Widget`` object to use as widget.
    - ``deform.widget_factory: typing.Callable`` - a callable with that accept ``request`` and
      returns a ``deform.widget.Widget`` object.
    - ``colander.field_factory: typing.Callable`` - a callable that accept ``request`` and returns a
      ``colander.SchemaType`` object.


    """
    # output colander schema from dataclass schema
    attrs = {}

    include_fields = include_fields or []
    exclude_fields = exclude_fields or []
    hidden_fields = hidden_fields or []
    readonly_fields = readonly_fields or []
    field_metadata = field_metadata or {}
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
                    metadata=field_metadata.get(prop.name, {}),
                    default_tzinfo=default_tzinfo,
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
                    metadata=field_metadata.get(prop.name, {}),
                    default_tzinfo=default_tzinfo,
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
            form_validators = copy.deepcopy(getattr(schema, "__validators__", []))
            # FIXME: this create a coupling with morpfw, need to decouple
            app = getattr(request, "app", None)
            if app:
                get_formvalidators = getattr(app, "get_formvalidators", None)
                if get_formvalidators:
                    form_validators += get_formvalidators(schema)

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
