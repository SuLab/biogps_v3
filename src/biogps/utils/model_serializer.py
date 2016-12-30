'''
An alternative model serializer for django models
Modified from: http://djangosnippets.org/snippets/1162/

Requirement:
    pyxslt (requires libxml2 and libxslt and their python-bindings)

Django's serializer has some limitations which makes it a bit of a pain to use. Basically it will ignore any atributes that have been added to a model object.

The code below is for an alternative serializer. This version allows you select what attributes will be serialized on a per object basis. It also allows you to either serialize the data into json or xml.

The original json encoder was written by Wolfram Kriesing

Example Usage:

dumper = DataDumper()
dumper.set_model_attrs(attrs)
dumper.dump(model_instance,'xml')
dumper.dump(model_instance,'json')
dumper.dump(queryset,'xml')

or just use the shortcut:
serialize(model_instance, 'xml', attrs)
serialize(model_instance, 'json')
serialize(queryset,'json', attrs=['id', 'title'])
serialize(pythonobject, 'json')

if attrs is not passed, output all available model fields
if passed data are not a model instance (or a list of), the data will be
 serialized as they are. Passed "attrs" has no effect.
'''

import types
import json
from decimal import Decimal
try:
    import pyxslt.serialize
except:
    pass
from django.db import models
from django.core.serializers.json import DateTimeAwareJSONEncoder

#This list contains the names of Data Models wanted to be treated the same as
# Django's own Model class, e.g., some data models are not derived from
# Relational DB.
OTHER_DATA_MODELS = ['BiogpsSearchResult']


class XMLSerializeError(Exception):
    pass


class DataDumper:
#    fields = {}
#    def selectObjectFields(self,objectType,fields = []):
#        self.fields[objectType] = fields

    model_attrs = None   # to store the list of attributes to return in
                         # serialized object if the passed data is a list
                         # of model instance or a single model instance

    def set_model_attrs(self, attrs=None):
        self.model_attrs = attrs

    def set_model_serializer(self, serializer=None, **kwargs):
        self.model_serializer = serializer
        self.model_serializer_kwargs = kwargs

    def dump(self, data, format='xml'):
        """
        The main issues with django's default json serializer is that properties that
        had been added to a object dynamically are being ignored (and it also has
        problems with some models).
        """

        def _is_model(data):
            return isinstance(data, models.Model) or \
                   getattr(getattr(data, '__class__', None), '__name__', None) in OTHER_DATA_MODELS

        def _any(data):
            ret = None
            if _is_model(data):
                ret = _model(data)
            elif isinstance(data, types.ListType) or \
                 isinstance(data, models.query.QuerySet):
                ret = _list(data)
            elif isinstance(data, dict):
                ret = _dict(data)
            elif isinstance(data, Decimal):
                # json.dumps() cant handle Decimal
                ret = str(data)
            else:
                ret = data
            return ret

        def _model(data):
            '''Input data is a Model instance.
               This is a modified _model method to replace the original one
               (commented out below)
            '''
            ret = {}
            if self.model_serializer:
                # if model_serializer is passed and valid, call it to get ret
                if type(self.model_serializer) in types.StringTypes:
                    _method = getattr(data, self.model_serializer, None)
                    if type(_method) is types.MethodType:
                        ret = _method(**self.model_serializer_kwargs)
                elif type(self.model_serializer) is types.FunctionType:
                    ret = self.model_serializer(data, **self.model_serializer_kwargs)
            else:
                # otherwise, check model_attrs to generate ret
                if self.model_attrs is None:
                    #by default, output all available model fields
                    self.model_attrs = [f.attname for f in data._meta.fields]

                for attr in self.model_attrs:
                    try:
                        _value = getattr(data, attr)
                    except AttributeError:
                        pass
                    # if _value is a instance method, call this method and assign
                    # the returned value, otherwise, just use _value as it is.
                    ret[attr] = _value() if type(_value) is types.MethodType else _value
            return _any(ret)

        def _list(data):
            ret = []
            for v in data:
                ret.append(_any(v))
            return ret

        def _dict(data):
            ret = {}
            for k, v in data.items():
                ret[k] = _any(v)
            return ret

        ret = _any(data)
        if(format == 'xml'):
            try:
                return pyxslt.serialize.toString(prettyPrintXml=False,
                                                 data=ret,
                                                 rootTagName='biogps')
            except NameError:
                raise XMLSerializeError('module "pyxslt" is required for XML serialization.')
        else:
            return json.dumps(ret, cls=DateTimeAwareJSONEncoder)


def serialize(data, format='json', attrs=None, model_serializer=None, **kwargs):
    '''A shortcut function to call DataDumper.
        @return: a serialized string

        @param data: any python object
        @param format: currently supports "json" or "xml" with "json" as the default.
        @param attrs: if passed data is a model instance or a list of model
                      instances, only listed attributes are serialized.
                      If the passed name matches a instance method, this method
                      will be called (without argument) and output the returned
                      value.
                      If attrs is not passed, output all available model fields
                      If passed data is not a model instance (or a list of),
                      the data will be serialized as it is. Passed "attrs" has no effect.
        @param model_serializer: alternatively, you can also use a complete custom
                                 serializer to convert Model instance to a serializable
                                 python object by passing "model_serializer" as:
                                    1. a method name of the Model instance passed
                                    2. a standalone function with the model instance as the first argument
                                 Note that when model_serializer is passed, parameter
                                   "attrs" is ignored.
        @param kwargs: the extra keyword paramters can be passed when model_serializer
                        is called.
    '''
    dumper = DataDumper()
    dumper.set_model_attrs(attrs)
    dumper.set_model_serializer(model_serializer, **kwargs)
    return dumper.dump(data, format)
