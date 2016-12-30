'''
The URLs listed here are served under /auth/, via https only in prod.
'''
from django.conf.urls import url
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

from biogps.apps.auth2 import views as auth2_views


urlpatterns = [
    url(r'^$',
        auth2_views.dashboard,
        name='auth_dashboard'),

    url(r'^checkusername/(?P<username>\w+)/$',
        auth2_views.check_username,
        name='auth_checkusername'),

    # Registration
    url(r'^signup/$',
        auth2_views.registration,
        name='auth_register'),
    url(r'^activation/required/$',
        TemplateView.as_view(template_name='account/activation_required.html'),
        name='activation_required'),
    url(r'^signup/complete/$',
        TemplateView.as_view(
            template_name='account/registration_complete.html'),
        name='registration_complete'),

    #openid registration
    url(r'^openid_signup/$',
        auth2_views.register_openid,
        {'template_name': 'auth/registration_form.html'},
        name='auth_register_openid'),
    url(r'^openid_login/complete$',
        auth2_views.openid_login_complete,
        name='auth_openid_login_complete'),
    #openid management
    url(r'^openid/$',
        auth2_views.changeopenid,
        name='auth_change_openid'),
    url(r'^openid/remove/$',
        auth2_views.removeopenid,
        name='auth_remove_openid'),

    #login/logout
    url(r'^login/$',
        auth2_views.login,
        {'template_name': 'auth/login.html'},
        name='auth_login'),
    url(r'^logout/$',
        auth2_views.logout,
        name='auth_logout'),

    url(r'^forgotusername/$',
        auth2_views.forget_username,
        name='auth_forget_username'),
    url(r'^forgotusername/done/$',
        auth2_views.forget_username_done,
        name='auth_forget_username_done'),

    #account edit
    url(r'^account/edit/$',
        auth2_views.edit_userinfo,
        name='auth_userinfo_edit'),
    url(r'^account/edit/done/$',
        auth2_views.edit_userinfo_done,
        name='auth_userinfo_edit_done'),

    #ajax requests
    url(r'^getuserdata$',
        auth2_views.getuserdata,
        name='auth_getuserdata'),
    url(r'^saveprofile$',
        auth2_views.save_uiprofile,
        name='auth_saveprofile'),

    url(r'^password/reset/$',
        auth2_views.password_reset,
        name='auth_password_reset'),
    url(r'^password/change/$',
        auth2_views.password_change,
        name='auth_password_change'),
]

urlpatterns += [
    # Registration
    # url(r'^signup/$',
    #     account_views.registration,
    #     name='auth_register'),
    # url(r'^activation/required/$',
    #     TemplateView.as_view(
    #         template_name='account/activation_required.html'),
    #     name='activation_required'),
    # url(r'^signup/complete/$',
    #     TemplateView.as_view(
    #         template_name='account/registration_complete.html'),
    #     name='registration_complete'),

    # Password management
    # url(r'^password/reset/$',
    #     account_views.password_reset,
    #     name='auth_password_reset'),
    # url(r'^password/change/$',
    #     account_views.password_change,
    #     name='auth_password_change'),

    url(r"^password/change/done/$",
        auth2_views.password_change_done,
        name="auth_password_change_done"),
    url(r"^email/change/$",
        auth2_views.email_change,
        name="auth_email_change"),
    url(r'^email/change/done/$',
        auth2_views.email_change_done,
        name='auth_email_change_done'),
]
