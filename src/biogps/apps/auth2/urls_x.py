'''
The URLs listed here are served under /authx/ as ajax services via http.
'''
from django.conf.urls import url

from biogps.apps.auth2 import views


urlpatterns = [
    url(r'^logout/$',
        views.logout,
        name='auth_logout_x'),
    url(r'^getuserdata$',
        views.getuserdata,
        name='auth_getuserdata'),
    url(r'^saveprofile$',
        views.save_uiprofile,
        name='auth_saveprofile'),
]
