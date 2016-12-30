from django.conf.urls import url

from .views import PluginViewSet


plugin_library = PluginViewSet.as_view({
    "get": "plugin_library",
    "post": "add_plugin"
})
plugin_view = PluginViewSet.as_view({
    "get": "get_plugin",
    "put": "update_plugin",
    "delete": "delete_plugin"
})
pluginlist = PluginViewSet.as_view({
    "get": "plugin_list"
})
plugin_url_test = PluginViewSet.as_view({
    "get": "test_plugin_url"
})
plugin_renderurl = PluginViewSet.as_view({
    "get": "render_url"
})
plugin_flag = PluginViewSet.as_view({
    "get": "flag"
})


urlpatterns = [
    url(r'^$', plugin_library),
    url(r'^(?P<plugin_id>\d+)(?:/(?P<slug>[\w-]*))?/$', plugin_view),
    url(r'^list/$', pluginlist),
    url(r'^all/$', pluginlist),
    url(r'^tag/$', pluginlist),

    # /species/human/
    # /tag/expression/
    # /species/human/tag/expression/
    # /tag/expression/species/human/
    url(r'^species/(?P<species>[\w-]+)(?:/tag/(?P<tag>[\w-]+))?/$',
        pluginlist),
    url(r'^tag/(?P<tag>[\w-]+)(?:/species/(?P<species>[\w-]+))?/$',
        pluginlist),

    # This gets used to generate the URLs for tags in plugin list views
    url(r'^tag/(?P<tag>[\w\s-]+)/$',
        pluginlist,
        name='plugin_list_for_tag'),

    url(r'test/$', plugin_url_test, name='test_plugin_url'),
    url(r'^(?P<plugin_id>\d+)/renderurl/$', plugin_renderurl),
    url(r'^(?P<plugin_id>\d+)/flag/$', plugin_flag),
]
