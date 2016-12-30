import re
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from rest_framework.response import Response

from biogps.utils.http import JSONResponse, render_to_formatted_response
from biogps.utils.models import Species
from biogps.utils import const
from biogps.search.navigations import BiogpsSearchNavigation, BiogpsNavigationDataset
from es_lib import ESQuery
import requests
from django.conf import settings

import logging
log = logging.getLogger('biogps_prod')


def status(request):
    '''This view is for debug or ES server monitoring purpose.'''
    if request.method in ['GET', 'HEAD']:
        es = ESQuery()
        status = es.status()
        return JSONResponse(status)


def _handle_commom_params(params, types=None):
    '''handles common params from QueryDict <params> (e.g. request.GET).'''
    q = params.get('q', "")

    # Figure out the type(s) of objects we're looking for
    if types is None:
        # 1) Check the params hash directly (i.e. if it came from a URL param)
        types = params.get('in', None)

        # 2) Check the query string contents
        if not types and q:
            pattern = 'in:([\w,]+)'
            _q = re.search(pattern, q)
            if _q:
                types = _q.group(1)
                q = re.sub(pattern, '', q).strip()

    if not types:
        # No match, set to gene which will route to V1 search in search funtion
        types = 'gene'

    # Ensure types finishes as an array
    if types is not None:
        types = [x.strip() for x in types.split(',')]
    # Handle tag and species filtering
    _filters = ['tag', 'species']
    filter_by = {}
    for f in _filters:
        # 1) Check the params hash directly
        _f = params.get(f, None)
        # 2) Check the query string contents
        if not _f and q:
            pattern = f + ':([\w,]+)'
            _q = re.search(pattern, q)
            if _q:
                _f = _q.group(1)
                q = re.sub(pattern, '', q).strip()
        # If we've found something, add it to our filter list
        if _f:
            filter_by[f] = _f

    # Paging parameters
    start = params.get('from', None)
    if not start:
        start = params.get('start', 0)
    start = int(start)
    size = params.get('size', None)
    if not size:
        size = params.get('limit', 10)
    size = int(size)
    explain = params.get('explain', None) == 'true'

    # Sorting parameter translation. Defaults to popularity
    sort_param = params.get('sort', '')
    # Handle special sort cases
    if not sort_param or sort_param == 'popular':    # e.g. /plugin/all/?sort=popular
        #set default sorting on popularity for plugin and dataset
        if types[0] == 'plugin':
            sort = [{'popularity': 'desc'}]
        elif types[0] == 'dataset':
            # Default BiogpsStat sorting
            sort = [{'popularity.all_time': {'order': 'desc', 'missing': '_last'}}]
        else:
            sort = None

    elif sort_param == 'newest':   # e.g. /plugin/all/?sort=newest
        sort = [{'created': 'desc'}]
    else:
        # Other generic sort case
        sort = [s.strip() for s in params.get('sort', '').split(',')]
        sort = [{s[1:]: 'desc'} if s[0] == '-' else s for s in sort if s]

    # Fields to return for each object. Defaults to _source
    fields = [s.strip() for s in params.get('fields', '_source').split(',')]

    f = [x.strip() for x in params.get('f', '').split(',') if x.strip() != '']  # facets fields
    h = [x.strip() for x in params.get('h', '').split(',') if x.strip() != '']  # hl_fields

    return dict(only_in=types, q=q, filter_by=filter_by, fields=fields,
                start=start, size=size, sort=sort, h=h, facets=f, explain=explain)


