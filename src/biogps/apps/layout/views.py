import json
from django.db.models import Q
# from django.core.serializers import serialize, get_serializer_formats
from django.utils.encoding import smart_text, smart_str
from django.http import HttpResponse

from rest_framework.decorators import api_view
from rest_framework import viewsets
from rest_framework.response import Response

from biogps.apps.layout.models import BiogpsGenereportLayout
from biogps.apps.plugin.models import BiogpsPlugin

from biogps.utils import log, is_valid_geneid, formatDateTime, setObjectPermission, cvtPermission
from biogps.utils.http import APIError, JSONResponse
from biogps.utils.jsonserializer import Serializer as JSONSerializer
from biogps.apps.plugin.models import PluginUrlRenderError
from biogps.apps.gene.boe import MyGeneInfo


class LayoutViewSet(viewsets.ViewSet):

    def get_layout(self, request, query=None):
        """ /layout/1/
            /layout/3-9/
            /layout/1,3,5/
            optional querystrings:
                loadplugin: if true ("1" or "true"), load associated plugin data in returned layout data
        """
        if query:
            query = query.lower()
            try:
                if query.find(',') != -1:
                    layout_id = [int(x) for x in query.split(',')]
                elif query.find('-') != -1:
                    start, end = [int(x) for x in query.split('-')][:2]
                    layout_id = [str(x) for x in range(start, end + 1)]
                else:
                    layout_id = [int(query)]
            except ValueError:
                return APIError('Invalid input parameters!')

            query_result = BiogpsGenereportLayout.objects.filter(pk__in=layout_id)

            loadplugin = (request.query_params.get('loadplugin', '').lower() in ['1', 'true'])

            for layout in query_result:
                layout.author = layout.owner.get_valid_name()
                layout.is_shared = (layout.owner != request.user)
                layout.loadplugin = loadplugin
            extra_itemfields = ['author', 'is_shared', 'layout_data']
            query_total_cnt = query_result.count()

            #logging layout access
            log.info('username=%s clientip=%s action=layout_query id=%s',
                     getattr(request.user, 'username', ''),
                     request.META.get('REMOTE_ADDR', ''),
                     ','.join([str(layout.id) for layout in query_result]))

        else:
            return APIError('Missing required parameter.')

        data = JSONSerializer().serialize(query_result, extra_fields={'totalCount': query_total_cnt}, extra_itemfields=extra_itemfields)
        data = json.loads(data)
        return Response(data)
        # format = request.GET.get('format', 'json')
        # if format not in get_serializer_formats():
        #     format = 'json'
        # if format == 'json':
        #     return HttpResponse(serialize('myjson', query_result, extra_fields={'totalCount': query_total_cnt}, extra_itemfields=extra_itemfields), content_type=MIMETYPE.get(format, None))
        # else:
        #     return HttpResponse(serialize(STD_FORMAT.get(format, format), query_result), content_type=MIMETYPE.get(format, None))

    def add_layout(self, request):
        return _layout_add(request)

    def update_layout(self, request, layout_id):
        return _layout_update(request, layout_id)

    def delete_layout(self, request, layout_id):
        return _layout_delete(request)

    def get_my_layoutlist(self, request):
        """
        A simplified and much faster handler for layoutlist/all/ service.
        # URL: /layoutlist/all/
        URL: /layout/all/
        """
        user = request.user
        layout_qs = BiogpsGenereportLayout.objects.get_available(user, excludemine=True)
        layout_qs = layout_qs.order_by('-lastmodified')
        layout_list = list(layout_qs.values('pk', 'layout_name'))
        for i, layout in enumerate(layout_list):
            layout = {'pk': layout['pk'],
                      'fields': {'layout_name': layout['layout_name'],
                                 'is_shared': True}}
            layout_list[i] = layout

        if not user.is_anonymous():
            my_layout_list = user.mylayouts.order_by('-lastmodified').values('pk', 'layout_name')
            my_layout_list = list(my_layout_list)
            for i, layout in enumerate(my_layout_list):
                layout = {'pk': layout['pk'],
                          'fields': {'layout_name': layout['layout_name'],
                                     'is_shared': False}}
                my_layout_list[i] = layout
            layout_list += my_layout_list

        layout_output = {"totalCount": len(layout_list),
                         "items": layout_list}

        return Response(layout_output)

    def layoutlist(self, request, query='all'):
        """
        # URL: /layoutlist/all/?userselected=1
        #      /layoutlist/all/?scope=my
        #      /layoutlist/all/?scope=shared
        #      /layoutlist/?search=demo
        #      /layoutlist/?search=demo&start=20&limit=10

        URL: /layout/list/?userselected=1
             /layout/list/?scope=my
             /layout/list/?scope=shared
             /layout/list/?search=demo
             /layout/list/?search=demo&start=20&limit=10

        """

        sort_order = request.query_params.get('dir', 'DESC')
        sort_by = request.query_params.get('sort', 'lastmodified')
        sort_order = sort_order.strip()
        sort_by = sort_by.strip()
        if sort_order.upper() == 'DESC':
            sort_by = '-' + sort_by
        scope = request.query_params.get('scope', 'all').lower()

        # userselectedonly = (request.GET.get('userselected','') == '1')
        userselectedonly = False    # tmp fix here, so that all user can pick up whatever is available ###

        # First, get all available layouts based on scope
        if (request.user.is_anonymous()):
            _dbobjects = get_shared_layouts(request.user, userselectedonly=False)
        else:
            if scope == 'my':
                _dbobjects = get_my_layouts(request.user)
            elif scope == 'shared':
                _dbobjects = get_shared_layouts(request.user, userselectedonly)
            else:
                _dbobjects = getall(request.user, userselectedonly)

        # filter layouts based on search parameter
        if 'search' in request.query_params:
            search_term = request.query_params['search'].strip()
            _dbobjects = _dbobjects.order_by(sort_by).filter(Q(layout_name__icontains=search_term) |
                                                             Q(description__icontains=search_term) |
                                                             Q(author__icontains=search_term))

        else:
            _dbobjects = _dbobjects.order_by(sort_by)

        if 'q' in request.query_params:
            query = request.query_params['q']
        elif 'query' in request.query_params:
            query = request.query_params['query']
        if query:
            if query.lower() == 'all':
                query_result = _dbobjects
            else:
                try:
                    if query.find(',') != -1:
                        layout_id = [int(x) for x in query.split(',')]
                    elif query.find('-') != -1:
                        start, end = [int(x) for x in query.split('-')][:2]
                        layout_id = [str(x) for x in range(start, end + 1)]
                    else:
                        layout_id = [int(query)]
                except ValueError:
                    return APIError('Invalid input parameters!')

                query_result = _dbobjects.filter(pk__in=layout_id)
            query_total_cnt = query_result.count()

        elif 'start' in request.query_params:
            start = request.query_params['start']
            limit = request.query_params.get('limit', _dbobjects.count())
            start = int(start)
            limit = int(limit)
            query_result = _dbobjects[start:start + limit]
            query_total_cnt = _dbobjects.count()

        elif 'search' in request.query_params:
            # in case that only query parameter is used.
            query_result = _dbobjects
            query_total_cnt = _dbobjects.count()

        else:
            return APIError('Missing required parameter.')

        for layout in query_result:
            layout.author = layout.owner.get_valid_name()
            layout.is_shared = (layout.owner != request.user)
        extra_itemfields = ['author', 'is_shared', 'layout_data']

        data = JSONSerializer().serialize(query_result, extra_fields={'totalCount': query_total_cnt}, extra_itemfields=extra_itemfields)
        data = json.loads(data)
        return Response(data)
        # format = request.GET.get('format', 'json')
        # if format not in get_serializer_formats():
        #     format = 'json'
        # if format == 'json':
        #     #using specialized jsonserializer
        #     return HttpResponse(serialize('myjson', query_result, extra_fields={'totalCount': query_total_cnt}, extra_itemfields=extra_itemfields), content_type=MIMETYPE.get(format, None))
        # else:
        #     return HttpResponse(serialize(STD_FORMAT.get(format, format), query_result), content_type=MIMETYPE.get(format, None))


