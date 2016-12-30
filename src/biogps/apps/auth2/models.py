from django.db import models
from django.db.models.signals import post_init
from django.contrib.auth.models import User, Group

from biogps.utils.fields.jsonfield import JSONField

ROLE_BIOGPSUSER = 'BioGPS Users'
ROLE_GNFUSER = 'GNF Users'
ROLE_NVSUSER = 'Novartis Users'
ROLE_SEPARATOR = '|'

GLOBAL_DEFAULT_SHARED_LAYOUT = [83, 114, 116, 158, 159, 170, 160, 1404, 1408];
#    3 "Default GNF layout" by "Chunlei Wu"
#    83 "Default layout" by "Chunlei Wu"
#    116 "Exon atlas" by "Andrew Su"
#    170 "KEGG" by "Andrew Su"
#    158 "Literature" by "Andrew Su"
#    160 "Model Organism Databases" by "Andrew Su"
#    114 "Reagents" by "Andrew Su"
#    159 "Wikipedia" by "Andrew Su"
#    1404 "Pathway" by "Chunlei Wu"
#    1408 "Nature Databases" by "Kira Anthony"



DEFAULT_UIPROFILE = {'defaultlayout': 83,
                   'sharedlayouts': GLOBAL_DEFAULT_SHARED_LAYOUT}  ##as the preset profile if user has empty profile.
DEFAULT_UIPROFILE_GNF = {'defaultlayout': 3,
                   'sharedlayouts': [3] + GLOBAL_DEFAULT_SHARED_LAYOUT}  ##as the preset profile if user has empty profile.

def clean_username(fqu):
    username = fqu
    for affix in ['@lj.gnf.org', '_nov']:
        if fqu.lower().endswith(affix):
            username = fqu[:-len(affix)]
            break
    return username

def expanded_username_list(username):
    for affix in ['@lj.gnf.org', '_nov']:
        if username.lower().endswith(affix):
            return [username]
    return [username+affix for affix in ['', '@lj.gnf.org', '_nov']]


class UserProfile(models.Model):
    '''
    This model provides extra information for each user.
    '''
    user = models.OneToOneField(User, related_name='profile')
    sid = models.CharField(max_length=100,blank=True,unique=True, db_index=True)
    affiliation = models.CharField(max_length=100,blank=True)
    roles = models.CharField(max_length=200,blank=True)
    uiprofile = JSONField(blank=True)

    def __unicode__(self):
        return u'UserProfile for "%s"' % (self.user.username)

    def set_default_uiprofile(self):
        if self.is_gnf_user():
            self.uiprofile = DEFAULT_UIPROFILE_GNF
        else:
            self.uiprofile = DEFAULT_UIPROFILE

    def get_uiprofile_or_create(self):
        '''Return uiprofile or create the default uiprofile.'''
        if not self.uiprofile:
            self.set_default_uiprofile()
        return self.uiprofile

    def get_roles(self):
        return self.roles.split(ROLE_SEPARATOR)

    def is_gnf_user(self):
        '''Return true if the user is a member of the GNF Role.'''
        if self.roles:
            return ROLE_GNFUSER in self.roles.split(ROLE_SEPARATOR)
        else:
            return False

    def is_nvs_user(self):
        '''Return true if the user is a member of the NVS Role.'''
        if self.roles:
            return ROLE_NVSUSER in self.roles.split(ROLE_SEPARATOR)
        else:
            return False

    class Meta:
#        db_table = 'adamauth_userprofile'
        ordering = ('user__username',)

