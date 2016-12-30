from django.conf.urls import patterns, url


urlpatterns = patterns(
    'biogps.apps.gene.views',
    url('^$', 'query', name='boe.query'),

    # url(r'^getgeneidentifiers/$',
    #      'getgeneidentifiers',
    #     name='boe.getgeneidentifiers'),

    url('^(?P<geneid>[\w\-\.]+)/identifiers/$',
        'getgeneidentifiers',
        name='gene.getgeneidentifiers')
)
