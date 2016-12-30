'''
Our own context processors
'''

from django.conf import settings

def base_processor(request):
    '''Return commonly used variables in base.html template.'''
    return {'django_compress': getattr(settings, 'COMPRESS', not settings.DEBUG),
            'max_query_length': settings.ES_MAX_QUERY_LENGTH,
            }