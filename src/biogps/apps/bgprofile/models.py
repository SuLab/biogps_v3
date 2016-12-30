from django.db import models
from django.db.models.signals import post_init
from django.contrib.auth.models import User, Group
from biogps.utils.fields.jsonfield import JSONField

from biogps.apps.auth2.models import clean_username

DEFAULT_PROFILE_INFO = [
    {"name":"About Me", "body":"I use BioGPS, but haven't written anything about myself yet."},
]

DEFAULT_PROFILE_PRIVACY = {
    # Each has the options:
    #   public, friends, private
    "profile_visible": "friends",
    "name_visible": "friends",
    "email_visible": "private",
}

class BiogpsProfile(models.Model):
    """
    This model provides public & friend-only information for each user.
    """
    user = models.OneToOneField(User, unique=True)
    info = JSONField(blank=True, default=DEFAULT_PROFILE_INFO)
    links = JSONField(blank=True, default=[])
    privacy = JSONField(blank=True, default=DEFAULT_PROFILE_PRIVACY)

    def __unicode__(self):
        try:
            return u'BiogpsProfile for "%s"' % (self.user.username)
        except:
            return u'BiogpsProfile for undefined user'

    # Permission Checking Methods
    def belongs_to(self, user):
        """ Returns true if the passed in user is the owner of this profile instance. """
        return self.user == user

    def is_public(self, fpass):
        """ Returns true if the profile is visible to people outside the user's network. """
        return (self.privacy['profile_visible'] == 'public' or
                (fpass and self.privacy['profile_visible'] == 'friends')
                )

    def is_name_visible(self, fpass):
        """ Returns true if the name should be visible to the calling user. """
        return (self.privacy['name_visible'] == 'public' or
                (fpass and self.privacy['name_visible'] == 'friends')
                )

    def is_email_visible(self, fpass):
        """ Returns true if the email should be visible to the calling user. """
        return (self.privacy['email_visible'] == 'public' or
                (fpass and self.privacy['email_visible'] == 'friends')
                )

    def get_email(self):
        """ Returns the email address for this user, if public. """
        if self.privacy['email_visible'] == 'Friends':
            return self.user.email

    # Pre-view processing
    def filter_for_user(self, user):
        """ Filters down the profile information to just the content that should
            be seen by the given user. This method is destructive to the profile
            information, so should not be saved after calling.
        """
        fpass = False #self.user.is_friends_with(user) # Calculate here whether or not the two users are friends.
        mine = self.belongs_to(user)

        if self.is_public(fpass) or mine:
            # Profile is public and/or users are friends
            self.show_friends = True
        else:
            # Profile is bare-minimum for anonymous user
            self.info = []
            self.links = []
            self.show_friends = False

        # Filter name and affiliation
        if self.is_name_visible(fpass) or mine:
            self.affiliation = self.user.affiliation
            if (not self.affiliation) and self.user.username.lower().endswith('@lj.gnf.org'):
                self.affiliation = 'GNF'

        self.name = self.user.get_valid_name()

        # Filter email address
        if self.is_email_visible(fpass) or mine:
            self.email = self.user.email

        return self

    def get_absolute_url(self):
        """ Returns the appropriate URL for this profile. """
        return self.user.get_absolute_url()

