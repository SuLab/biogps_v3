'''
RemoteModel
'''
from django.db import models
from django.db.models.query import QuerySet


def make_query_set_manager(klass):
    """
    This function is great for creating custom QuerySets that work
    anywhere, related objects included.

    eg.
    class TrackQuerySet(QuerySet):
      def deployed(self):
        return self.filter(deployed = True)

    class Track:
      objects = make_query_set_manager(TrackQuerySet)

    >>> Track.objects.deployed().filter(...)
    >>> Album.objects.all()[0].tracks.all().deployed().filter(...)

    """
    class QuerySetManager(models.Manager):
        # http://docs.djangoproject.com/en/dev/topics/db/managers/#using-managers-for-related-object-access
        """
        Note that we have to return an instance of this funny local
        class, rather than simply creating a class that the QuerySet
        subclass as an argument to its constructor.  I'm not entirely
        sure why, but I suspect it's to do with how Django creates the
        related managers; it may not know or care what's been passed to
        a Manager's constructor.
        """
        use_for_related_fields = True

        def __init__(self):
            self.queryset_class = klass
            super(QuerySetManager, self).__init__()

        def get_queryset(self):
            return self.queryset_class(self.model)

        # def __getattr__(self, attr, *args):
        #   try:
        #     return getattr(self.__class__, attr, *args)
        #   except AttributeError:
        #     return getattr(self.get_queryset(), attr, *args)

    return QuerySetManager()


class RemoteQuerySet(QuerySet):
    def filter(self, *args, **kwargs):
        '''support queries like:
             .filter(id=1)
             .filter(pk=1)
             .filter(id__in=id_list)   or "pk__in"
        '''
        _m = self.model
        # id or pk query
        id = kwargs.get('id', kwargs.get('pk', None))
        if id:
            return [_m()._get_obj_by_id(id)]

        # id__in or pk__in query
        id_list = kwargs.get('id__in', kwargs.get('pk__in', []))
        if id_list:
            return _m()._get_obj_by_id_list(id_list)

        return []

    def get(self, *args, **kwargs):
        rs = self.filter(*args, **kwargs)
        if rs:
            return rs[0]
        else:
            return None

    def in_bulk(self, id_list):
        gene_list = self.filter(id__in=id_list)
        gene_dict = dict([(g.id, g) for g in gene_list])
        return gene_dict

    def count(self):
        _m = self.model()
        if hasattr(_m, '_count'):
            return _m._count()
        else:
            raise NotImplementedError()


class RemoteModel(models.Model):
    '''RemoteModel basically creates an empty db table,
       while the actual queries (via filter/get etc) are
       made through remote web service calls
    '''
    def _get_obj_by_id(self, id):
        '''actual method to make web service call and return a
           model instance.
        '''
        raise NotImplementedError('This method should be implemented by each sub-class.')

    objects = make_query_set_manager(RemoteQuerySet)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        raise NotImplementedError('"save" method of a "RemoteModel instance is disabled.')