def get_my_layouts(user):
    if user.is_anonymous():
        return BiogpsGenereportLayout.objects.none()
    else:
        #query_result = BiogpsGenereportLayout.objects.get_mine(authorid=adamuser.sid)
        query_result = user.mylayouts.all()
        return query_result


def get_shared_layouts(user, userselectedonly=False):
    if not userselectedonly:
        #query_result = BiogpsGenereportLayout.objects.get_shared2(user)
        query_result = BiogpsGenereportLayout.objects.get_available(user, excludemine=True)
    else:
        shared_layouts = user.uiprofile.get('sharedlayouts', [])
        query_result = BiogpsGenereportLayout.objects.filter(id__in=shared_layouts).exclude(ownerprofile__sid=user.sid)

    return query_result


def getall(user, userselectedonly=False):
    """get all layouts available for given adamuser"""
    query_result = get_my_layouts(user) | get_shared_layouts(user, userselectedonly)
    return query_result


def getplugin(pid):
    plugin = {'id': pid}
    p = BiogpsPlugin.objects.get(pk=pid)
    for attr in ('title', 'url', 'type', 'author', 'description', 'lastmodified', 'options', 'created'):
        plugin[attr] = smart_str(getattr(p, attr))
    return plugin


def _layout_name_exists(layout_name, user):
    exist_layouts = user.mylayouts.filter(layout_name=layout_name)
    return exist_layouts.count() > 0


