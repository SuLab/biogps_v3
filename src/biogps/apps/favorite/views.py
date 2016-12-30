from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from biogps.utils.models import BioGPSModel
from biogps.utils.decorators import loginrequired
from biogps.utils.restview import RestView
from biogps.utils.http import JSONResponse
from biogps.apps.favorite.models import Favorite
from biogps.apps.gene.models import Gene
from biogps.apps.plugin.models import BiogpsPlugin
from biogps.apps.gene.models import get_gene_list

# Types of objects available for favoriting
fav_types = {'gene': Gene, 'plugin': BiogpsPlugin}


class FavoriteSubmitView(RestView):
    '''This class defines views for REST URL:
        /favorite/<modelType>/<objectID>/
    '''
    @loginrequired
    def get(self, request, modelType, objectID):
        # User has clicked favorite link - validate and save to DB.
        #favorite_choice = request.POST.get('choice', None)
        favorite_choice = request.GET.get('choice', None)
        if favorite_choice in ['true', 'false']:
            favorited = True if favorite_choice == 'true' else False

            if modelType == 'gene':
                # Special handling for genes, which are stored externally
                con_type = ContentType.objects.get_for_model(Gene)
            else:
                obj, con_type = BioGPSModel.get_object_and_ctype(modelType,
                                                                 pk=objectID)

            if con_type:
                # Get favorite
                try:
                    f = Favorite.objects.get(user=request.user,
                                             content_type=con_type,
                                             object_id=objectID)
                    if not favorited:
                        f.delete()
                except Favorite.DoesNotExist:
                    if favorited:
                        Favorite.objects.create(user=request.user,
                                                content_type=con_type,
                                                object_id=objectID)
                return JSONResponse({'success': True})
            else:
                return JSONResponse({'success': False,
                                     'error': 'Invalid object'})
        else:
            return JSONResponse({'success': False,
                                 'error': 'Invalid choice'})


class FavoriteObjectView(RestView):
    '''This class defines views for REST URL:
        /favorite/<modelType>/
    '''
    @loginrequired
    def get(self, request, modelType):
        # Return all of User's favorites for specified object
        _response = list()
        fav_model = modelType.lower()
        try:
            ct = ContentType.objects.get_for_model(fav_types[fav_model])
            _favorites = request.user.favorite_set.filter(content_type=ct)
            if fav_model == 'gene':
                _response = get_gene_list([f.object_id for f in _favorites])
            else:
                for f in _favorites:
                    fav_obj = f.content_type.get_object_for_this_type(id=f.object_id).object_cvt()
                    fav_meta = {'id': fav_obj['id'], 'name': fav_obj['name'], 'description': fav_obj['description']}
                    _response.append(fav_meta)
        except KeyError:
            pass
        return JSONResponse(_response)


class FavoriteView(RestView):
    '''This class defines views for REST URL:
        /favorite/
    '''
    @loginrequired
    def get(self, request):
        # Return all of User's favorites
        _favorites = request.user.favorite_set.all()
        _response = dict()
        if _favorites:
            fav_geneid_li = []
            for f in _favorites:
                if f.content_type.name == 'gene':
                    fav_geneid_li.append(f.object_id)
                else:
                    fav_obj = f.content_type.get_object_for_this_type(id=f.object_id)
                    short_name = fav_obj.short_name
                    fav_obj = fav_obj.object_cvt()
                    fav_meta = {'id': fav_obj['id'], 'name': fav_obj['name'], 'description': fav_obj['description']}
                    if short_name in _response.keys():
                        # Append favorite to content type list
                        _response[short_name].append(fav_meta)
                    else:
                        # Create new content type key and append result
                        _response[short_name] = [fav_meta]
            if fav_geneid_li:
                fav_genelist = get_gene_list(fav_geneid_li)
                if fav_genelist:
                    _response['gene'] = fav_genelist
        return JSONResponse(_response)
