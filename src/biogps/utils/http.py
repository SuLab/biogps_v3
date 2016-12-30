'''
This module provides useful utilitis and shortcuts for anything HttpResponse,
HttpRequest related. They are often used in view functions/classes
'''
import sys
import json
from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseBadRequest, HttpRequest
from django.utils import timezone
from django.utils.http import urlquote
from django.template.base import RequestContext
from django.shortcuts import render_to_response as raw_render_to_response
from django.core.paginator import Paginator, EmptyPage
from django.contrib.sites.models import Site

from rest_framework.response import Response

from biogps.utils.model_serializer import serialize

from .const import (AVAILABLE_SPECIES, MIMETYPE, ANONYMOUS_USER_ERROR,
                    MAX_QUERY_LENGTH, sample_gene)


def JSONResponse(pyobj, do_not_encode=False, **kwargs):
    '''Return a JSON serialized HttpRespone.
       if do_not_encode is True, assuming pyobj is already a JSON string, and
        just return it as it is.
       if "jsonp" is passed as a string, wrap json response in a jsonp callback.
    '''
    _json = json.dumps(pyobj) if not do_not_encode else pyobj
    jsonp = kwargs.pop('jsonp', None)
    if jsonp:
        _json = "{}({})".format(jsonp, _json)
    return HttpResponse(_json,
                        content_type='application/json; charset=%s' % settings.DEFAULT_CHARSET, **kwargs)


def TextResponse(string='', **kwargs):
    return HttpResponse(string,
                        content_type='text/plain; charset=%s' % settings.DEFAULT_CHARSET, **kwargs)


def XMLResponse(xmldata, **kwargs):
    return HttpResponse(xmldata,
                        content_type='text/xml; charset=%s' % settings.DEFAULT_CHARSET, **kwargs)


def api_error(errmsg, **kwargs):
    '''Return a standard Json-ized dictionary with given errmsg:
        @return: {'success': false,
                  'error': "there is an error here."}

        @param errmsg: actual error msg.
        @param status: given a different status code if needed.
        @param extra: anything passed in extra will be included in returned
                      dictionary.
                      E.g., json_error('error', redirect_to='/goto/here') will
                         returns {'success': false,
                                  'error':   'error',
                                  'redirect_to': '/goto/here'}

    '''
    error = {'success': False,
             'error': errmsg}
    return Response(error, **kwargs)

APIError = api_error
json_error = api_error

def biogpsError(errmsg, format='html'):
    '''if formate is 'html', return a full html page for errmsg using biogps_error.html template;
       if format is 'json', returns a Json-ized dictionary favored by EXTJS with given errmsg.'''
    if format.lower() == 'json':
        return api_error(errmsg)
    else:
        return render_to_response('biogps_error.html', {'title': 'Error', 'errmsg': errmsg})


class UnSupportedFormat(Exception):
    '''Raise this if passed format is not in the SUPPORTED_FORMATS list.'''


