from django.conf.urls import url

from biogps.search import views


urlpatterns = [
    url(r'^$', views.search, name='search'),
    url(r'^status/$', views.status, name='status'),
    url(r'^mapping/$', views.get_mapping),
    url(r'^interval/$', views.interval, name='interval_search'),
    url(r'^(?P<_type>.+)/$', views.search, name='search_in'),
]
