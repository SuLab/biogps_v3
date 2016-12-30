'''
A collection of common classes/functions for BioGPS models.
'''
import types

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
#from friends.models import friend_set_for
from django.utils.text import capfirst
from biogps.apps.www.models import BiogpsPermission
from biogps.utils.const import (ROLEPERMISSION_VALUES, ROLEPERMISSION_SHORTNAMES)
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from biogps.apps.rating.models import Rating
from biogps.apps.favorite.models import Favorite
from biogps.utils import dotdict


def queryset_iterator(model, batch_size=100):
    '''Performs batch query against DB for specified model, yields iterator'''
    start = 0
    total_cnt = model.objects.count()
    print("Iterating %d rows..." % total_cnt)
    for start in range(start, total_cnt, batch_size):
        end = min(start+batch_size, total_cnt)
        for row in model.objects.order_by('pk')[start:end]:
            yield row


def get_role_shortnames(role_list):
    '''Convert a list of roles to a list of roles in "short_names"
       (defined in biogps.utils.const.ROLEPERMISSION_SHORTNAMES)
    '''
    return [ROLEPERMISSION_SHORTNAMES.get(r, r) for r in role_list]


#==============================================================================
# Customized Manager
#==============================================================================
class PermissionManager(models.Manager):
    '''A customized model manager handles object permission.'''
    def get_mine(self, user):
        '''Return all objects created by the given user.
            @param user: a User object or user's sid string.
            @return: a QuerySet of objects.
        '''
        authorid = user.sid if isinstance(user, User) else user
        return self.filter(ownerprofile__sid=authorid)

    def get_available_by_role(self, roles):
        available_objects_byrole = self.none()
        if roles:
            if isinstance(roles, str):
                roles = [roles]
            object_type = self.model.object_type
            perm_qs = BiogpsPermission.objects.filter(object_type=object_type,
                                                      permission_type='R',
                                                      permission_value__in=roles)
            available_objects_byrole = self.filter(pk__in=perm_qs.values('object_id'))

        return available_objects_byrole

    def get_available_by_username(self, username):
        object_type = self.model.object_type
        shared_objects_byusername = self.none()
        if username:
            #Check if the object is shared with me by username
            perm_qs = BiogpsPermission.objects.filter(object_type=object_type,
                                                      permission_type='U',
                                                      permission_value=username)
            shared_objects_byusername = self.filter(pk__in=perm_qs.values('object_id'))
        return shared_objects_byusername

    def get_available_by_friendship(self, user):
        return self.none()
    #     object_type = self.model.object_type
    #     shared_objects_byfriendship = self.none()
    #     if user:
    #         #Check if the object is shared with me by my friends
    #         myfriends = [f.username for f in friend_set_for(user)]
    #         perm_qs = BiogpsPermission.objects.filter(object_type=object_type,
    #                                                   permission_type='F',
    #                                                   permission_value__in=myfriends)
    #         shared_objects_byfriendship = self.filter(pk__in=perm_qs.values('object_id'))
    #     return shared_objects_byfriendship

    def get_available(self, user, excludemine=False):
        ''' return all available objects for given user, including user's own objects and
           those shared ones user has permission.
           if anonymous user, return only public available objects.
           if excludemine, exclude those created by this user.
        '''
        if user.is_anonymous():
            query_result = self.get_available_by_role('BioGPS Users')
        else:
            if excludemine:
                mine = self.none()
            else:
                mine = self.get_mine(user.sid)
            query_result = self.get_available_by_role(user.roles) | \
                           self.get_available_by_username(user.username) | \
                           self.get_available_by_friendship(user) | mine
            if excludemine:
                query_result = query_result.exclude(ownerprofile__sid=user.sid)

        #return query_result.distinct()
        #Above "query_result.distinct()" causes an Oracle DB error:
        #DatabaseError: ORA-00932: inconsistent datatypes: expected - got NCLOB
        #for chained query like
        #BiogpsPlugin.objects.get_available(uu).filter(popularity__score__isnull=False).order_by('-popularity__score')
        return query_result

    def get_available_from(self, owner, viewer):
        ''' return all available objects owned by a given user, that are
            accessible by the calling user. used for the profile pages.
        '''
        if owner == viewer:
            return self.get_mine(owner.sid)
        else:
            return self.get_available(viewer, excludemine=True).filter(ownerprofile__sid=owner.sid)


