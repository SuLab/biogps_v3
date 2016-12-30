import types
from django import forms

from biogps.utils.models import Species
from models import BiogpsPlugin
from fields import SpeciesSelectMultiple

class BiogpsPluginForm(forms.ModelForm):
    species = forms.MultipleChoiceField(
                    choices=Species.form_choices(),
                    widget=SpeciesSelectMultiple(),
                    initial=Species.available_species,
                    required=False
              )

    class Meta:
        model = BiogpsPlugin
        fields = ('title', 'url', 'description', 'short_description', 'species')

    def __init__(self, *args, **kwargs):
        # Ensure we get the full species list.
        # Effectively all we're doing is copying 'species[]' to 'species' to
        # deal with the difference between Django and jQuery's representations
        # of arrays passed through URLs.
        if args:
            _dict = args[0].copy()      # Create a mutable copy of the QueryDict
            _dict.setlist('species', _dict.getlist('species[]'))
            _args = (_dict,)            # Create a new args tuple to pass on as normal
        else:
            _args = args
        super(BiogpsPluginForm, self).__init__(*_args, **kwargs)