def _layout_add(request):
    layout_name = smart_text(request.data['layout_name'].strip())
    layout_data = request.data['layout_data']
    # permission = request.data.get('permission', '')
    description = smart_text(request.data.get('description', ''))

    if _layout_name_exists(layout_name, request.user):
        return APIError('Name conflicts with existed one!')

    else:
        layout = BiogpsGenereportLayout(layout_name=layout_name,
                                        ownerprofile=request.user.profile,
                                        description=description)

        try:
            layout.save()
            layout.layout_data = json.loads(layout_data)
        except ValueError:
            return APIError('Passed "layout_data" is not a valid json string.')

        # logging layout add
        log.info('username=%s clientip=%s action=layout_add id=%s',
                 getattr(request.user, 'username', ''),
                 request.META.get('REMOTE_ADDR', ''),
                 layout.id)
        data = {'success': True,
                'layout_id': layout.id}
    return Response(data)


def _layout_update(request):

    layout_id = request.POST.get('layout_id', None)
    if not layout_id:
        return APIError('Missing required parameter.')

    rolepermission = request.POST.get('rolepermission', None)
    params = request.POST
    updatable_fields = ['layout_name', 'layout_data', 'description']      # 'permission',

    try:
        layout = request.user.mylayouts.get(id=layout_id)
        for f in updatable_fields:
            if f in params:
                if (f == 'layout_name') and (params[f] != layout.layout_name) and (_layout_name_exists(params[f], request.user)):
                    return APIError('Name conflicts with existed one!')
                if (f == 'layout_data'):
                    try:
                        setattr(layout, f, json.loads(params[f]))
                    except ValueError:
                        return APIError('Passed "layout_data" is not a valid json string.')
                else:
                    setattr(layout, f, params[f])

        layout.save()
        if rolepermission:
            setObjectPermission(layout, rolepermission)
            data = {'success': True}
        else:
            data = {'success': True}

    except BiogpsGenereportLayout.DoesNotExist:
        return APIError("Layout does not exist.")

    return Response(data)


def _layout_delete(request):
    layout_id = request.POST['layout_id']
    try:
        layout = request.user.mylayouts.get(id=layout_id)
        layout.delete()
        # logging layout delete
        log.info('username=%s clientip=%s action=layout_delete id=%s',
                 getattr(request.user, 'username', ''),
                 request.META.get('REMOTE_ADDR', ''),
                 layout_id)

        data = {'success': True}
    except BiogpsGenereportLayout.DoesNotExist:
        data = {'success': False,
                'error': "Layout does not exist."}

    return Response(data)


