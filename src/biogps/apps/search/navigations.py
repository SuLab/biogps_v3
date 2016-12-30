# -*- coding: utf-8 -*-
'''
This file defines a BiogpsSearchNavigation class to hold navigation data used
to render left-side navigation panel in search results/browse page.
'''
import requests

from collections import OrderedDict

from django.conf import settings

from biogps.utils.models import Species


class BiogpsNavigationDataset(object):
    def __init__(self, title, results=None, tags=None):
        self.doc_types = ['dataset']
        self._title = title
        self.results = results
        self.tags = tags
        self.init_facets()

    @property
    def title(self):
        return self._title

    def init_facets(self):
        facets = OrderedDict()
        facets['tag'] = {'name': 'TAGS', 'terms': []}
        if self.tags is None:
            res = requests.get(settings.DATASET_SERVICE_HOST + '/dataset/tag/')
            tags = res.json()['details']['results']
        else:
            tags = self.tags
        for e in tags:
            _f = {
                  'term': e['name'],
                  'icon': 'tag2',
                  'url': '/dataset/tag/'+e['name']+'/'
                  }
            facets['tag']['terms'].append(_f)
            
        facets['tag']['terms'].append({
                    'term': 'more ›',
                    'title': 'Show all Tags',
                    'url': '/dataset/tag/',
                    'css_class': 'more-link'
                })
        facets['species'] = {
            'name': 'SPECIES',
            'terms': []
        }
        ds_species =  ['human', 'mouse', 'rat', 'pig']
        for s in Species:
            if s.name not in ds_species:
                continue
            facets['species']['terms'].append({
                'term': s.name.capitalize(),
                'title': s.short_genus,
                'url': '/dataset/species/'+s.name+'/'
            })
        self.facets = facets

    @property
    def query_string(self):
        out = ''
        if self.doc_types:
            out += 'in:' + ','.join(self.doc_types) + ' '
        return out
    
    @property
    def paging_footer(self):
          if not self.results:
              return None
          out = 'Displaying '
          types = 'dataset'
  
          # Pluralize results
          if len(self.results['results']) != 1:
              types += 's '
  
          if self.results['count'] > len(self.results['results']):
              out += types
              out += str(self.results['start']) + ' - ' + str(self.results['end']) + ' of '
              out += str(self.results['count']) + ' in total.'
          else:
              out += str(self.results['count']) + ' ' + types
          return out


