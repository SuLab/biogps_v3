import types
from django.template.base import Library
from django.template.defaultfilters import stringfilter
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

from biogps.utils.const import species_d

register = Library()


@register.filter
@stringfilter
def html2text(value):
    import html2text
    return html2text.html2text(value)


#######################################################
#Taken from http://djangosnippets.org/snippets/1259/  #
#######################################################
@register.filter
def truncatesmart(value, limit=80):
    """
    Truncates a string after a given number of chars keeping whole words.

    Usage:
        {{ string|truncatesmart }}
        {{ string|truncatesmart:50 }}
    """

    try:
        limit = int(limit)
    # invalid literal for int()
    except ValueError:
        # Fail silently.
        return value

    # Make sure it's unicode
    value = unicode(value)

    # Return the string itself if length is smaller or equal to the limit
    if len(value) <= limit:
        return value

    # Cut the string
    value = value[:limit]

    # Break into words and remove the last
    words = value.split(' ')[:-1]

    # Join the words and return
    return ' '.join(words) + '...'


def smartjoin(value, arg, autoescape=None):
    """
    Only join a list/tuple not a string.
    Modified from Django's default join filter
    """
    if type(value) in (types.ListType, types.TupleType):
        value = map(force_unicode, value)
        if autoescape:
            from django.utils.html import conditional_escape
            value = [conditional_escape(v) for v in value]
        try:
            data = arg.join(value)
        except AttributeError:   # fail silently but nicely
            return value
        return mark_safe(data)
    else:
        return value
smartjoin.is_safe = True
smartjoin.needs_autoescape = True
register.filter(smartjoin)


@register.filter
def alwayslist(value):
    if value is None:
        return []
    elif type(value) in (types.ListType, types.TupleType):
        return value
    else:
        return [value]


@register.filter
def as_species(taxid):
    '''Convert the given taxid into a friendly species name.
       if can not convert, return the taxid itself.
    '''
    species = species_d.get(taxid, taxid)
    return species