#===============================================================================
# Abstract Models
#===============================================================================

class ModelWithPermission(models.Model):
    '''Provide permission control on each object in a model
       The model much provide self.object_type property.
    '''

    PUBLIC_ROLE = "BioGPS Users"
    GNF_ROLE = "GNF Users"

    @property
    def allowed_roles(self):
        return BiogpsPermission.objects.filter(object_type=self.object_type,
                                               object_id=self.id,
                                               permission_type='R')

    @property
    def allowed_users(self):
        return BiogpsPermission.objects.filter(object_type=self.object_type,
                                               object_id=self.id,
                                               permission_type='U')

    def get_permission(self):
        return BiogpsPermission.objects.filter(object_type=self.object_type,
                                               object_id=self.id).values('permission_type', 'permission_value')

    def set_permission(self, data, append=False):
        """data is a list of dictionaries like (same as that returned from get_permission):
           [{'permission_type': 'R', 'permission_value': 'GNF Users'},
            {'permission_type': 'U', 'permission_value': 'cwutest'}]
        """
        if not append:
            self.clean_permission()

        for d in data:
            d.update(dict(object_type=self.object_type, object_id=self.id))
            try:
                existing_item = BiogpsPermission.objects.get(**d)
            except BiogpsPermission.DoesNotExist:
                new_item = BiogpsPermission(**d)
                new_item.save()

    def clean_permission(self):
        """clean all permission and make it visible to author only."""
        existing_objs = BiogpsPermission.objects.filter(object_type=self.object_type, object_id=self.id)
        existing_objs.delete()

    permission = property(get_permission, set_permission, clean_permission)

    #set a make_private as a convenient alias
    make_private = clean_permission

    def share_to_public(self):
        """set a object to be shared with everybody, which set "BioGPS Users"
           role internally and remove all existing permissions
        """
        self.permission = [{'permission_type': 'R',
                            'permission_value': self.PUBLIC_ROLE}]

    def share_to_gnf(self):
        """set a object to be shared with GNF users, which set "GNF Users"
           role internally and remove all existing permissions
        """
        self.permission = [{'permission_type': 'R',
                            'permission_value': self.GNF_ROLE}]

    def share_to_user(self, to_user):
        """set a object to be shared with a specified user while keeping
           existing permissions
        """
        if to_user != self.owner:
            self.set_permission([{'permission_type': 'U',
                                  'permission_value': to_user.username}],
                                append=True)

    def share_to_users(self, to_user_list):
        """set a object to be shared with a list of specified users while
           keeping existing permissions
        """
        self.set_permission([{'permission_type': 'U', 'permission_value': to_user.username} for to_user in to_user_list if to_user != self.owner], append=True)

    def share_to_friends(self, of_user):
        """set a object to be shared with all connected friends of the
           specified user, while keeping existing permissions
        """
        self.set_permission([{'permission_type': 'F', 'permission_value': of_user.username}], append=True)

    @property
    def is_public(self):
        '''return True is the object is shared to everyone.'''
        return self.PUBLIC_ROLE in self.get_role_permission(returnsorted=False)

    #@property
    def is_shared(self):
        '''return True is the object is shared to a role or at least one user.
        '''
        return len(self.get_role_permission(returnsorted=False)) > 0 or \
               len(self.get_user_permission(returnsorted=False)) > 0 or \
               len(self.get_friendship_permission(returnsorted=False)) > 0

    def is_restricted(self):
        '''return True if the object is shared with only a subset of users'''
        return not (self.is_public or self.is_private)

    @property
    def is_private(self):
        '''return True is the object is not shared with anybody, only owner
           has the access.
        '''
        return not self.is_shared()

    class Meta:
        abstract = True

    def get_role_permission(self, returnsorted=False, returnshortname=False):
        pli = list(set([x['permission_value'] for x in self.get_permission() if x['permission_type'] == 'R']))
        if sorted:
            pli.sort()
        if returnshortname:
            pli = [ROLEPERMISSION_SHORTNAMES[x] for x in pli]
        return pli

    @property
    def role_permission(self):
        return self.get_role_permission(returnsorted=True)

    def get_user_permission(self, returnsorted=False):
        pset = set([x['permission_value'] for x in self.get_permission() if x['permission_type'] == 'U'])
        if sorted:
            return sorted(pset)
        else:
            return pset

    @property
    def user_permission(self, returnsorted=True):
        return self.get_user_permission(returnsorted=True)

    def get_friendship_permission(self, returnsorted=False):
        pset = set([x['permission_value'] for x in self.get_permission() if x['permission_type'] == 'F'])
        if sorted:
            return sorted(pset)
        else:
            return pset

    @property
    def friendship_permission(self, returnsorted=True):
        return self.get_friendship_permission(returnsorted=True)