class FormattedResponse():
    '''
    This is a helper class to return specific HttpResponse instance based on
    requested format. The typical usage is via L{render_to_formatted_response}
    shortcut function:

        def your_view(request):
            return render_to_formatted_response(request, data,
                                                allowed_formats=['json', 'xml'])

    '''
    SUPPORTED_FORMATS = ['html', 'json', 'xml']     # The order of this list
                                                    # defines the priority.

    def __init__(self, request,
                 data=None,
                 serialize_attrs=None,
                 model_serializer=None,
                 model_serializer_kwargs={},
                 html_template=None,
                 html_dictionary={},
                 html_skip_context=False,
                 allowed_formats=['html', 'json', 'xml'],
                 default_format='html',
                 pagination_by=None):
        '''
        @param request: HttpRequest instance
        @param data: any python object to be serialized.
                    if data is a list/tuple of B{Model instance} or a single B{Model instance},
                    "serialize_attrs" parameter can be used to specify the attributes in the output.
                    if data is other type, it is output as it is.
                    Pagination of data is supported by page query parameter.
        @param serialize_attrs: list of attributes from B{Model instance} need to be serialized
                                (it can be a method with no extra arguments but self)
        @param model_serializer: can be used to pass a custom serializer:
                                    1. a method name of the passed B{Model instance}
                                    2. a standalone function with the B{Model instance} as the first argument
                                 Note that when model_serializer is passed, parameter "serialize_attrs" is ignored.
        @param model_serializer_kwargs: the extra keyword paramters can be passed when model_serializer
                                          is called.
        @param html_template:  template file to render html page, passed to render_to_response
        @param html_dictionary: dictionary passed to render_to_response
        @param html_skip_context: if False(default), a context_instance is always passed to render_to_response
        @param allowed_formats: a list of allowed formats
        @param default_format: the default format if format is not requested.
        @param pagination_by: None: no pagination; an integer, the pagination size.
        '''
        self._request = request
        self._data = data
        self.serialize_attrs = serialize_attrs
        self.model_serializer = model_serializer
        self.model_serializer_kwargs = model_serializer_kwargs
        self.html_template = html_template
        self.html_dictionary = html_dictionary
        self.html_skip_context = html_skip_context
        self.pagination_by = pagination_by      # default page size for pagination if not None.
                                                # for html rendering, pagination is handled in
                                                # template by autopagination tag, so the
                                                # self.pagination_by settings here should be
                                                # consistent with the autopagination setting in
                                                # template files (e.g. dataset/list.html, plugin/list.html)

        if default_format not in self.SUPPORTED_FORMATS:
            raise UnSupportedFormat
        else:
            self.default_format = default_format

        for f in allowed_formats:
            if f not in self.SUPPORTED_FORMATS:
                raise UnSupportedFormat
        self.allowed_formats = allowed_formats

    def get_format(self, request):
        '''Get requested format based on:
             1. passed "format" URL parameter (via GET)
             2. passed "accept" header
        '''
        format = self._get_format_by_urlparam(request) or \
                 self._get_format_by_header(request) or \
                 self.default_format
        return format

    def _get_format_by_header(self, request):
        '''Get requested format based on passed "accept" header.
           Return None if none is matched.
        '''
        http_accept_header = request.META.get('HTTP_ACCEPT', '')
        # Special handling for IE's completely bizarre behavior
        if http_accept_header.find('application/xaml+xml') != -1:
            return self.SUPPORTED_FORMATS[0]

        format = None
        for fmt in self.SUPPORTED_FORMATS:
            if http_accept_header.find(fmt) != -1:
                format = fmt
                break
        return format

    def _get_format_by_urlparam(self, request):
        '''Get requested format based on passed "format" URL parameter.
           Return None if no such parameter or passed value is not supported.
        '''
        rm = request.GET if request.method == 'GET' else request.POST
        format = rm.get('format', '').lower().strip()
        if format not in self.SUPPORTED_FORMATS:
            format = None
        return format

    def render(self):
        '''returns actual HttpReponse instance based on requested format.'''
        format = self.get_format(self._request)

        if format not in self.allowed_formats:
            return HttpResponseNotAllowed(self.allowed_formats)
        elif format in ['json', 'xml']:
            #if isinstance(self._data, (list, QuerySet, BiogpsSearchResult)):
            if self.pagination_by:
                # if self._data is one of these types,
                # handling pagination here when "page" parameter is passed.
                # no need for html rendering, as it will be handle by autopagination
                # tag in the template.
                paginator = Paginator(self._data, self.pagination_by)
                # self._request.page is available when
                # pagination.middleware.PaginationMiddleware is used
                try:
                    _data = paginator.page(self._request.page).object_list
                except EmptyPage:
                    _data = []
            else:
                _data = self._data
            response = HttpResponse(serialize(_data,
                                              format=format,
                                              attrs=self.serialize_attrs,
                                              model_serializer=self.model_serializer,
                                              **self.model_serializer_kwargs),
                                    content_type=MIMETYPE.get(format, None))
            if format == 'json':
                #handle jsonp callback case
                jsonp_callback = self._request.GET.get('callback', '')
                if jsonp_callback:
                    response.content = '%s(%s)' % (jsonp_callback, response.content)
            return response

        elif format == 'html':
            if self.html_skip_context:
                context = None
            else:
                if settings.DEBUG:
                    from django.template.context_processors import request as request_processor
                    context = RequestContext(self._request, {}, (request_processor,))
                else:
                    context = RequestContext(self._request)