def list(request, *args, **kwargs):
    _type = kwargs['in']
    common_params = _handle_commom_params(kwargs)

    # Add breadcrumbs based on the filters
    for f, fv in common_params.get('filter_by').items():
        request.breadcrumbs(f.capitalize() + ': ' + fv.capitalize(), '/'.join(['', _type, f, fv, '']))
    if not common_params['filter_by']:
        _cap_type = _type[0].upper() + _type[1:]
        request.breadcrumbs('All {}s'.format(_cap_type), '/{}/all/'.format(_type))

    es = ESQuery(request.user)
    res = es.query(**common_params)

    # Set up the navigation controls
    nav = BiogpsSearchNavigation(request, type='list', es_results=res, params=common_params)

    # Do the basic page setup and rendering
    html_template = '{}/list.html'.format(_type)
    html_dictionary = {
        'items': res,
        'species': Species,
        'navigation': nav
    }
    ctype = common_params['only_in'][0]
    if ctype == 'plugin':
        es = ESQuery(request.user)
        res = es.query(**common_params)
        page_by = common_params.get('size', 10)

        # Set up the navigation controls
        nav = BiogpsSearchNavigation(request, type='list', es_results=res, params=common_params)

        # Do the basic page setup and rendering
        html_template = '{}/list.html'.format(_type)
        html_dictionary = {
            'items': res,
            'species': Species,
            'navigation': nav
        }
    elif ctype == 'dataset':
        page = request.GET.get('page', 1)
        page = int(page)
        #page_by = common_params.get('page_by', 10)
        #page_by equals list.html pagination setting
        page_by = 10
        species = common_params['filter_by'].get('species', None)
        tag = common_params['filter_by'].get('tag', None)
        args = {'page': page, 'page_by': page_by}
        tag_agg = None
        if species is None and tag is None:
            order = kwargs.get('sort', None)
            if order == 'popular':
                args['order'] = 'pop'
            else:
                args['order'] = 'new'
            res = requests.get(settings.DATASET_SERVICE_HOST + '/dataset/', params=args)
        else:
            if species is not None:
                args['species'] = species
            if tag is not None:
                args['tag'] = tag
            args['agg'] = 1
            res = requests.get(settings.DATASET_SERVICE_HOST + '/dataset/search/4-biogps/', params=args)
            tag_agg = res.json()['details']['aggregations']
        res = res.json()['details']
        # Set up the navigation controls
        # nav = BiogpsSearchNavigation(request, type='list', es_results=res, params=common_params)
        res['start'] = (page-1) * page_by
        res['end'] = res['start'] + len(res['results'])
        res['start'] += 1
        items = [None] * (res['start'] - 1) + res['results']
        if len(items) < res['count']:
            items += [None] * (res['count'] - res['end'])
        html_template = 'dataset/list.html'

        if tag is not None:
            title = tag.capitalize() + ' Datasets'
        else:
            title = 'Datasets'
        if species is not None:
            title += ' for ' + species.capitalize()
        nav = BiogpsNavigationDataset(title, res, tag_agg)

        # Do the basic page setup and rendering
        html_template = 'dataset/list.html'
        sample_gene = const.sample_gene
        res = items
        html_dictionary = {
            'items': res,
            # 'species': Species,
            'sample_geneid': sample_gene,
            'navigation': nav
        }
    else:
        raise ValueError("invalid ctype!")

    return Response(html_dictionary)
    # return render_to_formatted_response(request,
    #                                     data=res,
    #                                     allowed_formats=['html', 'json', 'xml'],
    #                                     model_serializer='object_cvt',
    #                                     html_template=html_template,
    #                                     html_dictionary=html_dictionary,
    #                                     pagination_by=page_by)  #10)


