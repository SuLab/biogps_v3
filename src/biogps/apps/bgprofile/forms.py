from django import forms
from .models import BiogpsProfile
from biogps.utils.fields.jsonfield import JSONFormField
#from fields import *

VALID_PRIVACY_CHOICES = ('public', 'friends', 'private')

class BiogpsProfileForm(forms.ModelForm):
    """
    Form handling code for BioGPS Profile objects.
    The majority of the logic is handled in the custom fields and widgets.
    """

    info = JSONFormField()
    links = JSONFormField()
    privacy = JSONFormField()

    class Meta:
        model = BiogpsProfile
        exclude = ('user',)

    def clean_privacy(self):
        """
        Validate that the privacy object is correctly formatted.

        """
        valid = True
        priv = self.cleaned_data['privacy']
        for sett in ('profile_visible', 'name_visible', 'email_visible'):
            if not priv[sett] in VALID_PRIVACY_CHOICES:
                valid = False
                raise forms.ValidationError(u'Invalid privacy setting.')

        if valid:
            return self.cleaned_data['privacy']
        else:
            raise forms.ValidationError(u'Privacy controls corrupted. Please refresh the page and try again.')
