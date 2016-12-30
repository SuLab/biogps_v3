from django.contrib.sitemaps import Sitemap
from django.utils import timezone

from biogps.www.models import BiogpsRootnode


class GenereportSitemap(Sitemap):
    changefreq = "monthly"  #"never"
    priority = 0.9
    lastmod = timezone.datetime(2010, 04, 14).date()
    limit = 5000   #default is 50000 (max allowed)

    def items(self):
        return BiogpsRootnode.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()

    def priority(self, obj):
        #lower priority for ensembl only gene since most of
        #them don't have much content
        return 0.9 if obj.data_source == 'ncbi' else 0.6

#     def lastmod(self, obj):
#         return obj.pub_date

class FlatPageSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5
    lastmod = timezone.datetime(2009, 1, 1).date()

    def items(self):
        return ['about', 'terms', 'help', 'faq', 'downloads','api', 'iphone']

    def location(self, obj):
        return '/' + obj + '/'
