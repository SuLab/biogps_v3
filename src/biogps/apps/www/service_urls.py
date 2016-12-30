"""
This is deprecated!
"""
from django.conf.urls import patterns, url


urlpatterns = patterns('biogps.www.views',
                       url(r'^search/$',
                           'query_gene',
                           name='search'),

                       url(r'^getgeneidentifiers/$',
                           'getgeneidentifiers',
                           name='getgeneidentifiers'),

                       url(r'^getgenereport/$',
                           'getgenereport',
                           name='getgenereport'),

                       url(r'^getgenelist/$',
                           'getgenelist',
                           name='getgenelist'),

                       url(r'^datasetlist/(?P<geneid>.+)/$',
                           'datasetlist',
                           name='datasetlist'),

                       url(r'^datasetvalues/$',
                           'datasetvalues',
                           name='datasetvalues'),

                       url(r'^datasetchart/$',
                           'datasetchart',
                           name='datasetchart'),

                       url(r'^datasetlist2/(?P<geneid>.+)/$',
                           'datasetlist2',
                           name='datasetlist2'),

                       url(r'^datasetchart2/(?P<datasetid>\d+)/(?P<reporter>.+)/$',
                           'datasetchart2',
                           name='datasetchart2'),

                       url(r'^datasetvalues2/(?P<datasetid>\d+)/$',
                           'datasetvalues2',
                           name='datasetvalues2'),


                       url(r'^getlastsearch/$',
                           'getlastsearch',
                           name='getlastsearch'),

                       url(r'^userroles/$',
                           'userroles',
                           name='userroles'),

                      )