@api_view(["POST"])
def layout_tree(request):
    """This is a service for populate layout list in TreePanel.
       accepts parameter "node" for POST method.
                         "scope" ("my" or "shared")
    """
    node = request.data.get('node', None)
    if not node:
        return APIError('Unsupported request method "%s"' % request.method)

    node = node.lower()
    children = []
    if node == 'root':
        children = [dict(text='My Layouts', id='/mylayout', cls='folder'),
                    dict(text='Shared Layouts', id='/sharedlayout', cls='folder')]
    elif node.split('/') == ['', 'mylayout']:
        #query_result = getall(request.adamuser)
        query_result = get_my_layouts(request.user)
        for _layout in query_result:
            child = dict(text=_layout.layout_name,
                         id='/mylayout/layout_' + str(_layout.id),
                         cls='folder',
                         layout_id=_layout.id,
                         layout_name=_layout.layout_name,
                         author=_layout.owner.get_valid_name(),
                         description=_layout.description,
                         rolepermission=cvtPermission(_layout.permission).get('R', None),
                         lastmodified=formatDateTime(_layout.lastmodified),
                         created=formatDateTime(_layout.created),
                         layout_scope='my',
                         #permission=_layout.permission,
                         )
            children.append(child)
    elif node.split('/') == ['', 'sharedlayout']:
        query_result = get_shared_layouts(request.user, userselectedonly=True)
        for _layout in query_result:
            child = dict(text=_layout.layout_name,
                         id='/sharedlayout/layout_' + str(_layout.id),
                         cls='folder',
                         layout_id=_layout.id,
                         layout_name=_layout.layout_name,
                         author=_layout.owner.get_valid_name(),
                         description=_layout.description,
                         rolepermission=cvtPermission(_layout.permission).get('R', None),
                         lastmodified=formatDateTime(_layout.lastmodified),
                         created=formatDateTime(_layout.created),
                         layout_scope='shared',
                         #permission=_layout.permission,
                         )
            children.append(child)

    elif len(node.split('/')) == 3:
        root, parent, _node = node.split('/')
        if root == '' and parent in ['mylayout', 'sharedlayout'] and _node.split('/')[-1].startswith('layout_'):
            layout_id = _node[len('layout_'):]
            _layout = BiogpsGenereportLayout.objects.get(id=layout_id)
            #layout_data = json.loads(_layout.layout_data)
            for i, p in enumerate(_layout.layout_data):
                p.update(getplugin(p['id']))
                child = dict(text=p['title'],
                             id='/'.join([root, parent, layout_id, 'plugin_' + str(i) + '_' + str(p['id'])]),
                             leaf=True,
                             cls="file",
                             plugindata=p)
                children.append(child)

#        if scope == 'my':
#            query_result = getall(request.adamuser)
#        else:
#            #shared
#            if request.adamuser.uiprofile.has_key('sharedlayouts') and type(request.adamuser.profile['sharedlayouts']) is type([]):
#                query_result = BiogpsGenereportLayout.objects.filter(id__in=request.adamuser.uiprofile['sharedlayouts'])
    return Response(children)


@api_view(["GET"])
def render_plugin_urls(request, layoutid):
    '''
    URL:  http://biogps.org/layout/159/renderurl/?gene=1017
    '''
    geneid = request.GET.get('geneid', '').strip()
    flag_mobile = request.GET.get('mobile', '').lower() not in ['0', 'false']    # TEMP. set flag_mobile default to True, so that iphone app can get
                                                        # mobile urls without adding "mobile" parameter.The default behavior
                                                        # may be changed later
    if not geneid:
        return APIError('Missing required parameter.')
    if not is_valid_geneid(geneid):
        return APIError('Invalid input parameters!')

    data = get_plugin_urls(request.user, layoutid, geneid, mobile=flag_mobile)
    if isinstance(data, HttpResponse):
        return data
    else:
        return JSONResponse(data)


def get_plugin_urls(user, layoutid, geneid, speciesid=None, mobile=False):
    '''
    Called by render_plugin_urls and mobile/getgeneurls
    URL:  http://biogps-dev.gnf.org/layout/159/renderurl/?geneid=1017
    '''

    if not geneid:
        return APIError('Missing required parameter.')
    if not is_valid_geneid(geneid):
        return APIError('Invalid input parameters!')

    available_layouts = get_my_layouts(user) | get_shared_layouts(user)

    try:
        layout = available_layouts.get(id=layoutid)
    except BiogpsGenereportLayout.DoesNotExist:
        return APIError("Layout does not exist or not belong to you.")

    mg = MyGeneInfo()
    g = mg.get_geneidentifiers(geneid)

    if not g or len(g['SpeciesList']) == 0:
        return APIError('Unknown gene id.')

    plugin_output = []
    for plugin in layout.plugins.order_by('title'):
        try:
            url = plugin.geturl(g, mobile=mobile)
            errmsg = None
        except PluginUrlRenderError as err:
            url = None
            errmsg = err.args[0]
        d = {'id': plugin.id,
             'title': plugin.title,
             'url': url}
        if errmsg:
            d['error'] = errmsg
        plugin_output.append(d)

    layout_output = []
    for lay in available_layouts.order_by('layout_name'):
        d = {'id': lay.id,
             'title': lay.layout_name}
        layout_output.append(d)

    data = {'success': True,
            'layout_id': layout.id,
            'layout_name': layout.layout_name,
            'geneid': geneid,
            'plugins': plugin_output,
            'layouts': layout_output}
    return data
