import copy
import dataclasses
import typing
from dataclasses import field
from datetime import date, datetime
from importlib import import_module

import colander
import sqlalchemy
import sqlalchemy_jsonfield as sajson
import sqlalchemy_utils as sautils
from deform.widget import HiddenWidget
from pkg_resources import resource_filename

from .common import dataclass_check_type, dataclass_get_type, is_dataclass_field


def sqlalchemy_params(prop, typ, **kwargs):
    t = dataclass_get_type(prop)

    params = {"name": prop.name, "type_": typ}

    if not isinstance(prop.default, dataclasses._MISSING_TYPE):
        params["default"] = prop.default

    if not isinstance(prop.default_factory, dataclasses._MISSING_TYPE):
        params["default"] = prop.default_factory

    if t["metadata"].get("primary_key", None) is True:
        params["primary_key"] = True

    if t["metadata"].get("index", None) is True:
        params["index"] = True

    if t["metadata"].get("autoincrement", None) is True:
        params["autoincrement"] = True

    if t["metadata"].get("unique", None) is True:
        params["unique"] = True

    params.update(kwargs)
    return params


def dataclass_field_to_sqla_col(prop: dataclasses.Field) -> sqlalchemy.Column:
    t = dataclass_get_type(prop)
    if t["type"] == date:
        params = sqlalchemy_params(prop, typ=sqlalchemy.Date())
        return sqlalchemy.Column(**params)
    if t["type"] == datetime:
        params = sqlalchemy_params(prop, typ=sqlalchemy.DateTime(timezone=True))
        return sqlalchemy.Column(**params)
    if t["type"] == str:
        str_format = t["metadata"].get("format", None)

        if str_format and "/" in str_format:
            str_format = str_format.split("/")[0]

        if str_format == "text":
            params = sqlalchemy_params(prop, typ=sqlalchemy.Text())
        elif str_format == "uuid":
            params = sqlalchemy_params(prop, typ=sautils.UUIDType())
        elif str_format == "fulltextindex":
            params = sqlalchemy_params(prop, typ=sautils.TSVectorType)
        else:
            str_len = prop.metadata.get("length", 256)
            params = sqlalchemy_params(prop, typ=sqlalchemy.String(str_len))
        return sqlalchemy.Column(**params)
    if t["type"] == int:
        if t["metadata"].get("format", None) == "bigint":
            params = sqlalchemy_params(prop, typ=sqlalchemy.BigInteger())
        else:
            params = sqlalchemy_params(prop, typ=sqlalchemy.Integer())
        return sqlalchemy.Column(**params)
    if t["type"] == float:
        if t["metadata"].get("format", None) == "numeric":
            params = sqlalchemy_params(prop, typ=sqlalchemy.Numeric())
        else:
            params = sqlalchemy_params(prop, typ=sqlalchemy.Float())

        return sqlalchemy.Column(**params)
    if t["type"] == bool:
        params = sqlalchemy_params(prop, typ=sqlalchemy.Boolean())
        return sqlalchemy.Column(**params)

    if is_dataclass_field(prop):
        raise NotImplementedError("Sub schema is not supported")

    if t["type"] == dict:
        params = sqlalchemy_params(prop, typ=sajson.JSONField())
        return sqlalchemy.Column(**params)
    if t["type"] == list:
        params = sqlalchemy_params(prop, typ=sajson.JSONField())
        return sqlalchemy.Column(**params)

    raise KeyError(prop)


def dc2pgsqla(schema, metadata, *, name=None) -> sqlalchemy.Table:
    """
    Convert ``dataclass`` to ``sqlalchemy`` ORM model

    :param schema: ``dataclass`` class
    :param metadata: ``sqlalchemy.MetaData`` object
    :param name: model name

    :return: ``sqlalchemy`` ORM class

    **Field metadata handling**

    - ``primary_key: bool`` - primary key flag
    - ``index: bool`` - flag on whether to index the column
    - ``autoincrement: bool`` - flag on whether to make column autoincrement
    - ``unique: bool`` - flag on whether to make column unique
    - ``searchable: bool`` - flag on whether to make column searchable using PGSQL Trigram
    - ``format: str`` - format of data: ``uuid``, ``text``, ``fulltextindex``,
      ``bigint``, ``numeric``. This forces SQLAlchemy to use specific data type
      for the format.
    """
    if name is None:
        if getattr(schema, "__table_name__", None):
            name = schema.__table_name__
        else:
            name = schema.__name__.lower()

    cols = []

    for attr, prop in sorted(schema.__dataclass_fields__.items(), key=lambda x: x[0]):
        prop = dataclass_field_to_sqla_col(prop)
        cols.append(prop)

    Table = sqlalchemy.Table(name, metadata, *cols, extend_existing=True)

    for attr, prop in schema.__dataclass_fields__.items():
        if prop.type in [str, typing.Optional[str]] and prop.metadata.get(
            "searchable", None
        ):
            sqlalchemy.Index(
                "ix_%s_%s_trgm_search" % (name, attr),
                getattr(Table.c, attr),
                postgresql_ops={attr: "gin_trgm_ops"},
                postgresql_using="gin",
                unique=False,
            )

    # FIXME: reject nested schema

    return Table


convert = dc2pgsqla
