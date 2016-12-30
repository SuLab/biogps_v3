'''
This file defines a BiogpsSearchResult class to hold search result returned
from es_lib.ESQuery.
'''
from biogps.utils import dotdict


class BiogpsSearchResult(dotdict):
    def __init__(self, *args, **kwargs):
        super(BiogpsSearchResult, self).__init__(*args, **kwargs)
        if not self.has_error():
            self['hits']['hit_count'] = len(self['hits']['hits'])

    def has_error(self):
        return self.get('error', None) is not None

    def __len__(self):
        if 'hits' in self and 'total' in self.hits:
            return self.hits.total
        return 0

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results, but still keep
        the dictionary-like behavior of get value by key.
        """

        if isinstance(k, basestring):
            #get an item like a dictionary
            value = self.get(k, None)
            return value

        elif isinstance(k, slice):
            start = k.start or 0
            stop = k.stop or len(self)
            if (k.start < 0 or k.stop < 0):
                raise IndexError("Negative indexing is not supported.")

            current_start, current_stop = self.get_current_hit_range()
            if start < current_start or stop > current_stop:
                #need to do an new query to get the chunk of hits
                self.__init__(self.query.fetch(start, stop - start))
                current_start, current_stop = self.get_current_hit_range()

            hit_list = self['hits']['hits'][start - current_start:stop - current_start]
            return [self._get_hit_fields(hit) for hit in hit_list]

        elif isinstance(k, int):
            #get a single item list a list
            if k < 0:
                raise ValueError("Negative indexing is not supported.")
            if k >= len(self):
                raise IndexError("Index out of range.")
            current_start, current_stop = self.get_current_hit_range()
            if k < current_start or k >= current_stop:
                #need to do an new query to get the chunk of hits
                self.__init__(self.query.fetch(k))
                current_start, current_stop = self.get_current_hit_range()
            hit = self['hits']['hits'][k - current_start]
            return self._get_hit_fields(hit)
        else:
            raise TypeError

    def _get_hit_fields(self, hit):
        """A helper to return either "fields" or "_source", or just "id" from
           a hit record.
        """
        return hit.get('fields', hit.get('_source', {'id': hit['_id']}))

    def get_current_hit_range(self):
        '''Return (start, stop) indexes for returned hits.'''
        start = self.query._q.start
        stop = start + self.query._q.size
        return (start, stop)

    def object_cvt(self):
        '''convert result object to a serializable object.'''
        attributes_to_ignore = ['query', '_shards']
        out = {}
        for key in self.keys():
            if key not in attributes_to_ignore:
                out[key] = self[key]
        return out
