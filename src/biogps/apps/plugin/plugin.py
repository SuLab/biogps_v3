import re
from django.db.models import F
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.serializers import serialize, get_serializer_formats
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.loader import render_to_string
from django.utils.encoding import smart_text
from django.utils.html import escape
from django.conf import settings

from biogps.utils import log, is_valid_geneid, setObjectPermission
from biogps.utils.const import MIMETYPE, STD_FORMAT, ExtError, AVAILABLE_SPECIES
from biogps.utils.http import allowedrequestmethod, loginrequired, JSONResponse
from .models import BiogpsPlugin, BiogpsPluginPopularity, PluginUrlRenderError

from tagging.models import Tag, TaggedItem
from tagging.utils import calculate_cloud
from biogps.apps.gene.boe import MyGeneInfo


#@loginrequired
def plugin(request, query=None):
    """
    https://biogps-dev.gnf.org/plugin_v1/159/
    https://biogps-dev.gnf.org/plugin_v1/1-5/
    https://biogps-dev.gnf.org/plugin_v1/1,10,24/
    https://biogps-dev.gnf.org/plugin_v1/all/
    https://biogps-dev.gnf.org/plugin_v1/?start=0&limit=20&scope=all&sort=created&dir=DESC
    https://biogps-dev.gnf.org/plugin_v1/?start=0&limit=20&scope=shared&sort=created&dir=DESC&search=ncbi+gene
    https://biogps-dev.gnf.org/plugin_v1/?start=0&limit=20&scope=shared&sort=created&dir=DESC&tags=ncbi+gene

    sortable fields: author, created, lastmodified, title, type, url, popularity
    searchable fields: author, url, description, type, tags
    """
    sortable_fields = ['author', 'created', 'lastmodified', 'title', 'type', 'url', 'popularity']

    if request.method == 'GET':
        sort_order = smart_text(request.GET.get('dir', 'DESC'))
        sort_by = smart_text(request.GET.get('mysort', 'lastmodified')).strip().lower()
        if sort_by not in sortable_fields:
            return HttpResponseBadRequest('unknown "sort" field "%s".' % escape(sort_by))
        if sort_by == 'popularity':
            sort_by = 'popularity__score'
        sort_order = sort_order.strip()
        sort_by = sort_by.strip()
        if sort_order.upper() == 'DESC':
            sort_by = '-' + sort_by
        scope = smart_text(request.GET.get('scope', 'all')).lower()

        if scope == 'my':
            #_dbobjects = BiogpsPlugin.objects.filter(authorid=request.adamuser.sid)
            #_dbobjects = get_my_plugins(request.adamuser)
            _dbobjects = get_my_plugins(request.user)
        elif scope == 'shared':
            _dbobjects = get_shared_plugins(request.user)
        else:
            #scope == 'all':
            _dbobjects = get_my_plugins(request.user) | get_shared_plugins(request.user)

        if request.GET.has_key('search'):
            #search_term_li = re.split('\s+', smart_text(request.GET['search']).strip().replace("'",r"\'"))
            search_string = smart_text(re.sub('[^\w-]', ' ', request.GET['search'])).strip()
            search_term_li = re.split('\s+', search_string)
            _searchquery = eval(' & '.join(['(%s)' % q for q in [' | '.join(["Q(%s__icontains='%s')" % (field, term) for field in ['title', 'url', 'description', 'type', 'author']]) for term in search_term_li]]))
            #_dbobjects = _dbobjects.order_by(sort_by).filter(_searchquery)
            _dbobjects = (_dbobjects.filter(_searchquery) | \
                          TaggedItem.objects.get_union_by_model(_dbobjects,
                                                                Tag.objects.filter(name__in=search_term_li))) \
                         .order_by(sort_by, 'pk')   # add secondary sorting by pk to avoid unexpected order in case of ties
                         #.filter(_searchquery).order_by(sort_by, 'pk')   # add secondary sorting by pk to avoid unexpected order in case of ties

        if request.GET.has_key('tags'):
            _tags = re.split('\s+', smart_text(request.GET['tags']).strip())
            tags = Tag.objects.filter(name__in=_tags)
            _dbobjects = TaggedItem.objects.get_union_by_model(_dbobjects, tags)

        else:
            #_dbobjects = BiogpsPlugin.objects.order_by(sort_by)
            _dbobjects = _dbobjects.order_by(sort_by, 'pk')   # add secondary sorting by pk to avoid unexpected order in case of ties

        if sort_by.endswith('popularity__score'):
            _dbobjects = _dbobjects.filter(popularity__score__isnull=False)

        if request.GET.has_key('q'):
            query = smart_text(request.GET['q'])
        elif request.GET.has_key('query'):
            query = smart_text(request.GET['query'])
        if query:
            query = query.strip()
            if query.lower() == 'all':
                #query_result = getall(request.adamuser)
                query_result = _dbobjects
            else:
                if query.find(',') != -1:
                    plugin_id = [x.strip() for x in query.split(',')]
                    for x in plugin_id:
                        if not x.isdigit():
                            return HttpResponseBadRequest('Invalid input parameters "%s".' % escape(query))

                elif query.find('-') != -1:
                    try:
                        start, end = [int(x) for x in query.split('-')][:2]
                    except ValueError:
                        return HttpResponseBadRequest('Invalid input parameters "%s".' % escape(query))
                    plugin_id = [str(x) for x in range(start, end + 1)]
                elif query.isdigit():
                    plugin_id = [query]
                else:
                    return HttpResponseBadRequest('Invalid input parameters "%s".' % escape(query))
                query_result = _dbobjects.filter(pk__in=plugin_id)
            #query_total_cnt = len(query_result)
            query_total_cnt = query_result.count()

        elif request.GET.has_key('start'):
            start = request.GET['start']
            limit = request.GET.get('limit', _dbobjects.count())
            start = int(start)
            limit = int(limit)
            #query_result = BiogpsPlugin.objects.order_by(sort_by)[start:start+limit]
            query_result = _dbobjects[start:start + limit]
            query_total_cnt = _dbobjects.count()

        elif request.GET.has_key('search'):
            #in case that only query parameter is used.
            query_result = _dbobjects
            query_total_cnt = _dbobjects.count()

        else:
            return HttpResponseBadRequest('Missing required parameter.')

        # Append extra attributes to each object, to be passed down in the JSON stream.
        for p in query_result:
            p.author = p.owner.get_valid_name()        # although plugin object has author field, but here we get author name from user table on the fly
            p.author_url = p.owner.get_absolute_url()
            p.is_shared = (p.owner != request.user)
            p.usage_percent = p.usage_percent()
            p.usage_layout_count = p.popularity.score
            p.usage_ranking = p.popularity.rank
            p.usage_users = p.popularity.users_count
            p.related_plugins = p.popularity.related_plugins

        extra_itemfields = ['author', 'author_url', 'is_shared', 'usage_percent', 'usage_percent', 'usage_layout_count', 'usage_ranking', 'usage_users', 'related_plugins']

        format = request.GET.get('format', 'json')
        if format not in get_serializer_formats():
            format = 'json'
        if format == 'json':
            #using specialized jsonserializer
            return HttpResponse(serialize('myjson', query_result, extra_fields={'totalCount': query_total_cnt}, extra_itemfields=extra_itemfields), content_type=MIMETYPE.get(format, None))
        else:
            return HttpResponse(serialize(STD_FORMAT.get(format, format), query_result), content_type=MIMETYPE.get(format, None))
        #return HttpResponse(serialize(STD_FORMAT.get(format, format), query_result),content_type=MIMETYPE.get(format, None))

    elif request.method == 'POST':
        if query == 'add':
            return _plugin_add(request)
        elif query == 'update':
            return _plugin_update(request)
        elif query == 'delete':
            return _plugin_delete(request)
        else:
            return HttpResponseBadRequest('Unsupported action "%s"' % escape(query))

    elif request.method == 'PUT':
        #update a record
        pass

    elif request.method == 'DELETE':
        pass

    else:
        return HttpResponseBadRequest('Unsupported request method "%s"' % request.method)


