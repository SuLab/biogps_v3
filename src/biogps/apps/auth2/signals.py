from django.contrib import auth
from django.dispatch import Signal
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

from urlauth.signals import authkey_processed
from urlauth.models import AuthKey

from biogps.apps.auth2.utils import email_template
from biogps.apps.auth2.models import (
    UserProfile, DEFAULT_UIPROFILE, ROLE_BIOGPSUSER,
)

account_created = Signal(providing_args=['user', 'request'])


# taken from django-account to keep previous site functionality
def authkey_handler(key, user, **kwargs):
    extra = key.extra
    action = extra.get('action')

    if 'activation' == action:
        if not user.is_active:
            user.is_active = True
            user.save()
            email_template(user.email, 'account/mail/welcome',
                           user=user, domain=Site.objects.get_current().domain)

    if user.is_active:
        if 'new_email' == action:
            if 'email' in extra:
                user.email = extra['email']
                user.save()


authkey_processed.connect(authkey_handler, sender=AuthKey)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        user = instance
        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            sid_prefix = user.username if user.username else str(user.id)
            UserProfile.objects.create(
                user=user,
                roles=ROLE_BIOGPSUSER,
                uiprofile=DEFAULT_UIPROFILE,
                sid=sid_prefix + '_sid',
            )

post_save.connect(create_user_profile, sender=get_user_model())
