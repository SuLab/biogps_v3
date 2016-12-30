#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
TODO:
       score-tuning:   1. Symbol
                    2. any ID
                    3. name
                    4. summary
                    5. other text (uniprot name, interpro desc, go term)

       case to consider:
                q=hypoxia inducible factor
                 if matching from the beginning, rank higher?
           appear first     # name: "hypoxia-inducible factor 1, alpha subunit (basic helix-loop-helix transcription factor)"
           appear latter    # name: "similar to egl nine homolog 1 (hypoxia-inducible factor prolyl hydroxylase 2) (hif-prolyl hydroxylase 2) (hif-ph2) (hph-2) (sm-20)"



    auto-correction:  1. multiple terms use default AND first, if no hit, do the OR automatically (with a note on UI)
'''
from functools import partial
from django.conf import settings
from django.db.models.signals import post_save, post_delete

#from pyes.exceptions import (NotFoundException, IndexMissingException,
#                            ElasticSearchException, TypeMissingException)

from biogps.utils import ask
from biogps.utils.models import queryset_iterator

#from .es_lib import get_es_conn

import logging
log = logging.getLogger('pyes')
if settings.DEBUG:
    log.setLevel(logging.DEBUG)
    if len(log.handlers) == 0:
        log_handler = logging.StreamHandler()
        log.addHandler(log_handler)


class BiogpsESIndexerBase(object):
    ES_HOST = settings.ES_HOST
    ES_INDEX_NAME = settings.ES_INDEXES['default']
    step = 100

    def __init__(self):
        self.conn = get_es_conn(self.ES_HOST, default_idx=[self.ES_INDEX_NAME])

    def check(self):
        '''print out ES server info for verification.'''
        print("Servers:", self.conn.servers)
        print("Default indices:", self.conn.default_indices)
        print("ES_INDEX_TYPE:", self.ES_INDEX_TYPE)

    def create_index(self):
        try:
            print(self.conn.open_index(self.ES_INDEX_NAME))
        #except NotFoundException:
        except IndexMissingException:
            print(self.conn.create_index(self.ES_INDEX_NAME))

    def delete_index_type(self, index_type):
        '''Delete all indexes for a given index_type.'''
        index_name = self.ES_INDEX_NAME
        #Check if index_type exists
        try:
            mapping = self.conn.get_mapping(index_type, index_name)
        except TypeMissingException:
            print('Error: index type "%s" does not exist in index "%s".' % (index_type, index_name))
            return
        path = '/%s/%s' % (index_name, index_type)
        if ask('Confirm to delete all data under "%s":' % path) == 'Y':
            return self.conn.delete_mapping(index_name, index_type)

    def verify_mapping(self, update_mapping=False):
        '''Verify if index and mapping exist, update mapping if mapping does not exist,
           or "update_mapping=True" explicitly
        '''
        conn = self.conn
        index_name = self.ES_INDEX_NAME
        index_type = self.ES_INDEX_TYPE

        #Test if index exists
        try:
            print("Opening index...", conn.open_index(index_name))
        except NotFoundException:
            print('Error: index "%s" does not exist. Create it first.' % index_name)
            return -1

        try:
            cur_mapping = conn.get_mapping(index_type, index_name)
            empty_mapping = False
        except ElasticSearchException:
            #if no existing mapping available for index_type
            #force update_mapping to True
            empty_mapping = True
            update_mapping = True

#        empty_mapping = not cur_mapping[index_name].get(index_type, {})
#        if empty_mapping:
#            #if no existing mapping available for index_type
#            #force update_mapping to True
#            update_mapping = True

        if update_mapping:
            print("Updating mapping...",)
            if not empty_mapping:
                print("\n\tRemoving existing mapping...", end='')
                print(conn.delete_mapping(index_name, index_type))
            _mapping = self.get_field_mapping()
            print(conn.put_mapping(index_type,
                                   _mapping,
                                   [index_name]))

    def index(self, doc, index_type, id=None):
        '''add a doc to the index. If id is not None, the existing doc will be
           updated.
        '''
        return self.conn.index(doc, self.ES_INDEX_NAME, index_type, id=id)

    def delete_index(self, index_type, id):
        '''delete a doc from the index based on passed id.'''
        return self.conn.delete(self.ES_INDEX_NAME, index_type, id)

    def optimize(self):
        return self.conn.optimize(self.ES_INDEX_NAME, wait_for_merge=True)


class BiogpsModelESIndexer(BiogpsESIndexerBase):
    '''The base class for indexing objects from BioGPSModel derived models,
       e.g., BioGPSPlugin, BiogpsGenereportLayout, etc.
    '''
    _model = None           # need to specify in each subclass
    ES_INDEX_TYPE = None    # need to specify in each subclass
    step = 100              # how many objects to retrieve in one queryset query

    def _get_field_mapping(self, extra_attrs={}):
        #field mapping templates
        id_type = {'store': "yes",
                   'index': 'not_analyzed',
                   'type': 'string',
                   'term_vector': 'with_positions_offsets'}
        text_type = {'store': "no",
              'index': 'analyzed',
              'type': 'string',
              'term_vector': 'with_positions_offsets'}
        date_type = {'store': "no",
              'index': 'not_analyzed',
              'type': 'date',
              'format': 'YYYY-MM-dd HH:mm:ss'}
        integer_type = {'type': 'integer'}
        float_type = {'type': 'float'}
        object_type = {'type': 'object'}
        boolean_type = {'type': 'boolean'}

        store_only = {'store': "yes",
                      'index': 'no',
                      'type': 'string'}
        disabled_object = {'type': 'object',
                           'enabled': False}
        disabled_string = {'type': 'string',
                           'index': 'no'}
        disabled_double = {'type': 'double',
                           'index': 'no'}
        disabled_integer = {'type': 'integer',
                             'index': 'no'}

        td = {'id_type': id_type,
              'text_type': text_type,
              'date_type': date_type,
              'integer_type': integer_type,
              'float_type': float_type,
              'boolean_type': boolean_type,
              'object_type': object_type,

              'store_only': store_only,
              'disabled_object':  disabled_object,
              'disabled_string':  disabled_string,
              'disabled_double':  disabled_double,
              'disabled_integer': disabled_integer}

        properties = {'in': id_type,
                      'id': id_type,
                      'created': date_type,
                      'lastmodified': date_type,
                      'role_permission': id_type,
                      'tags': id_type}

        for t_id in td.keys():
            for attr in extra_attrs.pop(t_id, []):
                properties[attr] = td[t_id]
        properties.update(extra_attrs)

        for f in properties:
            properties[f] = properties[f].copy()

        #some special settings
        #for tag field
        properties['tags']['index_name'] = 'tag'

        #for name field
        properties['name'] = {
             "type" : "multi_field",
             "store": "yes",
             "fields" : {
                "name" : {
                          'index': 'analyzed',
                          'type': 'string',
                          'boost': 2.0,
                          'term_vector': 'with_positions_offsets'
                         },
                "for_sort" : {
                              "type" : "string",
                              "index" : "not_analyzed"
                             }
              }
        }
        #for owner field
        properties['owner'] = {
            "store": "yes",
            "type": "object",
            "path": 'just_name',  #! This is important to make query "username:cwudemo" work, instead of using "owner.username:cwudemo"
            "properties" : {
                "username" : {
                              "type" : "string",
                              "index_name": "username",
                              "index": "not_analyzed",
                             },
                "name" : {
                           "type" : "string",
                          "index_name": "owner",
                          "index": "analyzed",
                         },
                "url" : {
                          "type" : "string",
                          "index": "no",
                         }
            }
        }

        #for rating_data field
        properties['rating_data'] = {
            "store": "yes",
            "type": "object",
            "properties": {
                "avg_stars": {"type": "short"},
                "total": {"type": "short"},
                "avg": {"type": "short"},
            }
        }

        mapping = {'properties': properties}
        # enable _source compression
        mapping["_source"] = {"enabled" : True,
                              "compress": True,
                              "compression_threshold": "1kb"}

#        #store "_all" for highlighting.
#        mapping["_all"] = {"store": "yes",
#                           "type": "string",
#                           "term_vector": "with_positions_offsets"}
        return mapping

    def get_field_mapping(self):
        raise NotImplementedError

    def build_index(self, update_mapping=False, bulk=True, verbose=False):
        conn = self.conn
        index_name = self.ES_INDEX_NAME
        index_type = self.ES_INDEX_TYPE

        self.verify_mapping(update_mapping=update_mapping)

        print("Building index...")
        cnt = 0
        for p in queryset_iterator(self._model, batch_size=self.step):
            doc = p.object_cvt(mode='es')
            conn.index(doc, index_name, index_type, doc['id'], bulk=bulk)
            cnt += 1
            if verbose:
                print(cnt, ':', doc['id'])
        print(conn.flush())
        print(conn.refresh())
        print('Done! - {} docs indexed.'.format(cnt))

    def index_object(self, object_id):
        obj = self._model.objects.get(id=object_id)
        doc = obj.object_cvt(mode='es')
        print(self.index(doc, self.ES_INDEX_TYPE, id=doc['id']))


class BiogpsPluginESIndexer(BiogpsModelESIndexer):
    '''A class for indexing all BiogpsPlugin objects.'''
    def __init__(self):
        from biogps.plugin.models import BiogpsPlugin
        self._model = BiogpsPlugin
        self.ES_INDEX_TYPE = self._model.short_name
        super(BiogpsModelESIndexer, self).__init__()

    def get_field_mapping(self):
        m_usage_data = {
            "store": "yes",
            "type": "object",
            "properties": {
                "users": {"type": "short"},
                "layouts": {"type": "short"},
            }
        }
        m = self._get_field_mapping(extra_attrs={'id_type': ['type', 'species'],
                                                 'text_type': ['name', 'description', 'short_description', 'url'],
                                                 "float_type": ['popularity'],
                                                 'disabled_object': ['options'],
                                                 'disabled_string': ['shortUrl', 'permission_style'],
                                                 'usage_data': m_usage_data
                                                 })
        return m


class BiogpsLayoutESIndexer(BiogpsModelESIndexer):
    '''A class for indexing all BiogpsGenereportLayout objects.'''
    def __init__(self):
        from biogps.layout.models import BiogpsGenereportLayout
        self._model = BiogpsGenereportLayout
        self.ES_INDEX_TYPE = self._model.short_name
        super(BiogpsModelESIndexer, self).__init__()

    def get_field_mapping(self):
        m = self._get_field_mapping(extra_attrs={'text_type': ['name', 'description'],
                                                 'disabled_string': ['permission_style'],
                                                 })
        #some special settings
#        m['name']['boost'] = 2.0
        return m


class BiogpsGenelistESIndexer(BiogpsModelESIndexer):
    '''A class for indexing all BiogpsGeneList objects.'''
    def __init__(self):
        from biogps.genelist.models import BiogpsGeneList
        self._model = BiogpsGeneList
        self.ES_INDEX_TYPE = self._model.short_name
        super(BiogpsModelESIndexer, self).__init__()

    def get_field_mapping(self):
        m = self._get_field_mapping(extra_attrs={'text_type': ['name', 'description'],
                                                 'disabled_string': ['permission_style'],
                                                 })
        #some special settings
#        m['name']['boost'] = 2.0
        return m


def _rebuild_x(delete_old=False, update_mapping=False, indexer=None):
    '''A convenient function for re-building indexes.
    '''
    es_indexer = indexer()
    if delete_old:
        es_indexer.delete_index_type(es_indexer.ES_INDEX_TYPE)
        update_mapping = True   # if delete_old is True, update_mapping should be True anyway
    es_indexer.build_index(update_mapping=update_mapping, bulk=True)

rebuild_plugin = partial(_rebuild_x, indexer=BiogpsPluginESIndexer)
rebuild_plugin.__doc__ = 'A convenient function for re-building all plugins.'
rebuild_layout = partial(_rebuild_x, indexer=BiogpsLayoutESIndexer)
rebuild_layout.__doc__ = 'A convenient function for re-building all layouts.'
rebuild_genelist = partial(_rebuild_x, indexer=BiogpsGenelistESIndexer)
rebuild_genelist.__doc__ = 'A convenient function for re-building all genelists.'


def rebuild_all(delete_old=False):
    '''A convenient function for re-building all biogpsmodel objects,
       not including genes and datasets.
    '''
    rebuild_plugin(delete_old)
    rebuild_layout(delete_old)
    rebuild_genelist(delete_old)


def on_the_fly_es_update_handler(sender, **kwargs):
    '''A post_save signal handler to update ES indexes whenever a BiogpsModel object
       is created/updated.

       To connect to a signal:
           post_save.connect(on_the_fly_es_update_handler, sender=BioGPSModel,
                             dispatch_uid="some_unique_id")

    '''
    if not getattr(settings, "SUSPEND_ES_UPDATE", None):
        object = kwargs['instance']
        es_indexer = BiogpsModelESIndexer()
        doc = object.object_cvt(mode='es')
        res = es_indexer.index(doc, object.short_name, object.id)
        return True


def on_the_fly_es_delete_handler(sender, **kwargs):
    '''A post_delete signal handler to delete ES indexes whenever a BiogpsModel object
       is deleted.

       To connect to a signal:
           post_delete.connect(on_the_fly_es_delete_handler, sender=BioGPSModel,
                               dispatch_uid="some_unique_id")

    '''
    if not getattr(settings, "SUSPEND_ES_UPDATE", None):
        object = kwargs['instance']
        es_indexer = BiogpsModelESIndexer()
        res = es_indexer.delete_index(object.short_name, object.id)
        return True


def set_on_the_fly_indexing(biogpsmodel):
    '''set input biogpsmodel for on the fly indexing:
          * add to index when a new object is created
          * update index when an object is updated
          * delete from index when an object is deleted
    '''
    post_save.connect(on_the_fly_es_update_handler, sender=biogpsmodel,
                      dispatch_uid=biogpsmodel.__name__ + 'update_indexer')
    post_delete.connect(on_the_fly_es_delete_handler, sender=biogpsmodel,
                      dispatch_uid=biogpsmodel.__name__ + 'delete_indexer')
