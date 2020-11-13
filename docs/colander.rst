Colander Converters
====================

``inverter`` provide several converters to ``colander`` based schema:

- ``dc2colander`` - converts ``dataclass`` to standard ``colander`` schema.
- ``dc2colanderjson`` - converts ``dataclass`` to a ``colander`` schema that serialize to JSON
  
  - date is serialized as number days from epoch
  - datetime is serialized as number of miliseconds from epoch

- ``dc2colanderavro`` - converts ``dataclass`` to a ``colander`` schema that serialize to ``avro`` compatible data
  
  - date is serialized as number days from epoch
  - datetime is serialized as number of miliseconds from epoch
  - dictionary (JSON field) is serialized as JSON string

- ``dc2colanderESjson`` - converts ``dataclass`` to a ``colander`` schema that serialize to ES compatible JSON
  
  - date is serialized as YYYY-MM-DD string
  - datetime is serialized as iso8601 string

.. autofunction:: inverter.dc2colander.convert

.. autofunction:: inverter.dc2colanderjson.convert

.. autofunction:: inverter.dc2colanderavro.convert

.. autofunction:: inverter.dc2colanderESjson.convert