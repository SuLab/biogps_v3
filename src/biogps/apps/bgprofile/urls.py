'''
The URLs listed here are served under /profile/
'''
from django.conf.urls import url

from biogps.apps.bgprofile import views


urlpatterns = [
    url(r'^$',
        views.index,
        name='apps.bgprofile.mine'),

    url(r'^edit/$',
        views.edit,
        name='apps.bgprofile.edit'),

    url(r'^(?P<userid>[\w-]+)/$',
        views.view),

    url(r'^(?P<userid>[\w-]+)/(?P<junk>.+)$',
        views.view,
        name='apps.bgprofile.view'),
]
