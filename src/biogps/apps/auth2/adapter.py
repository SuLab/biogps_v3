from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.app_settings import EmailVerificationMethod
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount import app_settings

from biogps.apps.auth2.models import (
    UserProfile, DEFAULT_UIPROFILE, ROLE_BIOGPSUSER,
)


class BiogpsAccountAdapter(DefaultAccountAdapter):
    def new_user(self, request):
        user = get_user_model()()
        user.is_active = False
        return user

    def get_login_redirect_url(self, request):
        assert request.user.is_authenticated()
        url = reverse('mainpage')
        return url


class BiogpsSocialAccountAdapter(DefaultSocialAccountAdapter):
    def new_user(self, request, sociallogin):
        user = get_user_model()()
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        assert request.user.is_authenticated()
        url = reverse('mainpage')
        return url

    def save_user(self, request, sociallogin, form=None):
        user = super(BiogpsSocialAccountAdapter, self).save_user(
            request, sociallogin, form)

        profile = UserProfile.objects.filter(user=user).first()

        if not profile:
            sid_prefix = user.username if user.username else str(user.id)
            UserProfile.objects.create(
                user=user,
                roles=ROLE_BIOGPSUSER,
                uiprofile=DEFAULT_UIPROFILE,
                sid=sid_prefix + '_sid',
            )

        return user

    def validate_disconnect(self, account, accounts):
        """
        Validate whether or not the socialaccount account can be
        safely disconnected.
        """
        if len(accounts) == 1:
            # No usable password would render the local account unusable
            if not account.user.has_usable_password():
                msg = ('Your account has no password set up. Please set your '
                       'password <a href="{}">here</a>.').format(
                    reverse('auth_password_change'))
                raise ValidationError(mark_safe(_(msg)))
            # No email address, no password reset
            if app_settings.EMAIL_VERIFICATION \
                    == EmailVerificationMethod.MANDATORY:
                if EmailAddress.objects.filter(user=account.user,
                                               verified=True).count() == 0:
                    raise ValidationError(_("Your account has no verified"
                                            " e-mail address."))
