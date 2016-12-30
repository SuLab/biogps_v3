import json
from django.core.serializers.json import Serializer as JSONSerializer
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.utils.encoding import smart_unicode

class Serializer(JSONSerializer):
    """
    A fix on JSONSerializer in order to handle customized JSONSerialier properly.
    """
    def handle_field(self, obj, field):
        if field.value_to_string:
            self._current[field.name] = smart_unicode(field.value_to_string(obj), strings_only=True)
        else:
            self._current[field.name] = smart_unicode(getattr(obj, field.name), strings_only=True)

def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of JSON data.
    """
    if isinstance(stream_or_string, basestring):
        import StringIO
        stream = StringIO.StringIO(stream_or_string)
    else:
        stream = stream_or_string
    for obj in PythonDeserializer(json.load(stream)):
        # a work-around for JSONField
        if hasattr(obj.object,'options'):
            obj.object.options = json.dumps(obj.object.options)
        if hasattr(obj.object,'layout_data'):
            obj.object.layout_data = json.dumps(obj.object.layout_data)

        yield obj