@loginrequired
def plugin_usage(request, pluginid):
    '''return a list of layout using input plugin. Only avaialble for user's own plugin.'''
    try:
        plugin = request.user.myplugins.get(id=pluginid)
    except BiogpsPlugin.DoesNotExist:
        return ExtError("Plugin does not exist or not belong to you.")
    return JSONResponse(plugin.usage_count(request.user))


def get_my_plugins(user):
    #query_result = BiogpsPlugin.objects.filter(authorid=adamuser.sid)
    if user.is_anonymous():
        return BiogpsPlugin.objects.none()
    else:
        #query_result = BiogpsPlugin.objects.get_mine(authorid=adamuser.sid)
        query_result = user.myplugins.all()
        for x in query_result:
            x.is_my_plugin = True
        return query_result


def get_shared_plugins(user):
    query_result = BiogpsPlugin.objects.get_available(user, excludemine=True)
    return query_result


def _process_options_parameters(params):
    """pre-process options parameters from passed QueryDict."""

    options = {}
#    securityaware = params.get('securityaware', False)               #####temp disable#####
#    if securityaware:
#        options['securityAware']= True
    speciesonly = params.get('speciesonly', 'none').lower()
    if speciesonly in AVAILABLE_SPECIES:
        options['speciesonly'] = speciesonly

    _allowedspecies = params.getlist('allowedspecies')
    _allowedspecies = [species.lower() for species in _allowedspecies]
    allowedspecies = []
    for species in AVAILABLE_SPECIES:
        if species in _allowedspecies:
            allowedspecies.append(species)
    if len(allowedspecies) > 0 and sorted(allowedspecies) != sorted(AVAILABLE_SPECIES):
        options['allowedSpecies'] = allowedspecies

    return options if options else None


