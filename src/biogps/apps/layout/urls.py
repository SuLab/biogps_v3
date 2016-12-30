from django.conf.urls import url

from .views import LayoutViewSet, render_plugin_urls


layout_save = LayoutViewSet.as_view({"post": "add_layout"})
layout_view = LayoutViewSet.as_view({
    "get": "get_layout",
    "put": "update_layout",
    "delete": "delete_layout"
})
layoutlist_all = LayoutViewSet.as_view({
    "get": "get_my_layoutlist"
})
layoutlist_view = LayoutViewSet.as_view({
    "get": "layoutlist"
})

urlpatterns = [
    url(r'^$', layout_save),
    url(r'^(?P<query>\d+)/$', layout_view),
    url(r'^list/$', layoutlist_view),
    url(r'^all/$', layoutlist_all),
    url(r'^(?P<layoutid>\d+)/renderurl/$', render_plugin_urls),
]
