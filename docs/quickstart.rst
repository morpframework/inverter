Quickstart
============

Installation
-------------

:: 

  pip install inverter

Creating Schema 
----------------

Following example creates ``colander`` schema from a ``dataclass``

.. code-block:: python

   from dataclasses import dataclass, field
   import typing
   from deform.widget import PasswordWidget
   from inverter import dc2colander
   import colander

   @dataclass
   class LoginForm(object):

       username: typing.Optional[str] = field(metadata={'required': True})
       password: typing.Optional[str] = field(
                        metadata={'required': True, 
                                  'deform.widget': PasswordWidget()})


   request = {}
   cschema = dc2colander.convert(LoginForm, request)

   assert issubclass(cschema, colander.Schema)


The same schema can also be converted to Avro Schema

.. code-block:: python

   from inverter import dc2avsc
   
   avsc = dc2avsc.convert(LoginForm, request, namespace='myapp')

   assert avsc == {
       'namespace': 'myapp', 
       'type': 'record', 
       'name': 'LoginForm', 
       'fields': [
           {'name': 'username', 'type': ['string', 'null']}, 
           {'name': 'password', 'type': ['string', 'null']}]}