class BiogpsSearchNavigation(object):
    def __init__(self, request, type='', doc_types=[], es_results=None, params={}):
        self._request = request
        self._path = request.path_info
        self.page_type = type
        self._es_results = es_results if es_results and not es_results.has_error() else None
        self._filters = params.get('filter_by', None)
        self.query = params.get('q', None)

        self.doc_types = params.get('only_in', None) or [t['term'] for t in self._es_results.facets._type.terms]
        self.multiple_types = len(self.doc_types) > 1 or len(self.doc_types) == 0
        self.doc_type = None if self.multiple_types else self.doc_types[0]

        self._init_facets()
        pass

    @property
    def title(self):
        if self.is_search():
            out = 'Search Results'
            if self.doc_type:
                out = self.doc_type.capitalize() + ' ' + out

        elif self.doc_type:
            if self._es_results and self._filters:
                out = self.doc_type.capitalize() + 's'
                if 'tag' in self._filters:
                    out = self._filters['tag'].capitalize() + ' ' + out
                if 'species' in self._filters:
                    _species = self._filters['species']
                    if not isinstance(_species, basestring):
                        _species = ', '.join(_species)
                    out += ' for ' + _species.capitalize()
            else:
                out = 'BioGPS ' + self.doc_type.capitalize() + ' Library'
        else:
            out = 'BioGPS Library'
        return out

    @property
    def query_string(self):
        out = ''
        if self.doc_types:
            out += 'in:' + ','.join(self.doc_types) + ' '
        if self._filters:
            for f, fv in self._filters.items():
                out += f + ':'
                out += fv if isinstance(fv, basestring) else ','.join(fv)
                out += ' '
        if self.query:
            out += self.query
        return out

    @property
    def paging_footer(self):
        if not self._es_results:
            return None
        out = 'Displaying '
        types = self.doc_type or 'result'

        # Pluralize results
        if len(self._es_results) != 1:
            types += 's '

        if self._es_results.hits.total > self._es_results.hits.hit_count:
            out += types
            hit_range = self._es_results.get_current_hit_range()
            out += str(hit_range[0] + 1) + ' - ' + str(hit_range[1]) + ' of '
            out += str(self._es_results.hits.total) + ' in total.'
        else:
            out += str(self._es_results.hits.total) + ' ' + types
        return out

    def _init_facets(self):
        facets = OrderedDict()
        # OBJECT TYPE NAVIGATION
        # TMP disabled
        '''
        facets['type'] = {
            'name': 'LIBRARY',
            'terms': [
                {'term': 'plugin', 'url': '/plugin/'},
                # {'term': 'layout', 'url': '/layout/'},
                {'term': 'dataset', 'url': '/dataset/'},
                # {'term': 'genelist', 'url': '/genelist/'}
            ]
        }
        if self.is_search():
            facets['type']['name'] = 'SEARCH'
            #facets['type']['terms'].insert(0, {'term': 'gene', 'url': '/gene/'})
        # Add in type faceting from search results
        active_set = False
        if self._es_results and self._es_results.facets._type:
            for s in self._es_results.facets._type.terms:
                for t in facets['type']['terms']:
                    if t['term'] == s['term']:
                        t['count'] = s['count']
                    try:
                            if t['term'] in self.doc_types:
                            t['active'] = True
                            active_set = True
                    except KeyError:
                        pass
        for t in facets['type']['terms']:
            t['term'] = t['term'].capitalize() + 's'
        '''

        # CATEGORY NAVIGATION
        # Add in category faceting from search results
        if self._es_results and self._es_results.facets.tag:
            active_set = False
            facets['tag'] = {'name': 'TAGS', 'terms': []}
            for c in self._es_results.facets.tag.terms:
                _f = {
                    'term': c['term'],
                    'count': c['count'],
                    'icon': 'tag2',
                    'url': self.add_facet_to_path('tag', c['term'])
                }
                try:
                    if (not active_set) and self._filters['tag'] == c['term']:
                        _f['active'] = True
                        active_set = True
                except (KeyError, TypeError):
                    pass
                facets['tag']['terms'].append(_f)

            if self.doc_type:
                _f = {
                    'term': 'All ' + self.doc_type.capitalize() + 's',
                    'url': '/' + self.doc_type + '/all/'
                }
                if (not active_set):
                    _f['active'] = True
                facets['tag']['terms'].insert(0, _f)

                facets['tag']['terms'].append({
                    'term': 'more ›',
                    'title': 'Show all Tags',
                    'url': '/' + self.doc_type + '/tag/',
                    'css_class': 'more-link'
                })

        # SPECIES NAVIGATION
        facets['species'] = {
            'name': 'SPECIES',
            'terms': []
        }

        is_dataset = ['human', 'mouse', 'rat', 'pig'] if self.doc_type == 'dataset' else False
        for s in Species:
            if is_dataset and s.name not in is_dataset:
                continue
            facets['species']['terms'].append({
                'term': s.name.capitalize(),
                'title': s.short_genus,
                'url': self.add_facet_to_path('species', s.name)
            })
        # Add in species faceting from search results
        active_set = False
        if self._es_results and self._es_results.facets.species:
            for s in self._es_results.facets.species.terms:
                for t in facets['species']['terms']:
                    if t['term'].lower() == s['term']:
                        t['count'] = s['count']
                    try:
                        if self._filters['species'] == t['term'].lower():
                            t['active'] = True
                            active_set = True
                    except (KeyError, TypeError):
                        pass

        self.facets = facets

    def add_facet_to_path(self, facet, term):
        if self.is_search():
            return self.add_facet_to_search_url(facet, term)
        else:
            return self.add_facet_to_list_url(facet, term)

    def add_facet_to_search_url(self, facet, term):
        path = '/search/?'
        terms = []
        if self.query:
            terms.append('q=' + self.query)
        if self.doc_types:
            terms.append('in=' + ','.join(self.doc_types))
        if self._filters:
            for f, fv in self._filters.items():
                if f == facet: continue
                terms.append(f + '=' + fv)

        terms.append(facet + '=' + term)

        return path + '&'.join(terms)

    def add_facet_to_list_url(self, facet, term):
        path = self._path.split('/')

        # Remove existing special case URLs
        # SPECIAL URL 1: /plugin/all/
        # Remove it every time
        try:
            i = path.index('all')
            path.pop(i)
        except ValueError:
            pass
        # SPECIAL URL 2: /plugin/tag/
        # Remove it only when there is nothing after it
        if path[-2] == 'tag':
            path.pop(-2)

        # If the facet already exists in the URL, replace the value
        try:
            i = path.index(facet)
            path[i+1] = term
        # If the facet is new to this URL, append it
        except ValueError:
            end = path.pop()
            path.append(facet)
            path.append(term)
            path.append(end)

        return '/'.join(path)

    def is_search(self):
        return self.page_type == 'search'

    def is_list(self):
        return self.page_type == 'list'
