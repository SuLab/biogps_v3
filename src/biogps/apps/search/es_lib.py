'''
The API library for performing queries on ElasticSearch.
'''
import sys
import json
from django.conf import settings
# from pyes import (ES, TermQuery, TermsQuery, StringQuery,
#                   FilteredQuery, BoolQuery, RangeQuery, MatchAllQuery)
# from pyes import ESRange
# from pyes.exceptions import (ElasticSearchException,
#                              SearchPhaseExecutionException,
#                              InvalidQuery)
# from pyes.es import ESJsonEncoder

from elasticsearch import ElasticSearch, ElasticsearchException
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import Q, Bool, MatchAll, A

from biogps.utils.models import get_role_shortnames
from biogps.search.results import BiogpsSearchResult

# import logging
# log = logging.getLogger('pyes')
# if settings.DEBUG:
#     log.setLevel(logging.DEBUG)
#     if len(log.handlers) == 0:
#         log_handler = logging.StreamHandler()
#         log.addHandler(log_handler)

def get_es_conn(ES_HOST=None, default_idx=settings.ES_INDEXES['default']):
    ES_HOST = ES_HOST or settings.ES_HOST
    # conn = ES(ES_HOST, default_indices=default_idx,
    #           max_retries = 10, timeout=300)
    conn = ElasticSearch(ES_HOST, timeout=300)
    return conn


_conn = get_es_conn()


def safe_genome_pos(s):
    '''
       >>> safe_genome_pos(1000) = 1000
       >>> safe_genome_pos('1000') = 1000
       >>> safe_genome_pos('10,000') = 100000
    '''
    if isinstance(s, int):
        return s
    elif isinstance(s, str):
        return int(s.replace(',', ''))
    else:
        raise ValueError('invalid type "%s" for "save_genome_pos"' % type(s))


#class TermsQuery(TermQuery):
#    _internal_name = "terms"
#
#    def __init__(self, *args, **kwargs):
#        super(TermsQuery, self).__init__(*args, **kwargs)
#
#    def add(self, field, value, minimum_match=1):
#        #if type(value) is not types.ListType:
#        if isinstance(value, list):
#            raise InvalidParameterQuery("value %r must be valid list" % value)
#        self._values[field] = value
#        if minimum_match:
#            if isinstance(minimum_match, int):
#                self._values['minimum_match'] = minimum_match
#            else:
#                self._values['minimum_match'] = int(minimum_match)


