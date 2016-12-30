'''Models definition for BioGPS GeneList.'''
from django.db import models
from django_extensions.db.fields import AutoSlugField
from tagging.registry import register

from biogps.utils.models import BioGPSModel
from biogps.utils.fields.jsonfield import JSONField
from biogps.apps.auth2.models import UserProfile
from biogps.apps.search.build_index import set_on_the_fly_indexing


class BiogpsGeneList(BioGPSModel):
    name = models.CharField(max_length=100)
    data = JSONField(blank=True, editable=False)
    size = models.PositiveIntegerField()   # the number of genes stored in data
    ownerprofile = models.ForeignKey(UserProfile, to_field='sid',
                                     db_column='authorid')
    author = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    options = JSONField(blank=True, editable=False)
    lastmodified = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)
    slug = AutoSlugField(populate_from='name')

    #required setting for ModelWithPermission and PermissionManager working
    object_type = 'G'
    #short_name will be used as the index_type for ES indexing
    short_name = 'genelist'

    def __unicode__(self):
        return u'"%s" by "%s"' % (self.name, self.author)

    class Meta:
        # permissions = (
        #     ("can_share_genelist", "Can share genelists with others."),
        # )
        ordering = ("name",)
        get_latest_by = 'lastmodified'

    def object_cvt(self, mode='ajax'):
        '''A helper function to convert a BiogpsGeneList object to a simplified
            python dictionary, with all values in python's primary types only.
            Such a dictionary can be passed directly to fulltext indexer or
            serializer for ajax return.

          @param mode: can be one of ['ajax', 'es'], used to return slightly
                         different dictionary for each purpose.
          @return: an python dictionary
        '''
        return self._object_cvt(extra_attrs={'AS_IS': ['name', 'description']},
                                mode=mode)

register(BiogpsGeneList)

set_on_the_fly_indexing(BiogpsGeneList)