def search(request, _type=None):
    '''The view function for urls:
          /search/?q=cdk2
          /search/plugin/?q=cancer
          /search/layout/?q=pathway
          /search/?q=cancer&in=plugin
          /search/?q=pathway2&in=layout
          /search/?q=cancer&in=plugin,gene

          /search/plugin/?q=cancer&from=10&size=10

          /search/plugin/?q=cancer&sort=id

       Note that un-recognized _type string is ignored, if no valid _type is
         passed, the search is against all types.

    '''
    common_params = _handle_commom_params(request.GET, types=_type)
    # format = request.GET.get('format', 'html')
    q = common_params.get('q', '')

    # For now V2 search does not support genes
    #if format == 'html' and common_params['only_in'] == ['gene']:
    if common_params['only_in'] == ['gene']:
        # Redirect the user to the V1 search engine
        _url = ('/?query=' + q) if q else '/'
        return HttpResponseRedirect(request, _url)

    ctype = common_params['only_in'][0]
    if ctype == 'plugin':
        es = ESQuery(request.user)
        res = es.query(**common_params)
        #logging query stat
        if res.has_error():
            logmsg = 'action=es_query in=%s query=%s qlen=%s error=1 errormsg=%s' % \
                     (','.join(common_params['only_in']),
                      q[:1000],   # truncated at length 1000
                      len(q),
                      res.error)
        else:
            logmsg = 'action=es_query in=%s query=%s qlen=%s num_hits=%s total=%s' % \
                     (','.join(common_params['only_in']),
                      q[:1000],   # truncated at length 1000
                      len(q),
                      res.hits.hit_count,
                      len(res))
        log.info(logmsg)
        # log plugin_quick_add action
        flag_plugin_quick_add = _type == 'plugin' and request.GET.get('quickadd', None) is not None
        if flag_plugin_quick_add:
            log.info('action=plugin_quick_add')

        # Set up the navigation controls
        nav = BiogpsSearchNavigation(request, type='search', es_results=res, params=common_params)

        # Do the basic page setup and rendering
        if res.query and res.query.has_valid_doc_types():
            # Successful search result
            ctype = common_params['only_in'][0]
            request.breadcrumbs('{} Library'.format(ctype.capitalize()), '/{}/'.format(ctype))
            try:
                request.breadcrumbs(u'Search: {}'.format(q.split(' ', 1)[1]), request.path_info + u'?q={}'.format(q))
            except IndexError:
                request.breadcrumbs(u'Search: {}'.format(q), request.path_info + u'?q={}'.format(q))
            html_template = '{}/list.html'.format(ctype)
            html_dictionary = {
                'items': res,
                'species': Species,
                'navigation': nav
            }
        else:
            html_template = 'search/no_results.html'
            html_dictionary = {}

        if res.has_error():
            html_dictionary['items'] = None
            html_dictionary['error'] = res.error

    elif ctype == 'dataset':
        page = request.GET.get('page', 1)
        page = int(page)
        #page_by = common_params.get('page_by', 10)
        #page_by equals list.html pagination setting
        page_by = 10
        args = {'query': common_params['q'], 'page': page, 'page_by': page_by}
        res = requests.get(settings.DATASET_SERVICE_HOST + '/dataset/search/4-biogps/', params=args)
        res = res.json()['details']

        # Set up the navigation controls
        res['start'] = (page-1) * page_by
        # should not use page_by
        res['end'] = res['start'] + len(res['results'])
        res['start'] += 1
        nav = BiogpsNavigationDataset('Dataset Search Results', res)

        # Do the basic page setup and rendering
    #    if res.query and res.query.has_valid_doc_types():
        if len(res['results']) > 0:
            # mock up whole array for django-paginator
            items = [None] * (res['start'] - 1) + res['results']
            if len(items) < res['count']:
                items += [None] * (res['count'] - res['end'])
            ctype = 'dataset'
            request.breadcrumbs('{} Library'.format(ctype.capitalize()), '/{}/'.format(ctype))
            try:
                request.breadcrumbs(u'Search: {}'.format(q.split(' ', 1)[1]), request.path_info + u'?q={}'.format(q))
            except IndexError:
                request.breadcrumbs(u'Search: {}'.format(q), request.path_info + u'?q={}'.format(q))
            html_template = '{}/list.html'.format(ctype)
            html_dictionary = {
                'items': items,
                'species': Species,
                'navigation': nav
            }
        else:
            html_template = 'search/no_results.html'
            html_dictionary = {}
    else:
        raise ValueError("invalid ctype!")

    return render_to_formatted_response(request,
                                        data=res,
                                        allowed_formats=['html', 'json', 'xml'],
                                        model_serializer='object_cvt',
                                        html_template=html_template,
                                        html_dictionary=html_dictionary)


def interval(request):
    chr = request.GET.get('chr', None)
    gstart = request.GET.get('gstart', None)
    gend = request.GET.get('gend', None)
    taxid = request.GET.get('taxid', None)
    species = request.GET.get('species', None)
    assembly = request.GET.get('assembly', None)

    if not chr or not gstart or not gend or \
      (not taxid and not species and not assembly):
        return HttpResponseBadRequest("Missing required parameters.")

    common_params = _handle_commom_params(request.GET, types='gene')

    es = ESQuery(request.user)
    res = es.query_gene_by_interval(chr, gstart, gend,
                                    taxid, species, assembly,
                                    **common_params)
    return JSONResponse(res.object_cvt())


def get_mapping(request):
    es = ESQuery(request.user)
    return JSONResponse(es.conn.get_mapping())
