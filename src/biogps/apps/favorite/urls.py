from django.conf.urls import url

from biogps.apps.favorite import views


urlpatterns = [
    url(r'^$', views.FavoriteView, name='FavoriteView'),
    url(r'^(?P<modelType>.+)/(?P<objectID>\d+)/$',
        views.FavoriteSubmitView,
        name='FavoriteSubmitView'),
    url(r'^(?P<modelType>.+)/$',
        views.FavoriteObjectView,
        name='FavoriteObjectView'),
]
