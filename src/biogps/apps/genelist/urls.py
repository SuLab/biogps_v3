from django.conf.urls import url

from .views import GeneListViewSet

genelist_save = GeneListViewSet.as_view({"post": "add_genelist"})
genelist_view = GeneListViewSet.as_view({
    "get": "get_genelist",
    "put": "update_genelist",
    "delete": "delete_genelist"
})
genelist_all = GeneListViewSet.as_view({
    "get": "getmygenelists"
})
genelist_union = GeneListViewSet.as_view({
    "get": "genelist_union"
})
genelist_intersection = GeneListViewSet.as_view({
    "get": "genelist_intersection"
})
genelist_download = GeneListViewSet.as_view({
    "get": "genelist_download"
})


urlpatterns = [
    url(r'^$', genelist_save),
    url(r'^(?P<genelistid>[0-9]+)/$', genelist_view),
    url(r'^all/$', genelist_all),
    url(r'^union/$', genelist_union),
    url(r'^intersection/$', genelist_intersection),
    url(r'^download/$', genelist_download),

]
