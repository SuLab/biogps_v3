'''Models definition for BioGPS plugins.'''
from django.db import models
from tagging.registry import register

from biogps.utils.models import BioGPSModel
from biogps.utils.fields.jsonfield import JSONField
from biogps.apps.auth2.models import UserProfile
from biogps.apps.plugin.models import BiogpsPlugin
from biogps.apps.search.build_index import set_on_the_fly_indexing


class BiogpsGenereportLayout(BioGPSModel):
    layout_name = models.CharField(max_length=100)
    plugins = models.ManyToManyField(BiogpsPlugin, through="BiogpsLayoutPlugin")
    ownerprofile = models.ForeignKey(UserProfile, to_field='sid', db_column='authorid')
    author = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    lastmodified = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    #if true, return plugin details in layout_data
    loadplugin = False

    #required setting for ModelWithPermission and PermissionManager working
    object_type = 'L'
    #short_name will be used as the index_type for ES indexing
    short_name = 'layout'

    def __unicode__(self):
        return u'"%s" by "%s"' % (self.layout_name, self.author)

    class Meta:
        # set app_lable to www for back-compatibility
        # so that existing record in content-type table will match this model
#        app_label = 'www'
        #To set the actual table name to use, which matches existing DB
#        db_table = 'www_biogpsgenereportlayout'
        permissions = (
            ("can_share_layout", "Can share layouts with others."),
        )
        ordering = ("layout_name",)
        get_latest_by = 'lastmodified'

    def object_cvt(self, mode='ajax'):
        '''A helper function to convert a BiogpsGenereportLayout object to a
            simplified python dictionary, with all values in python's primary
            types only. Such a dictionary can be passed directly to fulltext
            indexer or serializer for ajax return.

          @param mode: can be one of ['ajax', 'es'], used to return slightly
                         different dictionary for each purpose.
          @return: an python dictionary
        '''
        return self._object_cvt(extra_attrs={'name': 'layout_name',
                                             'description': 'description'},
                                mode=mode)

    #==========================================================================
    # methods specific for this model
    #==========================================================================
    def get_layout_data(self, loadplugin=False):
        """return layout_data as a list of dictionaries.
            e.g., [{'width': 838, 'id': 10, 'top': 28, 'left': 10, 'useroptions': None, 'height': 435}]
        """
        if loadplugin or self.loadplugin:
            return [dict(id=p.plugin.id,
                         height=p.height,
                         width=p.width,
                         left=p.left,
                         top=p.top,
                         useroptions=p.useroptions,

                         #more details about the plugin
                         title=p.plugin.title,
                         url=p.plugin.url,
                         author=p.plugin.owner.get_valid_name(),
                         author_url=p.plugin.owner.get_absolute_url(),
                         type=p.plugin.type,
                         description=p.plugin.description,
                         lastmodified=p.plugin.lastmodified,
                         species=p.plugin.species,
                         options=p.plugin.options
                         )
                    #for p in self.biogpslayoutplugin_set.order_by('top', 'left')]
                    #for p in self.biogpslayoutplugin_set.select_related().order_by('top', 'left')]
                    for p in self.biogpslayoutplugin_set.order_by('top', 'left').select_related(
                        "plugin__id",
                        "plugin__url",
                        "plugin__type",
                        "plugin__description",
                        "plugin__lastmodified",
                        "plugin__species",
                        "plugin__options",

                        "plugin__ownerprofile__user",
                        "plugin__ownerprofile",
                       )]


        else:
            return [dict(id=p.plugin.id,
                         height=p.height,
                         width=p.width,
                         left=p.left,
                         top=p.top,
                         useroptions=p.useroptions)
                    #for p in self.biogpslayoutplugin_set.select_related().order_by('top', 'left')]
                    for p in self.biogpslayoutplugin_set.order_by('top', 'left').select_related(
                        "plugin__id",
                        )]

    def save_layout_data(self, layout_data):
        """save layout_data (a list of dictionaries).
            e.g. layout_data = [{'width': 838, 'id': 10, 'top': 28, 'left': 10, 'useroptions': None, 'height': 435}]
        """
        if isinstance(layout_data, (list, tuple)):
            self.plugins.clear()

            for d in layout_data:
                p = BiogpsPlugin.objects.get(id=d['id'])
                _d = BiogpsLayoutPlugin.objects.create(layout=self, plugin=p)
                for attr in ['height', 'width', 'left', 'top']:
                    if d.get(attr, None) is not None:
                        setattr(_d, attr, max(0, int(d[attr])))
                if d.get('useroptions', None):
                    _d.useroptions = d['useroptions']
                _d.save()

    def clean_layout_data(self):
        '''remove all existing layout_data.'''
        self.plugins.clear()

    layout_data = property(get_layout_data, save_layout_data, clean_layout_data)


register(BiogpsGenereportLayout)


set_on_the_fly_indexing(BiogpsGenereportLayout)


class BiogpsLayoutPlugin(models.Model):
    """store the plugin data in a layout."""
    layout = models.ForeignKey(BiogpsGenereportLayout)
    plugin = models.ForeignKey(BiogpsPlugin)
    height = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    left = models.PositiveIntegerField(null=True, blank=True)
    top = models.PositiveIntegerField(null=True, blank=True)
    #extra options user specified for the container layout.
    useroptions = JSONField(blank=True, editable=False)

#    class Meta:
        # set app_lable to www for back-compatibility
        # so that existing record in content-type table will match this model
#        app_label = 'www'
        #To set the actual table name to use, which matches existing DB
#        db_table = 'www_biogpslayoutplugin'

    def __unicode__(self):
        return u'plugin "%s" in layout "%s"' % (self.plugin.title, self.layout.layout_name)