#                #always add django_compress to the context
#                #the value is based on compress.conf.settings.COMPRESS
#                context['django_compress'] = getattr(settings, 'COMPRESS', not settings.DEBUG)

                # add get_vars for use in passing on search parameters to JSON and XML links
                # this logic is adapted from django-pagination
                # getvars = context['request'].GET.copy()
                getvars = context.request.GET.copy()
                if len(getvars.keys()) > 0:
                    context['getvars'] = "&%s" % getvars.urlencode()
                else:
                    context['getvars'] = ''

#                # add the full path as a variable for use with the login/logout links
#                context['full_path'] = context['request'].path_info
#                if context['getvars']:
#                    context['full_path'] += '?' + context['getvars']

#                # set the maximum search query length
#                context['max_query_length'] = settings.ES_MAX_QUERY_LENGTH

                # set alternate formats based on what has been allowed
                if len(self.allowed_formats) > 1:
                    # remove the HTML format but keep the rest
                    context['alternate_formats'] = [af for af in self.allowed_formats if af != 'html']
            return raw_render_to_response(self.html_template,
                                          self.html_dictionary,
                                          context_instance=context)


def render_to_formatted_response(*args, **kwargs):
    """
    A shortcut to return a HttpResponse using L{FormattedResponse} helper class.
    See FormattedResponse for parameter details.
    """
    formatted_instance = FormattedResponse(*args, **kwargs)
    return formatted_instance.render()


def render_to_response(request, *args, **kwargs):
    '''A modified version of render_to_response with request always the first
       argument and the requestcontext is always passed.
    '''
    context = RequestContext(request)
    kwargs.setdefault('context_instance', context)
    return raw_render_to_response(*args, **kwargs)


def _get_traceback(self, exc_info=None):
    "Helper function to return the traceback as a string"
    import traceback
    return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))


def email_admin_last_exception(request):
    """
    Email admin about the exception just caught. It's useful when we need to
    catch an exception nicely but still want to send admin an email about it.
    Email code were taken from django.core.handlers.base.BaseHandler.
    handle_uncaught_exception.

    Usage example (normally in a view):
                try:
                     raise ValueError
                except ValueError:
                     email_admin_last_exception(request)
                     return <some nicer response>
    """
    from django.core.mail import mail_admins

    exc_info = sys.exc_info()

    if settings.DEBUG_PROPAGATE_EXCEPTIONS:
        raise

    if settings.DEBUG:
        from django.views import debug
        return debug.technical_500_response(request, *exc_info)

    # When DEBUG is False, send an error message to the admins.
    subject = 'Error (%s IP): %s' % ((request.META.get('REMOTE_ADDR') in settings.INTERNAL_IPS and 'internal' or 'EXTERNAL'), request.path)
    try:
        request_repr = repr(request)
    except:
        request_repr = "Request repr() unavailable"

    message = "%s\n\n%s" % (_get_traceback(exc_info), request_repr)
    mail_admins(subject, message, fail_silently=True)


def getCommonDataForMain(request):
    if request.META.get('HTTP_HOST', '').startswith('ec2'):  # in case of dev site from ec2
        current_site = request.META['HTTP_HOST']             # This allows login form on main page, index_ext.html, work for biogps-stage/biogps-trunk server.
    else:
        current_site = Site.objects.get_current()
    user_type = request.user.account_type() if request.user.is_authenticated() else "Anonymous"
    with_https = getattr(settings, 'WITH_HTTPS', False)

    #available_species
    default_org = request.GET.get('org', 'human').lower()
    if default_org in AVAILABLE_SPECIES and default_org != AVAILABLE_SPECIES[0]:
        idx = AVAILABLE_SPECIES.index(default_org)
        available_species = [default_org] + AVAILABLE_SPECIES[:idx]+AVAILABLE_SPECIES[idx+1:]
    else:
        available_species = AVAILABLE_SPECIES

    d = dict(user_type=user_type,
             site=current_site,
             with_https=with_https,
             max_query_len=MAX_QUERY_LENGTH,
             available_species=json.dumps(available_species),
             sample_gene=json.dumps(sample_gene))

    return d