def _plugin_add(request, sendemail=True):
    '''
    If sendemail is True, an notification email will be sent out for every new plugin added.
    '''
    url = smart_text(request.POST['url'].strip())
    title = smart_text(request.POST['title'].strip())
    type = smart_text(request.POST.get('type', 'iframe'))
    description = smart_text(request.POST.get('description', ''))
    options = _process_options_parameters(request.POST)
    rolepermission = request.POST.get('rolepermission', None)
    userpermission = request.POST.get('userpermission', None)
    tags = request.POST.get('tags', None)

    #flag to allow save duplicated (same url, type, options) plugin
    allowdup = (request.POST.get('allowdup', None) == '1')

#    exist_plugins = BiogpsPlugin.objects.filter(title = title,
#                                                url = url,
#                                                type = type,
#                                                #authorid = authorid,
#                                                ownerprofile__sid = ownerprofile.sid,
#                                                author = author,
#                                                #options=options,
#                                                description = description)

    if not allowdup:
        all_plugins = request.user.myplugins.all() | get_shared_plugins(request.user)
#        dup_plugins = all_plugins.filter(url = url,
#                                         type = type,
#                                         options=options)
        dup_plugins = all_plugins.filter(url=url)

        if dup_plugins.count() > 0:
            data = {'success': False,
                    'dup_plugins': [dict(id=p.id, text=smart_text(p)) for p in dup_plugins],
                    'error': 'Duplicated plugin exists!'}
            return JSONResponse(data)

#    exist_plugins = request.user.myplugins.filter(title = title,
#                                                  url = url,
#                                                  type = type,
#                                                  #options=options,
#                                                  description = description)
#
#    if exist_plugins.count() > 0:
#        data = {'success': False,
#                'error': 'Identical plugin exists!'}
#    else:
    plugin = BiogpsPlugin(title=title,
                          url=url,
                          type=type,
                          ownerprofile=request.user.profile,
                          description=description)
    if options:
        plugin.options = options
    plugin.save()
    if rolepermission or userpermission:
        setObjectPermission(plugin, rolepermission, userpermission, sep=',')

    if tags is not None:
        plugin.tags = smart_text(tags)

    #create an entry on popularity table
    BiogpsPluginPopularity.objects.get_or_create(plugin=plugin, score=0)

    #logging plugin add
    log.info('username=%s clientip=%s action=plugin_add id=%s',
             getattr(request.user, 'username', ''),
             request.META.get('REMOTE_ADDR', ''),
             plugin.id)

    if not settings.DEBUG and sendemail:
        #send email notification
        from biogps.utils.http import mail_managers_in_html
        current_site = Site.objects.get_current()
        subject = 'New Plugin "%s" by %s' % (plugin.title, plugin.author)
        message = render_to_string('plugin/newplugin_notification.html', {'p': plugin, 'site': current_site})
        mail_managers_in_html(subject, message, fail_silently=True)

    data = {'success': True,
            'plugin_id': plugin.id}
    return JSONResponse(data)