class ESQuery():
    ES_AVAILABLE_TYPES = settings.ES_AVAILABLE_TYPES
    ES_MAX_QUERY_LENGTH = settings.ES_MAX_QUERY_LENGTH
    ES_INDEX_NAME = settings.ES_INDEX_NAME

    def __init__(self, user=None):
        self.conn = _conn
        self.s = Search().using(self.conn).index(self.ES_INDEX_NAME)
        self.user = user

        #remembers the last successful query and doc_types for later use
        self._q = None
        self._doc_types = None

    def status(self):
        '''Return the status report from cluster_health call.'''
        return self.conn.cluster.health()

    def _get_user_filter(self, user=None):
        '''Get a filter query with given user context, which will be used
           for filtering hits down to those are only accessible to the user.
        '''
        #filter = TermQuery(field='permission', value='gnfusers')
        user = user or self.user

        # filter = BoolQuery()
        filters = []

        #filter by roles
        if not user or user.is_anonymous():
            user_roles = []
        else:
            user_roles = get_role_shortnames(user.roles)
        if 'biogpsusers' not in user_roles:
            #always add the role for public access
            user_roles.append('biogpsusers')
        # role_filter = TermsQuery(field='role_permission', value=user_roles)
        role_filter = Q('terms', role_permission=user_roles)
        filters.append(role_filter)

        #filter by username to get user's own objects
        if user and user.username:
            # username_filter = TermQuery(field='username', value=user.username)
            username_filter = Q('term', username=user.username)
            filters.append(username_filter)

        return filters

    def _get_default_facets(self, doc_types):
        facets = set()
        if len(doc_types) > 0:
            for _type in doc_types:
                if _type in self.ES_AVAILABLE_TYPES:
                    facets |= set(self.ES_AVAILABLE_TYPES[_type]['facets'])
            facets = list(facets)
        return facets or None

    # def _switch_index(self, doc_types=None):
    #     '''switch index to perform ES queries based on doc_types:
    #          if doc_types = "dataset" or ["dataset"], set to
    #              settings.ES_INDEXES['dataset']
    #          if doc_types contains "dataset" and others, include
    #              settings.ES_INDEXES['dataset']
    #          otherwise, set to settings.ES_INDEXES['default']
    #     '''
    #     if doc_types in ['dataset', ['dataset'], ('dataset',)]:
    #         self.conn.default_indices = [settings.ES_INDEXES['dataset']]
    #     elif type(doc_types) in (types.ListType, types.TupleType) and \
    #          'dataset' in doc_types:
    #         self.conn.default_indices = [settings.ES_INDEXES['default'],
    #                                       settings.ES_INDEXES['dataset']]
    #     else:
    #         self.conn.default_indices = [settings.ES_INDEXES['default']]

    def _query(self, q=None, doc_types=None, fields=None, **kwargs):
        '''Do the actual query.'''
        q = q or self._q
        doc_types = doc_types or self._doc_types
        # self._switch_index(doc_types)
        s = self.s.doc_type(**doc_types).query(q, fields=fields).extra(**kwargs)
        # Run the actual search
        try:
            result = s.execute()
        except ElasticsearchException:
            exc_name = sys.exc_type.__name__
            err_msg = sys.exc_value.args[0] if (sys.exc_value.args) > 0 else ""
            err_msg = exc_name + ": " + err_msg
            result = {'error': err_msg}

        #record the last successful query and doc_types for later use:
        self._q = q
        self._doc_types = doc_types

        result = BiogpsSearchResult(result)
        #keep a reference of ESQuery object generates the result.
        result.query = self
        return result

    def has_valid_doc_types(self):
        '''Return True if "only_in" doc_types used in ES query are valid type
           (specified in settings.ES_AVAILABLE_TYPES)
        '''
        if self._doc_types and isinstance(self._doc_types, list) and \
                len(set(self._doc_types) - set(self.ES_AVAILABLE_TYPES)) == 0:
            return True
        else:
            return False

    def query(self, q=None, fields=None, start=0, size=10, sort=None, only_in=None,
              h=['_all'], facets=None, returnquery=False, explain=False,
              filter_by=None, custom_filter=None):
        '''Perform a query on ES and return SearchResult object.
           @param q: if q is a string, it will be wrapped as a StringQuery,
                      otherwise, q must be a pre-built Query instance.
           @param fields: a list of fields to be returned in the query result.
                          to return all field, use ['_source'].
           @param start:  hits to skip, for pagination.
           @param size:   # of hits to be returned, for pagination.
           @param sort:  fields used to sort return hits, e.g.,
                            ['species', 'symbol']
                            ['-_id']  # descending on _id field
           @param only_in: a list of "index_types" to search against. Any types
                            not in self.ES_AVAILABLE_TYPES will be ignored;
                           or a string of one specific index_type;
                           or if empty (None or []), all available index_type
                                 will be searched against.
           @param h: fields for highlighting
           @param facets: fields for faceting, using default facets if None.
           @param returnquery: if True, return query JSON string for debugging.
           @param explain: if True, enables explanation for each hit on how its
                             score was computed.
           @param filter_by: A dictionary of {<field>: <value>} or
                                a list of (<field>, <value>) tuple, e.g.,
                      {'tag': 'chart', 'species': 'human'}
                      [('tag', 'chart'), ('species', ['human', 'mouse'])]
                      Note that <value> can be a list for multiple values.
           @param custom_filter: if provided, apply this filter instead.

        '''
        # Parse out the possible types to search across
        # doc_types = []
        # if only_in:
        #     if isinstance(only_in, basestring):
        #         only_in = [only_in]
        #     doc_types = list(set(only_in) & set(self.ES_AVAILABLE_TYPES))
        # doc_types = doc_types or self.ES_AVAILABLE_TYPES.keys()
        if only_in:
            if isinstance(only_in, str):
                only_in = [only_in]
            doc_types = only_in
        else:
            doc_types = self.ES_AVAILABLE_TYPES.keys()

        # Initialize q if it was not specified
        if not q:
            q = MatchAll()
        # Setup q as a Query object if it was passed in as a string
        if isinstance(q, str):
            # Check for max query length
            if len(q) > self.ES_MAX_QUERY_LENGTH:
                return BiogpsSearchResult({'error': 'Query string too long.'})
            #q = StringQuery(q, default_operator='AND')
            q = Q('query_string', query=q)

        # Apply custom_filter if provided
        if custom_filter:
            q = Bool(must=q, filter=custom_filter)
        # Otherwise, call the default filter build chain
        else:
            filters = self._build_filters(doc_types, filter_by)
            if filters:
                q = Bool(must=q, filter=filters)

        s = self.s.doc_type(**doc_types).query(q, fields=fields)
        # Add highlighting
        for _h in h:
            s.highlight(_h, fragment_size=300, number_of_fragments=0)

        # Add faceting
        _facets = facets or self._get_default_facets(doc_types)
        if _facets:
            for _f in _facets:
                a = A('terms', field=_f)
                s.aggs.bucket(_f, a)
        if sort:
            s.sort(*sort)
        if explain:
            s.extra(explain=explain)
        s = s[start: (start + size)]

        # Only for debugging
        if returnquery:
            return json.dumps(s.to_dict(), indent=2)

        # Run the actual search
        try:
            result = s.execute()
        except ElasticsearchException:
            exc_name = sys.exc_type.__name__
            err_msg = sys.exc_value.args[0] if (sys.exc_value.args) > 0 else ""
            err_msg = exc_name + ": " + err_msg
            result = {'error': err_msg}
        return result

    # def fetch(self, start, size=None):
    #     '''Based on stored last self._q and self._doc_types to fetch more hits
    #        based on given start and size.
    #        size will be the same if not provided.
    #     '''
    #     if not self._q or not self._doc_types:
    #         return

    #     self._q.start = start
    #     if size:
    #         self._q.size = size
    #     return self._query()

    def _build_filters(self, only_in=[], filter_by=None):
        '''Return list of hits based on given value on a specific field.
           @param filter_by: A dictionary of {<field>: <value>} or
                             a list of (<field>, <value>) tuple, e.g.,
                   {'tag': 'chart', 'species': 'human'}
                   [('tag', 'chart'), ('species', ['human', 'mouse'])]
                   Note that <value> can be a list for multiple values.

           @param kwargs: refer to self.query method.
        '''
        filters = self._get_user_filter()

        if filter_by:
            if isinstance(filter_by, dict):
                _filter_by = filter_by.items()
            else:
                _filter_by = filter_by
            for (field, value) in _filter_by:
                filters.append(Q('terms', field=value))

        return filters

    def get(self, type, id, fields=None):
        '''Get an indexed doc based on type and doc id.
           Optional fields can be used to specify the fields should be
           returned. By default, the whole doc will be returned.
           e.g.

                 self.get('gene', '1017', fields=['name', 'symbol'])
                 self.get('plugin', '9')
            if unknown id, None is returned.
        '''
        if type not in self.ES_AVAILABLE_TYPES:
            raise ValueError('Unknown "type": "%s".' % type)

        # if type is any of biogps models, do a query with user_filter
        #result = self.filter("_id", id, only_in=[type])
        q = Q('term', _id=id, filter=self._get_user_filter())
        s = self.s.doc_type([type]).query(q, fields=fields)
        result = s.execute()

        if result.hits.total == 1:
            return result.hits[0]
        elif result.hits.total == 0:
            return
        else:
            raise ValueError('Ambiguous "id", "%s", in "%s" index_type.' % (id, type))

        # if '_source' in d:
        #     return dotdict(d['_source'])
        # elif 'fields' in d:
        #     d['fields']['id'] = d['_id']
        #     return dotdict(d['fields'])
        # else:
        #     raise KeyError('Can not find either "_source" or "fields" key.')

    # def query_gene_by_interval(self, chr, gstart, gend,
    #                            taxid=None, species=None, assembly=None,
    #                            **kwargs):
    #     '''query genes by genome interval.'''
    #     if (taxid, species, assembly) == (None, None, None):
    #         raise ValueError('At least one of "taxid", "species", "assembly" need to be specified.')

    #     qrange = ESRange(field='pos',
    #                      from_value=safe_genome_pos(gstart),
    #                      to_value=safe_genome_pos(gend),
    #                      include_lower=True,
    #                      include_upper=True)
    #     q = RangeQuery(qrange)
    #     filter = BoolQuery()
    #     filter.add_must(TermQuery('chr', chr))
    #     if taxid:
    #         filter.add_must(TermQuery('taxid', taxid))
    #     if species:
    #         filter.add_must(TermQuery('species', species))
    #     if assembly:
    #         filter.add_must(TermQuery('assembly', assembly))

    #     q = FilteredQuery(q, filter)
    #     return self.query(q, only_in=['gene'], **kwargs)


class ESPages():
    ''' For use with Django's paginator. Currently not used after pyes
        update implemented ResultSet, which provides the count,
        __getitem__, and __len__ methods required for Django's paginator. '''
    def __init__(self, es_query, **kwargs):
        ''' Make initial ES query'''
        self.conn = ElasticSearch(settings.ES_HOST[0], timeout=10.0)
        self.es_query = es_query
        res = self.conn.search(query=self.es_query, size='0', **kwargs)
        self.total_hits = res['hits']['total']

    def count(self):
        return self.total_hits

    def __getitem__(self, q_slice):
        ''' Make ES query for range of hits'''
        q = self.es_query.search(start=str(q_slice.start), size=str(q_slice.stop-q_slice.start+1))
        res = self.conn.search(q)
        return res['hits']['hits']

    def __len__(self):
        return self.count()
