.. inverter documentation master file, created by
   sphinx-quickstart on Thu Nov 12 17:05:27 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

inverter: Convert dataclass to another class
============================================

``inverter`` is a library that help convert D(ata)C(lass) to A(nother) C(lass). Supported
output classes / schemas are:

- `colander <https://docs.pylonsproject.org/projects/colander/en/latest/>`_ schema model.
- `Apache Avro <http://avro.apache.org/docs/current/spec.html>`_ schema JSON.
- `JSON Schema <https://json-schema.org/>`_ through `Python JSL library <https://jsl.readthedocs.io/en/latest/>`_ model.
- `SQLALchemy <https://docs.sqlalchemy.org/>`_ model (current converter outputs primarily PostgreSQL compatible model).

.. note:: 
   This library was originally part of ``morpfw`` project, and might still
   have some coupling leftover to morpfw.