def set_object_permission(object, roles=None, users=None, sep=','):
    '''
    A convenient function for set object role and user permissions.
       roles is a string for "shortcut" word defined in ROLEPERMISSION_VALUES,
               or can be multiple words seperated by sep.
                 e.g. 'myself', 'gnfusers, novartisusers'
               or can be special keywords:
                 'friendusers' or 'novartisusers'
            #TODO: need to expand to any role.

       users is a string with allowed usernames.
                 e.g. 'cwudemo', 'cwudemo1, cwuemo2'

            #TODO: need to check if user exists

       if both roles and users are None, existing permissions will be cleaned
    '''
    permissions = []
    if type(roles) in types.StringTypes:
        # Special handling for 'friends' since it's not really a role
        if roles.strip() == 'friendusers':
            permissions.append(dict(permission_type="F",
                                    permission_value=object.owner.username))
        else:
            # Special handling because 'novartisusers' implies both Novartis & GNF
            if roles.strip() == 'novartisusers':
                roles = 'gnfusers, novartisusers'

            for _rolepermission in roles.strip().split(','):
                rolepermission = ROLEPERMISSION_VALUES.get(_rolepermission.strip(), None)
                if rolepermission:
                    permissions.append(dict(permission_type="R",
                                            permission_value=rolepermission))

    if type(users) in types.StringTypes:
        for _user in users.strip().split(','):
            userpermission = _user.strip()
            if userpermission:
                permissions.append(dict(permission_type="U",
                                        permission_value=userpermission))
    if permissions:
        object.permission = permissions
    else:
        del object.permission


