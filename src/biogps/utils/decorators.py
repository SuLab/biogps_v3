from functools import wraps
from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.http import urlquote
from .http import json_error


ANONYMOUS_USER_ERROR = 'Login required for accessing this service.'


def loginrequired(fn):
    '''if used, will return an error for annoymous user.

       If the request is an ajax one:
           @return: {'success': false,
                     'error': <standard_anonymous_user_error>,
                     'redirct_to': '/goto/here'}
           returned status code will be 403
       or a normal page request:
          @return 302 redirect.
    '''
    @wraps(fn)
    def check_usr(*args, **kwargs):
        request = None
        if len(args) > 0 and isinstance(args[0], HttpRequest):
            request = args[0]
        elif len(args) > 1 and isinstance(args[1], HttpRequest):
            request = args[1]
        if hasattr(request, 'user') and request.user.is_anonymous():
            login_url = settings.LOGIN_URL
#            path = urlquote(request.get_full_path())   # this is the full path
            path = urlquote(request.path)     # this is the relative path
            if request.is_ajax():
                return json_error(ANONYMOUS_USER_ERROR,
                                  status=403,
                                  redirect_to='%s?next=%s' % (login_url, path))
            else:
                return HttpResponseRedirect('%s?next=%s' % (login_url, path))
        else:
            return fn(*args, **kwargs)
    return check_usr

#This is deprecated now
# def loginrequired_or_redirect(fn):
#    '''if used, will redirect to login page for annoymous user.'''
#    @wraps(fn)
#    def check_usr(*args, **kwargs):
#        request = args[0]
#        if request.user.is_anonymous():
#            login_url = settings.LOGIN_URL
#            path = urlquote(request.get_full_path())
#            return HttpResponseRedirect('%s?next=%s' % (login_url, path))
#        else:
#            return fn(*args, **kwargs)
#    return check_usr

##Modified from django_authopenid.views.not_authenticated
def not_authenticated(func):
    """ decorator that redirect user to next page if
    he is already logged."""
    def decorated(request, *args, **kwargs):
        if request.user.is_authenticated():
            next = request.GET.get("next", None)
            if not next:
                next = "/"
            return HttpResponseRedirect(next)
        return func(request, *args, **kwargs)
    return decorated
