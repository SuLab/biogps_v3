import types
from itertools import chain
from django.db import models
from django.forms.widgets import CheckboxInput, CheckboxSelectMultiple
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from biogps.utils.models import Species

class SpeciesSelectMultiple(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<div id="%s">' % attrs['id']]
        # Normalize to strings
        str_values = set(value)
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'%s <label%s>%s</label>' % (rendered_cb, label_for, option_label))
        output.append(u'</div>')
        return mark_safe(u'\n'.join(output))


class SpeciesField(models.CharField):
    description = "An array of species strings"
    widget = SpeciesSelectMultiple

    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if not value:
            return Species.available_species
        if type(value) is types.ListType:
            return value
        return value.split(',')

    def get_db_prep_save(self, value, connection):
        '''Returns species value prepped for saving to database.'''
        _value = '' if self.uses_all_species(value) else ','.join(value)
        return _value

    def uses_all_species(self, value):
        '''Confirm whether this value indicates all species or not.
           Returns True when the value is either None or matches the full list
           of available species. Returns False when one or more of the
           available species are not in the value's list.
        '''
        if value:
            for s in Species.available_species:
                if s not in value:
                    return False
        return True
