# THIS FILE IS NOT IN USE
# It was a first-pass implementation of custom form widgets for Profile Privacy control.
# It has been superceded by the handling in forms.py, but remains here for future reference.

from django.forms import widgets

__all__ = ('ProfilePrivacyInput',)

class ProfilePrivacyInput(widgets.MultiWidget):
    """
    Defines the HTML structure of the form control elements used for the
    profile_privacy attribute of a BiogpsProfile object instance.
    """
    
    def __init__(self, attrs=None, choices=()):
        widget_list = (
            widgets.Select(attrs=attrs, choices=choices), # profile_visible
            widgets.Select(attrs=attrs, choices=choices), # name_visible
            widgets.Select(attrs=attrs, choices=choices) # email_visible
        )
        super(ProfilePrivacyInput, self).__init__(widget_list, attrs)
    
    def decompress(self, value):
        """
        Accepts a single value which it then extracts enough values to
        populate the various widgets.
        """
        if value:
            print value
            return [
                value['profile_visible'],
                value['name_visible'],
                value['email_visible']
            ]
        return [None, None, None]
    
    def render(self, name, value, attrs=None):
        """
        Converts the widget to an HTML representation of itself.
        """
        output = super(ProfilePrivacyInput, self).render(name, value, attrs)
        return output
    
