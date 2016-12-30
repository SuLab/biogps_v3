'''
Modified based on http://djangosnippets.org/snippets/2041/
It provides a class-based view
Usage example:

class MyView(View):
    def __init__(self, arg=None):
        self.arg = arg
    def get(request):
        return HttpResponse(self.arg or 'No args passed')

@login_required
class MyOtherView(View):
    def post(request):
        return HttpResponse()

# in urls.py
# And all the following work as expected.
urlpatterns = patterns(''
    url(r'^myview1$', 'myapp.views.MyView', name='myview1'),
    url(r'^myview2$', myapp.views.MyView, name='myview2'),
    url(r'^myview3$', myapp.views.MyView('foobar'), name='myview3'),
    url(r'^myotherview$', 'myapp.views.MyOtherView', name='otherview'),
)

'''
from django.http import HttpRequest, HttpResponseNotAllowed

def _load_put_and_files(request):
    """
    This is taken from "django-rest-interface".
    Ref http://code.google.com/p/django-rest-interface/source/browse/trunk/django_restapi/resource.py

    Populates request.PUT and request.FILES from
    request.raw_post_data. PUT and POST requests differ
    only in REQUEST_METHOD, not in the way data is encoded.
    Therefore we can use Django's POST data retrieval method
    for PUT.
    """
    if request.method == 'PUT':
        request.method = 'POST'
        request._load_post_and_files()
        request.PUT = request.POST
        request.method = 'PUT'


class _CallableViewClass(type):
    def __new__(cls, name, bases, dct):
#        if 'HEAD' not in dct and 'GET' in dct:
#            # XXX: this function could possibly be moved out
#            # to the global namespace to save memory.
#            def HEAD(self, request, *args, **kwargs):
#                response = self.GET(request, *args, **kwargs)
#                response.content = u''
#                return response
#            dct['HEAD'] = HEAD

        dct['permitted_methods'] = []
        for method in ('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'CONNECT', 'TRACE'):
            if hasattr(dct.get(method.lower(), None), '__call__'):
                dct['permitted_methods'].append(method)

        return type.__new__(cls, name, bases, dct)

    def __call__(cls, *args, **kwargs):
        if args and isinstance(args[0], HttpRequest):
            instance = super(_CallableViewClass, cls).__call__()
            return instance.__call__(*args, **kwargs)
        else:
            instance = super(_CallableViewClass, cls).__call__(*args, **kwargs)
            return instance


class RestView(object):
    __metaclass__ = _CallableViewClass

    def __call__(self, request, *args, **kwargs):
        if request.method in self.permitted_methods:
            handler = getattr(self, request.method.lower())
            if request.method == 'PUT':
                _load_put_and_files(request)

            # XXX: Could possibly check if 'before' returns a response
            # and return that instead.
            self.before(request, args, kwargs)
            return handler(request, *args, **kwargs)

        return HttpResponseNotAllowed(self.permitted_methods)

    def before(self, request, args, kwargs):
        """Override this method to add common functionality to all HTTP method handlers.

        args and kwargs are passed as regular arguments so you can add/remove arguments:
            def before(self, request, args, kwargs):
                kwargs['article'] = get_object_or_404(Article, id=kwargs.pop('article_id')
            def get(self, request, article): # <== 'article' instead of 'article_id'
                ...
            def post(delf, request, article): # <== 'article' instead of 'article_id'
                ...
        """
        pass
