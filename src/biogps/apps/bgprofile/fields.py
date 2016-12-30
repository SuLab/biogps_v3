# THIS FILE IS NOT IN USE
# It was a first-pass implementation of custom form widgets for Profile Privacy control.
# It has been superceded by the handling in forms.py, but remains here for future reference.

from django.forms import fields, widgets
from widgets import *

__all__ = ('ProfilePrivacyField',)

PRIVACY_CHOICES = (
    ('true', 'Public'),
    ('Friends', 'Friends-Only'),
    ('false', 'Private')
)


def clean_value(value):        
    if value == True or value == 'true':
        return True
    elif value == 'Friends':
        return 'Friends'
    else:
        return False


class ProfilePrivacyField(fields.MultiValueField):
    """
    Multiple-object field to handle the full contents of the profile_privacy
    attribute of a BiogpsProfile object.
    """
    
    widget = ProfilePrivacyInput(choices = PRIVACY_CHOICES)
    
    def __init__(self, *args, **kwargs):
        """
        Have to pass a list of field types to the constructor, else we
        won't get any data to our compress method.
        """
        all_fields = (
            fields.ChoiceField(choices = PRIVACY_CHOICES),
            fields.ChoiceField(choices = PRIVACY_CHOICES),
            fields.ChoiceField(choices = PRIVACY_CHOICES)
            )
        super(ProfilePrivacyField, self).__init__(all_fields, *args, **kwargs)
    
    def clean(self, value):
        return super(ProfilePrivacyField, self).clean(value)
    
    def compress(self, data_list):
        """
        Takes the values from the MultiWidget and passes them as a
        list to this function. This function needs to compress the
        list into a single object to save.
        """
        if data_list:
            if isinstance(data_list, (list, tuple)):
                compressed = {
                    "profile_visible": clean_value(data_list[0]),
                    "name_visible": clean_value(data_list[1]),
                    "email_visible": clean_value(data_list[2])
                }
                return compressed
            else:
                return data_list
        return None
    