class BioGPSModel(ModelWithPermission):

    def _object_cvt(self, extra_attrs={}, mode='ajax'):
        '''A base function to convert a BiogpsModel object to a simplified
            python dictionary, with all values in python's primary types only.
            Such a dictionary can be passed directly to fulltext indexer or
            serializer for ajax return.

          @param extra_attrs: a dictionary for extra attrs to add:
                        {'a1': 's1',    # out['a1'] = object.s1
                         'a2': fn1,     # out['a2'] = fn(object)
                         'AS_IS': ['s2', 's3'] # out['s1'] = object.s1, out['s2'] = object.s2
          @param mode: can be one of ['ajax', 'es'], used to return slightly
                         different dictionary for each purpose.
          @return: an python dictionary
        '''
        _available_modes = ['ajax', 'es']
        if mode not in _available_modes:
            raise ValueError('"mode" parameter needs to be one of %s.' % _available_modes)

        owner = {'username': self.owner.username,
                 'name': self.owner.get_valid_name(),
                 'url': self.owner.get_absolute_url()}
        out = {
            'id': self.id,
            'owner': owner,
            'permission_style': self.permission_style
        }
        for attr in ['created', 'lastmodified']:
            out[attr] = getattr(self, attr).strftime('%Y-%m-%d %H:%M:%S')
        if self.tags:
            out['tags'] = [t.name for t in self.tags]
        role_permission = self.get_role_permission(returnsorted=True,
                                                   returnshortname=True)
        if role_permission:
            out['role_permission'] = role_permission

        if self.rating_data:
            out['rating_data'] = self.rating_data

        for attr in extra_attrs:
            if attr == 'AS_IS':
                for k in extra_attrs['AS_IS']:
                    out[k] = getattr(self, k)
            else:
                val = extra_attrs[attr]
                if type(val) is types.StringType:
                    out[attr] = getattr(self, val)
                elif type(val) is types.FunctionType:
                    out[attr] = val(self)

        if mode == 'es':
            if not self.short_name:
                raise ValueError('"short_name" attribute needs to be set first.')
            out['in'] = self.short_name
            if 'options' in out and out['options'] == '':
                out['options'] = None     # this is a tmp fix for ES error when creating a new plugin.

        return out

    def object_cvt(self, *args, **kwargs):
        """should be implemeted in each subClass of BiogpsModel."""
        raise NotImplementedError

    def re_index(self):
        '''Force the object re-indexed by ES'''
        from biogps.search.build_index import BiogpsModelESIndexer
        es_indexer = BiogpsModelESIndexer()
        doc = self.object_cvt(mode='es')
        res = es_indexer.index(doc, self.short_name, self.id)
        return res

    def get_author(self):
        '''returns User object of the author of this plugin.
           deprecated. Use get_owner instead.
        '''
        return self.get_owner()

    def get_owner(self):
        return self.ownerprofile.user
    def set_owner(self, user):
        self.ownerprofile = user.profile
    owner = property(get_owner, set_owner)

    @property
    def permission_style(self):
        '''Return a string class for CSS indication of the general permission
           level of this object.
        '''
        if self.is_public:
            return 'public'
        elif self.is_private:
            return 'private'
        else:
            return 'restricted'

    def save(self, force_insert=False, force_update=False):
        '''Override "save" method to automatically update "author" field from
           ownerprofile field before saving.
        '''
        self.author = self.owner.get_valid_name()
        super(ModelWithPermission, self).save(force_insert, force_update)

    objects = PermissionManager()

    ratings = GenericRelation(Rating)

    def check_user_favorite(self, user, con_type):
        '''Check if user favorited this object.'''
        try:
            user.favorite_set.get(content_type=con_type, object_id=self.id)
            self.is_favorite = True
        except Favorite.DoesNotExist:
            pass

    def check_user_rating(self, user, con_type):
        '''Check if user rated this object.'''
        try:
            self.user_rating = user.rating_set.get(content_type=con_type,
                                                   object_id=self.id).rating
        except Rating.DoesNotExist:
            pass

    def prep_user_data(self, user):
        '''Get user's favorites, etc and append results to object.'''
        con_type = ContentType.objects.get_for_model(self)
        self.check_user_favorite(user, con_type)
        self.check_user_rating(user, con_type)

    @staticmethod
    def get_object_and_ctype(model_name, pk):
        ''' Returns object and content type for the supplied model and key'''
        model_prefixes = {'plugin': 'biogps',
                          'dataset': 'biogps',
                         }
        try:
            # Supporting old 'www' app label
            content_type = ContentType.objects.get(app_label='www',
                              model=model_prefixes[model_name]+model_name)
        except ContentType.DoesNotExist:
            try:
                content_type = ContentType.objects.get(model=
                                    model_prefixes[model_name]+model_name)
            except ContentType.DoesNotExist:
                # Invalid model_name
                return False, False
        try:
            obj = content_type.get_object_for_this_type(id=pk)
        except ObjectDoesNotExist:
            # Invalid pk
            return False, True
        return obj, content_type

    def avg_rating(self):
        try:
            avg_rating = int(round(self.ratings.all().aggregate(models.Avg(
                             'rating'))['rating__avg']))
        except TypeError:
            # No ratings yet
            avg_rating = 0
        return avg_rating

    def total_ratings(self):
        ''' Number of ratings for this object'''
        return self.ratings.count()

    @property
    def rating_data(self):
        ''' Return all rating information for this object'''
        rating_avg = self.avg_rating()
        # Multiply by 2 for half star ratings
        rating_stars_avg = rating_avg * 2
        return dict(avg=rating_avg, avg_stars=rating_stars_avg,
                                                total=self.total_ratings())

    class Meta:
        abstract = True
        get_latest_by = 'lastmodified'


