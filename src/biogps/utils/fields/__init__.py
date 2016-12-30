#The hacking below should be deprecated now as django_extensions added support for South

#from django_extensions.db.fields import AutoSlugField as _AutoSlugField
#
#
## Sub-classed AutoSlugField to add South's introspection rule
#class AutoSlugField(_AutoSlugField):
#    pass
#
#from south.modelsinspector import add_introspection_rules
#add_introspection_rules([
#    (
#        [AutoSlugField], # Class(es) these apply to
#        [],         # Positional arguments (not used)
#        {           # Keyword argument
#            "populate_from": ["_populate_from", {}],
#        },
#    ),
#], ["^biogps\.utils\.fields\.AutoSlugField"])