# Add additional attributes to the built-in User model.
# Methods such as get_display_name and save_uiprofile are accessible from the
# template system as well, allowing calls like:
#       {{ user.display_name|escape }}
def _extend_user(user):
    _profile = user.profile
    setattr(user, 'sid', _profile.sid)
    setattr(user, 'affiliation', _profile.affiliation)
    setattr(user, 'roles', _profile.get_roles())
    setattr(user, 'uiprofile', _profile.get_uiprofile_or_create())
    setattr(user, 'is_gnf_user', _profile.is_gnf_user())
    setattr(user, 'is_nvs_user', _profile.is_nvs_user())
    setattr(user, 'myplugins', _profile.biogpsplugin_set)
    setattr(user, 'mylayouts', _profile.biogpsgenereportlayout_set)
    setattr(user, 'mygenelists', _profile.biogpsgenelist_set)
    from types import MethodType

    @models.permalink
    def get_absolute_url(user):
        """ Returns the appropriate URL for this profile. """
        return ('apps.bgprofile.view',
                [str(user.id), clean_username(user.username)])
    setattr(user, 'get_absolute_url',
            MethodType(get_absolute_url, user))

    def get_clean_username(user):
        ''' Return a string suitable for identifying the user.
            Also available to the template system, allowing calls like::
            {{ user.clean_username|escape }}
        '''
        return clean_username(user.username)
    setattr(user, 'clean_username', MethodType(get_clean_username, user))

    def get_display_name(user):
        ''' Return a string suitable for identifying the user.
            Also available to the template system, allowing calls like::
            {{ user.display_name|escape }}
        '''
        return user.first_name or clean_username(user.username)
    setattr(user, 'display_name', MethodType(get_display_name, user))

    def get_valid_name(user):
        '''Return user's full name or username if fullname is not available.'''
        return user.get_full_name() or clean_username(user.username)
    setattr(user, 'get_valid_name', MethodType(get_valid_name, user))

    def save_uiprofile(user, uiprofile):
        _profile = user.profile
        _profile.uiprofile = uiprofile
        _profile.save()
    setattr(user, 'save_uiprofile', MethodType(save_uiprofile, user))

    def can_share(self):
        '''Return true if the user is allowed to share plugins and layouts.

        The decision is made by checking if the user is in the **can_share** group.
        Membership in that group is assigned elsewhere.
        '''
        return self.groups.filter(name='can_share').count()>0
    setattr(user, 'can_share', MethodType(can_share, user))

    def has_openid(self):
        '''Return true if the user has an OpenID associated with their account.

        The decision is made by checking if the user is in the **openid** group.
        Membership in that group is assigned elsewhere.
        '''
        # return self.groups.filter(name='openid').count()>0
        # return hasattr(self, 'userassociation')
        return self.socialaccount_set.exists()
    setattr(user, 'has_openid', MethodType(has_openid, user))

    def is_openid_only(self):
        '''Return true if the user can only authenticate via OpenID.

        If the user belongs to the **openid** group, but not **adam**, then we
        assume that they do not have a password in ADAM.
        '''
#        return (self.groups.filter(name='openid').count()>0 and
#                self.groups.filter(name='adam').count()==0)
        # return self.has_openid() and self.password == '!'
        return self.has_openid() and not self.has_usable_password()
    setattr(user, 'is_openid_only', MethodType(is_openid_only, user))

    def add_group_by_name(self, group_name):
        '''Given a Group name, adds the user to said group.'''
        self.groups.add(Group.objects.get(name=group_name))
    setattr(user, 'add_group_by_name', MethodType(add_group_by_name, user))

    def grant_openid(self):
        '''Adds the user to the **openid** group, indicating they can now
        authenticate via OpenID.  This method is only called from
        biogps.auth2.views.register_openid
        '''
        self.add_group_by_name('openid')
    setattr(user, 'grant_openid', MethodType(grant_openid, user))

    def account_type(self):
        '''Return the type of account authentication this user has.
        '''
        if not self.is_authenticated():
            return "Anonymous"
        elif self.is_gnf_user:
            return "GNF User"
        elif self.is_nvs_user:
            return "Novartis User"
        return "BioGPS User"
    setattr(user, 'account_type', MethodType(account_type, user))

    # def is_friends_with(self, user2):
    #     '''Given a second user object, returns True if the two users are friends.
    #     '''
    #     from friends.models import friend_set_for
    #     return user2 in friend_set_for(self)
    # setattr(user, 'is_friends_with', MethodType(is_friends_with, user))

    def invite_status_with(self, user2):
        '''Given a second user object, returns:
            False if the two users have no connection.
            String if the two users are friends or an invite is in the system.
        '''
        invite = self.invitations_to.filter(from_user=user2)
        if invite:
            return invite[0].get_status_display()
        else:
            return False
    setattr(user, 'invite_status_with', MethodType(invite_status_with, user))

    def is_migrated(self):
        try:
            return self.migration.migrated
        except UserMigration.DoesNotExist:
            return False
    setattr(user, 'is_migrated', MethodType(is_migrated, user))

    return user

def extend_user_handler(sender, **kwargs):
    '''A signal handler to modify the default behavior of build-in User model.'''
    user = kwargs['instance']
    if user.id:
        try:
            _extend_user(user)
        except UserProfile.DoesNotExist:
            pass
    return True

post_init.connect(extend_user_handler, sender=User, dispatch_uid='extend_user_handler')

USERFLAG_CHOICES = (
    ('D', 'Demo account'),
)

class UserFlag(models.Model):
    user = models.OneToOneField(User, related_name='flag')
    type = models.CharField(max_length=1, choices=USERFLAG_CHOICES)

#    class Meta:
#        db_table = 'adamauth_userflag'


class UserMigration(models.Model):
    user = models.OneToOneField(User, related_name='migration')
    date = models.DateTimeField(auto_now_add=True)
    migrated = models.BooleanField(default=False)    #mark user migrated
    to_delete = models.NullBooleanField()    #mark user to be deleted
    flag = models.CharField(max_length=100, blank=True)  # a placeholder to keep any other flags

#    class Meta:
#        db_table = 'adamauth_usermigration'