@loginrequired
def _plugin_update(request):
    plugin_id = smart_text(request.POST['plugin_id'])
    rolepermission = request.POST.get('rolepermission', None)
    userpermission = request.POST.get('userpermission', None)
    options = _process_options_parameters(request.POST)
    tags = request.POST.get('tags', None)
    params = request.POST

    updatable_fields = ['title', 'url', 'description']
    try:
        plugin = request.user.myplugins.get(id=plugin_id)
        for f in updatable_fields:
            if f in params:
                setattr(plugin, f, smart_text(params[f].strip()))

        if not plugin.options:
            if options:
                plugin.options = options
        else:
            if options:
                plugin.options.update(options)
            else:
                #plugin.options is not None and options is None
                #always clean-up allowedspecies field
                if plugin.options.has_key('allowedSpecies'):
                    del plugin.options['allowedSpecies']

        plugin.save()

        if rolepermission or userpermission:
            setObjectPermission(plugin, rolepermission, userpermission, sep=',')

        if tags is not None:
            plugin.tags = smart_text(tags)

        data = {'success': True}

    except BiogpsPlugin.DoesNotExist:
        data = {'success': False,
                'error': "Plugin does not exist or not belong to you."}

    return JSONResponse(data)


@loginrequired
def _plugin_delete(request):
    plugin_id = request.POST['plugin_id']
    try:
        plugin = request.user.myplugins.get(id=plugin_id)
        plugin.delete()
        del plugin.permission

        #logging plugin delete
        log.info('username=%s clientip=%s action=plugin_delete id=%s',
                 getattr(request.user, 'username', ''),
                 request.META.get('REMOTE_ADDR', ''),
                 plugin_id)

        data = {'success': True}
    except BiogpsPlugin.DoesNotExist:
        data = {'success': False,
                'error': "Plugin does not exist or not belong to you."}

    return JSONResponse(data)


class PluginSearchForm(forms.Form):
    pluginquery = forms.CharField(max_length=100)


def pluginbrowser(request):

    if request.method == 'POST':
        #This form actually should not be submitted via POST. It is done by javascript function with AJAX call.
        #So this block of code will not be executed.
        form = PluginSearchForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect('/')
    else:
        _dbobjects = get_my_plugins(request.user) | get_shared_plugins(request.user)
        #get newest 10 plugins
        newest_plugin_list = _dbobjects.order_by('-created')[:10]
        #get recently updated 10 plugins
        #updated_plugin_list = _dbobjects.order_by('-lastmodified')[:10]
        updated_plugin_list = _dbobjects.exclude(created__gte=F('lastmodified')).order_by('-lastmodified')[:10]
                                                       #^^^^^when a new plugin is saved, "created" is slightly newer than "lastmodified"
        popular_plugin_list = _dbobjects.filter(popularity__score__isnull=False).order_by('-popularity__score')[:10]
        form = PluginSearchForm()

        plugin_tags = calculate_cloud(Tag.objects.usage_for_queryset(_dbobjects, counts=True, min_count=2))

        d = {'form': form,
             'newest_plist': newest_plugin_list,
             'updated_plist': updated_plugin_list,
             'popular_plist': popular_plugin_list,
             'anonymous_user': request.user.is_anonymous(),
             'plugin_tags': plugin_tags,
            }
        return render_to_response('plugin/pluginlibrary.html', d)
