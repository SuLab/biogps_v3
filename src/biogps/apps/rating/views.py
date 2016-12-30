from django.http import HttpResponseBadRequest
from biogps.apps.rating.models import Rating
from biogps.apps.rating.forms import RatingForm
from biogps.utils.decorators import loginrequired
from biogps.utils.models import BioGPSModel
from biogps.utils.restview import RestView
from biogps.utils.http import JSONResponse


class RatingSubmitView(RestView):
    '''This class defines views for REST URL:
        /rating/<modelType>/<objectID>/
    '''
    @loginrequired
    def post(self, request, modelType, objectID):
        rating_form = RatingForm(request.POST)
        invalid_message = '''Invalid rating value submitted.
        Acceptable values are 1 - 5.'''
        try:
            posted_rating = int(request.POST['rating'])
        except ValueError:
            return HttpResponseBadRequest(invalid_message)
        if posted_rating < 1 or posted_rating > 5:
            return HttpResponseBadRequest(invalid_message)
        elif rating_form.is_valid():
            obj, con_type = BioGPSModel.get_object_and_ctype(modelType,
                                                             pk=objectID)
            if obj and con_type:
                cleaned_rating = rating_form.cleaned_data['rating']
                # If first time rating this object save to DB,
                # otherwise return False
                r, first_rating = Rating.objects.get_or_create(
                    user=request.user,
                    content_type=con_type,
                    object_id=objectID,
                    defaults={'rating': cleaned_rating})
                if not first_rating:
                    # User previously rated this object, update
                    r.rating = cleaned_rating
                    r.save()
                # Get total and average ratings for this object
                obj_ratings = obj.rating_data
                #update ES index for this object
                obj.re_index()

                return JSONResponse({'success': True,
                                     'totalRatings': obj_ratings['total'],
                                     'avgRating': obj_ratings['avg_stars']})
            else:
                return JSONResponse({'success': False,
                                     'error': 'Invalid object'})
        else:
            return HttpResponseBadRequest(str(rating_form.errors))
