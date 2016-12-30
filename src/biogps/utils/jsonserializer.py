import json
from django.core.serializers.json import Serializer as JSONSerializer
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import smart_text
from . import cvtPermission


class Serializer(JSONSerializer):
    def start_serialization(self):
        self._current = None
        self.objects = []

    def handle_field(self, obj, field):
        if field.value_to_string:
            self._current[field.name] = smart_text(field.value_to_string(obj), strings_only=True)
        else:
            self._current[field.name] = smart_text(getattr(obj, field.name), strings_only=True)

    def end_object(self, obj):
        super(JSONSerializer, self).end_object(obj)
        fields = self.objects[-1]["fields"]

        if 'authorid' in fields:
            del fields['authorid']

        if 'ownerprofile' in fields:
            del fields['ownerprofile']

        if getattr(obj, 'permission', None):
            fields.update({'permission': cvtPermission(obj.permission)})

#        if hasattr(obj, 'is_shared'):
#             fields.update({'is_shared': obj.is_shared})

        if getattr(obj, 'tags', None):
            fields.update({'tags': ' '.join([t.name for t in obj.tags])})

#        if hasattr(obj, 'usage_percent'):
#            fields.update({'usage_percent': obj.usage_percent})

        if not hasattr(self, 'extra_itemfields'):
            self.extra_itemfields = self.options.get("extra_itemfields", [])
        for field in self.extra_itemfields:
            if hasattr(obj, field):
                fields.update({field: getattr(obj, field)})

    def end_serialization(self):
        if not hasattr(self, 'extra_fields'):
            self.extra_fields = self.options.get("extra_fields", {})
        output_obj = self.extra_fields
        output_obj['items'] = self.objects
        self.objects = output_obj

        #exclude items passed in options which are not accepted by simplejsno.dump called next.
        self.options.pop('stream', None)
        self.options.pop('fields', None)
        self.options.pop('extra_fields', None)
        self.options.pop('extra_itemfields', None)

        json.dump(self.objects, self.stream, cls=DjangoJSONEncoder, **self.options)
