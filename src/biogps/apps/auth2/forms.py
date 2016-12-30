"""
Forms and validation code for user registration.

"""
from django import forms
import re
alnum_re = re.compile(r'^\w+$') # regexp. from jamesodo in #django
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from django_authopenid.forms import OpenidVerifyForm
#from captcha.fields import CaptchaField

from biogps.apps.auth2.models import (
    DEFAULT_UIPROFILE, ROLE_BIOGPSUSER, expanded_username_list,
)
from allauth.account.forms import SignupForm
from allauth.account.forms import ResetPasswordForm
from allauth.socialaccount.forms import SignupForm as AllauthSocialSignupForm

from biogps.apps.auth2.models import UserProfile

# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = { 'class': 'required' }


class RegistrationForm(SignupForm):
    #required fields
    # username, email, password and password_dup are already defined in SignupForm.

    #optional fields
    first_name = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(),
                                label=_(u'first name'))
    last_name = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(),
                                label=_(u'last name'))
    affiliation = forms.CharField(max_length=150, required=False,
                                  widget=forms.TextInput(),
                                  label=_(u'affiliation'))

    #checkbox
    tou = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Terms of Use'))

    signup_ann = forms.BooleanField(widget=forms.CheckboxInput(),
                                    initial=True, required=False)

    #required for django_friends module, when user signs up via the link received from a join-request.
    invitation_key = forms.CharField(max_length=40, required=False, widget=forms.HiddenInput())

    def clean_tou(self):
        """
        Validate that the user accepted the Terms of Service.

        """
        if self.cleaned_data.get('tou', False):
            return self.cleaned_data['tou']
        raise forms.ValidationError('You must agree to the terms to register')

    def clean_email(self):
        if 'email' in self.cleaned_data:
            email = self.cleaned_data['email']
            return email

    def save(self, request):
        user = super(RegistrationForm, self).save(request)
        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            # now create user profile
            # not useful now, set a dummy value here.
            # Will be deleted eventually.
            sid = user.username + '_sid'
            profile = UserProfile.objects.create(
                user=user,
                sid=sid,
                roles=ROLE_BIOGPSUSER,
                uiprofile=DEFAULT_UIPROFILE,
            )
        affiliation = self.cleaned_data.get('affiliation', '')
        if affiliation:
            profile.affiliation = affiliation
        profile.save()
        for param in ['first_name', 'last_name']:
            value = self.cleaned_data.get(param, '')
            if value:
                setattr(user, param, value)
        user.save()

        #This section is for handling sign-up with an invitation_key received from a join-request.
        #Ideally, the friendship should be established when user activate his account, instead upon sign-up.
        if self.cleaned_data["invitation_key"]:
            from friends.models import JoinInvitation # @@@ temporary fix for issue 93
            try:
                join_invitation = JoinInvitation.objects.get(confirmation_key = self.cleaned_data["invitation_key"])
                join_invitation.accept(user)
            except JoinInvitation.DoesNotExist:
                pass
        #end of the section

        return user


class SocialRegistrationForm(AllauthSocialSignupForm):
    first_name = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(),
                                label=_(u'first name'))
    last_name = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(),
                                label=_(u'last name'))
    affiliation = forms.CharField(max_length=150, required=False,
                                  widget=forms.TextInput(),
                                  label=_(u'affiliation'))
    tou = forms.BooleanField(
        widget=forms.CheckboxInput(attrs=attrs_dict),
        label=_(u'I have read and agree to the Terms of Use'),
    )
    signup_ann = forms.BooleanField(widget=forms.CheckboxInput(),
                                    initial=True, required=False)
    invitation_key = forms.CharField(max_length=40, required=False,
                                     widget=forms.HiddenInput())

    def clean_tou(self):
        if self.cleaned_data.get('tou', False):
            return self.cleaned_data['tou']
        raise forms.ValidationError('You must agree to the terms to register')

    def save(self, request):
        user = super(SocialRegistrationForm, self).save(request)

        affiliation = self.cleaned_data.get('affiliation', '')
        profile = user.profile
        if affiliation:
            profile.affiliation = affiliation
        profile.save()

        for param in ['first_name', 'last_name']:
            value = self.cleaned_data.get(param, '')
            if value:
                setattr(user, param, value)
        user.save()

        if self.cleaned_data["invitation_key"]:
            from friends.models import JoinInvitation
            try:
                join_invitation = JoinInvitation.objects.get(
                    confirmation_key=self.cleaned_data["invitation_key"])
                join_invitation.accept(user)
            except JoinInvitation.DoesNotExist:
                pass

        return user


#override original OpenidVerifyForm to fix an issue when using fqu
class OpenidVerifyForm(OpenidVerifyForm):
    def clean_username(self):
        """ validate username """
        if 'username' in self.cleaned_data:
            if not alnum_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(_("Usernames can only contain \
                    letters, numbers and underscores"))
            return self.cleaned_data['username']


class ForgetUsernameForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"), max_length=75)

    def save(self):
        email = self.cleaned_data["email"]
        username_li = sorted([x['username'] for x in User.objects.filter(email__iexact=email).values('username')])
        return username_li


class EditUserInfoForm(forms.Form):
    #required fields
#    username = forms.CharField(widget=forms.HiddenInput())
#    email = forms.EmailField(widget=forms.TextInput(),
#                             label=_(u'email address'))
    first_name = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(),
                                label=_(u'first name'))
    last_name = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(),
                                label=_(u'last name'))
    affiliation = forms.CharField(max_length=150, required=False,
                                  widget=forms.TextInput(),
                                  label=_(u'affiliation'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(EditUserInfoForm, self).__init__(*args, **kwargs)

    def save(self):
        if self.user.is_authenticated():
            updated = False
            for attr in ['first_name', 'last_name', 'affiliation']:
                new_value = self.cleaned_data.get(attr, None)
                if new_value:
                    if attr == 'affiliation':
                        profile = self.user.profile
                        profile.affiliation = new_value
                        profile.save()
                    else:
                        setattr(self.user, attr, new_value)
                        updated = True
            if updated:
                self.user.save()
        return self.user


class PasswordResetForm(ResetPasswordForm):
    '''subclass original PasswordResetForm to add username field, as the emails in our
       auth_user table are not unique.
    '''
    username = forms.CharField(max_length=30, label=_(u'Username'))

    def clean(self):
        username = self.cleaned_data.get('username', None)
        email = self.cleaned_data.get('email', None)
        if username and email:
            if User.objects.filter(username__in=expanded_username_list(username.lower()), email=email).count() == 1:
                return self.cleaned_data
        raise forms.ValidationError(u'Can not find matched user account')


# taken from django-account to keep previous site functionality
class EmailChangeForm(forms.Form):
    """
    Form for email chanage.
    """

    email = forms.EmailField(label=_(u'New email'))