def isRobot(request):
    '''return True if request's HTTP_USER_AGENT indicates it's from a specified web crawler.
       Possible string it looks for is defined in settings.BOT_HTTP_USER_AGENT.
    '''
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    for s in settings.BOT_HTTP_USER_AGENT:
        if user_agent.find(s) != -1:
            return True
    return False

def isIE(request):
    '''return True if request is from IE.'''
    return request.META.get('HTTP_USER_AGENT', '').find('MSIE') != -1

# def HttpResponseRedirectWithIEFix(request, url):
#     '''To fix an obscure IE bug when url contains hash string,
#        Ref: http://www.michiknows.com/2007/06/06/ie-redirect-bug-with-dynamic-location-hash/
#     '''
#     if isIE(request):
#         return HttpResponse('<script>document.location.href = "%s"</script>' % url)
#     else:
#         return HttpResponseRedirect(url)

def set_domain_cookie(request, response):
    '''This is to set a "gnf.org" domain cookie used by security-aware plugins.'''
    max_age = settings.SESSION_COOKIE_AGE
    expires = timezone.datetime.strftime(timezone.datetime.utcnow() + timezone.timedelta(seconds=settings.SESSION_COOKIE_AGE), "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie('secure_plugin_client_session', request.session.session_key,
                        max_age=max_age, expires=expires,
                        domain='biogps.org',
                        secure=False)   # settings.SESSION_COOKIE_SECURE or None)
    return response

def is_dev_server(request):
    '''return True is server is running under django's dev server.'''
#    server_string = request.META.get('SERVER_SOFTWARE', '')
#    return server_string.startswith('WSGIServer')
    server_string = request.META.get('SERVER_SOFTWARE', '')
    return not server_string.startswith('Apache')


def mail_managers_in_html(subject, message, fail_silently=False):
    """Sends a message to the managers, as defined by the MANAGERS setting.
       passed message is a html document.
    """
    from django.core.mail import EmailMessage
    msg = EmailMessage(settings.EMAIL_SUBJECT_PREFIX + subject, message,
                       settings.SERVER_EMAIL, [a[1] for a in settings.MANAGERS])
    msg.content_subtype = "html"
    msg.send(fail_silently=fail_silently)


# Decorators

def allowedrequestmethod(*allowedmethods):
    '''if used, will return an error for request.method not specified in allowedmethods argument.'''
    def decorator(fn):
        @wraps(fn)
        def check_method(*args, **kwargs):
            request = args[0]
            if request.method not in allowedmethods:
                return HttpResponseBadRequest('Unsupported request method "%s"' % request.method)
            else:
                return fn(*args, **kwargs)
        return check_method
    return decorator

def loginrequired(fn):
    '''if used, will return an error for annoymous user.'''
    @wraps(fn)
    def check_usr(*args, **kwargs):
        request = None
        if len(args) > 0 and isinstance(args[0], HttpRequest):
            request = args[0]
        elif len(args) > 1 and isinstance(args[1], HttpRequest):
            request = args[1]
        if hasattr(request, 'user') and request.user.is_anonymous():
            return HttpResponse(json.dumps(ANONYMOUS_USER_ERROR), content_type=MIMETYPE['json'])
        else:
            return fn(*args, **kwargs)
    return check_usr


def loginrequired_or_redirect(fn):
    '''if used, will redirect to login page for annoymous user.'''
    @wraps(fn)
    def check_usr(*args, **kwargs):
        request = args[0]
        if request.user.is_anonymous():
            login_url = settings.LOGIN_URL
            path = urlquote(request.get_full_path())
            return HttpResponseRedirect('%s?next=%s' % (login_url, path))
        else:
            return fn(*args, **kwargs)
    return check_usr


def openidrequired(fn):
    '''if used, will require an OpenID enabled account to access.
       Eg. the OpenID account editing page.
    '''
    @wraps(fn)
    def check_usr(*args, **kwargs):
        request = args[0]
        if request.user.is_authenticated() and not request.user.has_openid():
            errmsg = 'Your account must have OpenID enabled to access this page.'
            return biogpsError(errmsg, 'html')
        else:
            return fn(*args, **kwargs)
    return check_usr

# def docenabled(fn):
#     '''if used, the doc string will be displayed in /doc page'''
#     fn.docenabled = True
#     return fn

# End of decorators
