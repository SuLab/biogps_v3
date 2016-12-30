'''
This file defines all views for URL pattern /plugin/*
'''
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_text
from django.http import HttpResponseRedirect
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.core.mail import mail_managers, send_mail

from rest_framework import viewsets
from rest_framework.response import Response

from biogps.utils.http import api_error
from biogps.utils.models import set_object_permission, Species
from biogps.utils import log, is_valid_geneid

from tagging.models import Tag
from flag.models import add_flag

from biogps.apps.rating.models import Rating
from biogps.apps.gene.boe import MyGeneInfo
from biogps.apps.search.navigations import BiogpsSearchNavigation
from biogps.apps.search.es_lib import ESQuery
from biogps.apps.search.views import list as list_view
from .models import BiogpsPlugin, PluginUrlRenderError
from .forms import BiogpsPluginForm


class PluginViewSet(viewsets.ViewSet):
    def plugin_library(self, request):
        '''This class defines views for REST URL:
             /plugin/
        '''
        # Get the assorted plugin lists that will go in tabs.
        _dbobjects = BiogpsPlugin.objects.get_available(request.user)
        max_in_list = 15

        list1 = []
        list1.append({
            'name': 'Most Popular',
            'more': '/plugin/all/?sort=popular',
            'items': _dbobjects.filter(popularity__score__isnull=False).order_by('-popularity__score')[:max_in_list]
        })
        list1.append({
            'name': 'Newest Additions',
            'more': '/plugin/all/?sort=newest',
            'items': _dbobjects.order_by('-created')[:max_in_list]
        })
        if request.user.is_authenticated():
            mine = {
                'name': 'My Plugins',
                # 'more': '/plugin/mine/',
                'items': BiogpsPlugin.objects.get_mine(request.user)
            }
            if len(mine['items']) > 0:
                list1.append(mine)

        # Get the assorted plugins lists that will go in large category boxes.
        list2 = []
        list2.append({
            'name': 'Expression data',
            'more': '/plugin/tag/expression/',
            'items': _dbobjects.filter(id__in=[26, 430, 440, 58, 9, 469, 38, 200]).order_by('title')
        })
        list2.append({
            'name': 'Protein resources',
            'more': '/plugin/tag/protein/',
            'items': _dbobjects.filter(id__in=[29, 431, 37, 65, 22, 428, 25, 179, 39]).order_by('title')
        })
        list2.append({
            'name': 'Genetics resources',
            'more': '/plugin/tag/genetics/',
            'items': _dbobjects.filter(id__in=[221, 320, 80, 35, 120, 495, 31, 462, 125, 241, 424]).order_by('title')
        })
        list2.append({
            'name': 'Gene portals and MODs',
            'more': '/plugin/tag/portal/',
            'items': _dbobjects.filter(id__in=[27, 69, 10, 30, 47, 32, 135]).order_by('title')
        })
        list2.append({
            'name': 'Pathway databases',
            'more': '/plugin/tag/pathway/',
            'items': _dbobjects.filter(id__in=[565, 15, 66, 500, 159, 259, 319]).order_by('title')
        })
        list2.append({
            'name': 'Literature',
            'more': '/plugin/tag/literature/',
            'items': _dbobjects.filter(id__in=[68, 49, 470, 322, 339, 48]).order_by('title')
        })
        # Sort the list by the number of plugins, which makes the final
        # rendering look nice at all resolutions.
        list2.sort(key=lambda x: (len(x['items']), x['name']))

        # Set up the navigation controls
        # We use ES to give us the category facets
        es = ESQuery(request.user)
        res = es.query(None, only_in='plugin', start=0, size=1)
        nav = BiogpsSearchNavigation(request, type='plugin', es_results=res)

        # Do the basic page setup and rendering
        # prepare_breadcrumb(request)
        # html_template = 'pluginindex.html'
        # html_dictionary = {
        data = {
            'list1': list1,
            'list2': list2,
            'species': Species,
            'all_tags': Tag.objects.all(),
            'navigation': nav
        }
        return Response(data)
        # return render_to_formatted_response(request,
        #                                     data=None,
        #                                     allowed_formats=['html'],
        #                                     html_template=html_template,
        #                                     html_dictionary=html_dictionary,
        #                                     pagination_by=10)

    def add_plugin(self, request, sendemail=True):
        '''
        If sendemail is True, an notification email will be sent out for every new plugin added.
        POST to /plugin
            optional parameters:
                rolepermission
                userpermission
                tags
                allowdup
        '''
        rolepermission = request.data.get('rolepermission', None)
        userpermission = request.data.get('userpermission', None)
        tags = request.data.get('tags', None)
        data = {'success': False}

        f = BiogpsPluginForm(request.data)
        if f.is_valid():
            #flag to allow save duplicated (same url, type, options) plugin
            allowdup = (request.data.get('allowdup', None) == '1')
            if not allowdup:
                all_plugins = BiogpsPlugin.objects.get_available(request.user)
                dup_plugins = all_plugins.filter(url=f.cleaned_data['url'])

                if dup_plugins.count() > 0:
                    data = {'success': False,
                            'dup_plugins': [dict(id=p.id, text=smart_text(p), url=p.get_absolute_url()) for p in dup_plugins],
                            'error': 'Duplicated plugin exists!'}
                    return Response(data, status=400)

            # proceed with saving the plugin
            plugin = f.save(commit=False)
            plugin.type = 'iframe'
            plugin.ownerprofile = request.user.profile
            plugin.save()

            if rolepermission or userpermission:
                set_object_permission(plugin, rolepermission, userpermission, sep=',')

            if tags is not None:
                plugin.tags = smart_text(tags)

            plugin.save()   # Save again to trigger ES index update
            data['success'] = True
            data['id'] = plugin.id

            # Logging plugin add
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
        else:
            data['success'] = False
            data['errors'] = f.errors

        return Response(data, status=200 if data['success'] else 400)

    def plugin_list(self, request, *args, **kwargs):
        '''This class defines views for REST URL:
             /plugin/all/
             /plugin/mine/
             /plugin/popular/
             /plugin/tag/expression/
             /plugin/species/human/
             /plugin/species/human/tag/expression/
        '''

        kwargs.update(request.GET.items())
        kwargs.update({'in': 'plugin'})
        return list_view(request, *args, **kwargs)

    def _get_plugin(self, request, plugin_id):
        available_plugins = BiogpsPlugin.objects.get_available(request.user)
        return get_object_or_404(available_plugins, id=plugin_id)

    def get_plugin(self, request, plugin_id, slug=None):
        '''Get a specific plugin object via GET
        '''
        plugin = self._get_plugin(plugin_id)
        if request.user.is_authenticated():
            plugin.prep_user_data(request.user)

        nav = BiogpsSearchNavigation(request, params={'only_in': ['plugin']})
        # html_template = 'plugin/show.html'
        html_dictionary = {
            'current_obj': plugin,
            'rating_scale': Rating.rating_scale,
            'rating_static': Rating.rating_static,
            'canonical': plugin.get_absolute_url(),
            'navigation': nav
        }
        return Response(html_dictionary)
        # return render_to_formatted_response(request,
        #                                     data=plugin,
        #                                     allowed_formats=['html', 'json', 'xml'],
        #                                     model_serializer='object_cvt',
        #                                     html_template=html_template,
        #                                     html_dictionary=html_dictionary)

    def update_plugin(self, request, plugin_id, slug=None):
        '''
        Modify a plugin via PUT.
        '''
        plugin = self._get_plugin(plugin_id)
        rolepermission = request.data.get('rolepermission', None)
        userpermission = request.data.get('userpermission', None)
        tags = request.data.get('tags', None)
        data = {'success': False}

        f = BiogpsPluginForm(request.data, instance=plugin)
        if f.is_valid():
            if rolepermission or userpermission:
                set_object_permission(plugin, rolepermission, userpermission, sep=',')

            if tags is not None:
                plugin.tags = smart_text(tags)

            f.save()
            data['success'] = True

            # Logging plugin modification
            log.info('username=%s clientip=%s action=plugin_modify id=%s',
                     getattr(request.user, 'username', ''),
                     request.META.get('REMOTE_ADDR', ''),
                     plugin.id)
        else:
            data['success'] = False
            data['errors'] = f.errors

        return Response(data, status=200 if data['success'] else 400)

    def delete_plugin(self, request, plugin_id, slug=None):
        plugin = self._get_plugin(plugin_id)
        plugin.delete()
        del plugin.permission

        # Logging plugin delete
        log.info('username=%s clientip=%s action=plugin_delete id=%s',
                 getattr(request.user, 'username', ''),
                 request.META.get('REMOTE_ADDR', ''),
                 plugin.id)

        data = {'success': True}

        return Response(data)

    def test_plugin_url(request):
        '''This view is used to test a url template with a given gene.
           http://biogps.org/plugin/test?url=http://www.google.com/search?q={{Symbol}}&geneid=1017
           http://biogps.org/plugin/test?url=http://www.google.com/search?q={{MGI}}&species=mouse&geneid=1017

           if species is not provided, all available species are assumed.
        '''
        geneid = request.query_params.get('geneid', '').strip()
        url = request.query_params.get('url', '').strip()
        species = [s.strip() for s in request.GET.get('species', '').split(',')]
        species = None if species == [''] else species
        if not geneid or not url:
            return api_error('Missing required parameter.')
        if not is_valid_geneid(geneid):
            return api_error('Invalid input parameters!')
        plugin = BiogpsPlugin(url=url, species=species)

        mg = MyGeneInfo()
        g = mg.get_geneidentifiers(geneid)

        if not g or len(g['SpeciesList']) == 0:
            return api_error('Unknown gene id.')

        try:
            url = plugin.geturl(g)
        except PluginUrlRenderError as err:
            return api_error(err.args[0], status=400)

        data = {'success': True,
                'geneid': geneid,
                'url': url}
        return Response(data)

    def render_url(self, request, plugin_id):
        '''
        URL:  http://biogps.org/plugin/159/renderurl/?geneid=1017
              http://biogps.org/plugin/159/renderurl/?geneid=1017&redirect    -    will re-direct to rendered url
              http://biogps.org/plugin/159/renderurl/?geneid=1017&mobile=true    -    use optional mobile_url if provided by the owner
        '''
        plugin = self._get_plugin(plugin_id)
        geneid = request.GET.get('geneid', '').strip()
        flag_mobile = request.GET.get('mobile', '').lower() in ['1', 'true']
        if not geneid:
            return api_error('Missing required parameter.')
        if not is_valid_geneid(geneid):
            return api_error('Invalid input parameters!')

        mg = MyGeneInfo()
        g = mg.get_geneidentifiers(geneid)

        if not g or len(g['SpeciesList']) == 0:
            return api_error('Unknown gene id.')

        try:
            url = plugin.geturl(g, mobile=flag_mobile)
        except PluginUrlRenderError as err:
            return api_error(err.args[0])

        #goto url directly if "redirect" is passed
        if 'redirect' in request.query_params:
            return HttpResponseRedirect(url)

        data = {'success': True,
                'plugin_id': plugin.id,
                'geneid': geneid,
                'url': url}
        return Response(data)

    def flag(self, request, plugin_id):
        '''Flag a plugin as inappropriate content.'''
        plugin = self._get_plugin(plugin_id)
        try:
            content_type = ContentType.objects.get(
                app_label=plugin._meta.app_label, model=plugin._meta.model_name)
        except BiogpsPlugin.DoesNotExist:
            return api_error('ContenType for "BiogpsPlugin" does not exist.')

        reason = "Reason: " + request.POST.get("reason")
        comment = smart_text(reason + ".\nComment: " + request.POST.get("comment", ''))

        user_agent = request.META.get('HTTP_USER_AGENT', '')

        #apply flag
        flaginstance = add_flag(request.user, content_type, plugin.id, plugin.owner, comment)
        site = Site.objects.get_current()
        #notify moderator
        d = {
            'flagger': request.user,
            'plugin': plugin,
            'flaginstance': flaginstance,
            'user_agent': user_agent,
            'site': site
        }
        mail_managers(subject='Plugin was flagged by a user',
                      message=render_to_string('plugin/plugin_flagged_notification.txt', d),
                      fail_silently=True)
        #notify plugin owner
        if plugin.owner and plugin.owner.email:
            d = {
                'flagger': request.user,
                'plugin': plugin,
                'flaginstance': flaginstance,
                'site': site,
                'user_agent': user_agent,
                'for_plugin_owner': True
            }
            send_mail('Your plugin was flagged by a user',
                      render_to_string('plugin/plugin_flagged_notification.txt', d),
                      settings.DEFAULT_FROM_EMAIL,
                      [plugin.owner.email])

        json_response = {'success': True,
                         'msg': 'You have added a flag. A moderator will review your submission shortly.'}
        return Response(json_response)