#class BiogpsSpecies:
#    '''A class to hold all metadata related with species.
#       Note that this is not a Django Model, but we still put it in models.py,
#       because it represents data as well. The difference is that we sync the
#       original data from remote BOCSERVICE_URL when the app starts.
#    '''
#    def __init__(self, **kwds):
#        self.__dict__.update(kwds)
#
#    def __repr__(self):
#        return str(self.__dict__.items())
#
#    def __getitem__(self, item):
#        return self.__dict__.get(item, None)

class BiogpsSpecies(dotdict):
    '''A class to hold all metadata related with species.
       Note that this is not a Django Model, but we still put it in models.py,
       because it represents data as well. The difference is that we sync the
       original data from remote BOCSERVICE_URL when the app starts.
    '''
    pass

class BiogpsSpeciesList(object):

    def __init__(self, container=[]):
        self.container = container
        self.sync_metadata()

    def add(self, k):
        self.container.append(k)

    def __getitem__(self, key):
        for s in self.container:
            if s.name == key or s.taxid == key:
                return s
        raise KeyError("Need a species name or taxid as the key.")

    def __iter__(self):
        return self.container.__iter__()

    def __len__(self):
        return len(self.container)

    def __repr__(self):
        return str(self.container)

    def __str__(self):
        return 'BiogpsSpeciesList: ' + ', '.join(self.available_species)

    @property
    def available_species(self):
        '''return a list of available species names.'''
        return [s.name for s in self.container]

    def form_choices(self):
        '''return a list of tuples for use in Django Forms'''
        return [(s.name, capfirst(s.name)) for s in self.container]

    def sync_metadata(self):
        '''Sync meta from remote BOCSERVICE_URL.'''
        if self.__len__() == 0:
            self.add(BiogpsSpecies(
                name='human',
                taxid=9606,
                prefix='Hs',
                assembly='hg19',
                genus='Homo sapiens',
                sample_gene=1017        # CDK2
            ))
            self.add(BiogpsSpecies(
                name='mouse',
                taxid=10090,
                prefix='Mm',
                assembly='mm9',
                genus='Mus musculus',
                sample_gene=12566       # CDK2
            ))
            self.add(BiogpsSpecies(
                name='rat',
                taxid=10116,
                prefix='Rn',
                assembly='rn4',
                genus='Rattus norvegicus',
                sample_gene=362817      # CDK2
            ))
            self.add(BiogpsSpecies(
                name='fruitfly',
                taxid=7227,
                prefix='Dm',
                assembly='dm3',
                genus='Drosophila melanogaster',
                sample_gene=42453       # CDK2
            ))
            self.add(BiogpsSpecies(
                name='nematode',
                taxid=6239,
                prefix='Ce',
                assembly='ce7',
                genus='Caenorhabditis elegans',
                sample_gene=172677      # CDK8
            ))
            self.add(BiogpsSpecies(
                name='zebrafish',
                taxid=7955,
                prefix='Dr',
                assembly='danRer6',
                genus='Danio rerio',
                sample_gene=406715      # CDK2
            ))
            self.add(BiogpsSpecies(
                name='thale-cress',
                taxid=3702,
                prefix='At',
                assembly='',            # we don't have genomic data for arabidopsis right now
                genus='Arabidopsis thaliana',
                sample_gene=837405      # CSD1
            ))
            self.add(BiogpsSpecies(
                name='frog',
                taxid=8364,
                prefix='Xt',
                assembly='xenTro2',
                genus='Xenopus tropicalis',
                sample_gene=493498      # cdk2
            ))
            self.add(BiogpsSpecies(
                name='pig',
                taxid=9823,
                prefix='Ss',
                assembly='susScr2',
                genus='Sus scrofa',
                sample_gene=100127490,  # CDK2
            ))

            #assign rank (from 1) to each species in the order of addition
            #assign short_genus to each species (like H. sapiens for human)
            for i, s in enumerate(self.container):
                s['rank'] = i + 1
                _genus_words = s['genus'].split()
                s['short_genus'] = "%s. %s" % (_genus_words[0][0].upper(), _genus_words[-1])

Species = BiogpsSpeciesList()
