from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.base import RequestContext
from django.contrib.auth.models import User

from biogps.utils.http import (loginrequired_or_redirect,
                               JSONResponse,
                               getCommonDataForMain)
from biogps.apps.auth2.models import clean_username
from biogps.apps.plugin.models import BiogpsPlugin
from .models import BiogpsProfile
from .forms import BiogpsProfileForm
#from friends.models import friend_set_for


@loginrequired_or_redirect
def index(request, **kwargs):
    """
    Profile index page.
    URL:          http://biogps.org/profile/
    """

    return HttpResponseRedirect(request, request.user.get_absolute_url())


@loginrequired_or_redirect
def edit(request, via="POST"):
    '''
    URL:          http://biogps.gnf.org/profile/edit/
    '''

    profile = BiogpsProfile.objects.get_or_create(user=request.user)
    profile = profile[0]   # get_or_create returns a tuple, and we just want the first object

    if request.method == 'POST':
        form = BiogpsProfileForm(request.POST, instance=profile)

        if form.is_valid():
            form.save()
            data = {'success': True}
        else:
            data = {'success': False, 'errors': form.errors}

        return JSONResponse(data)
    else:
        return HttpResponseRedirect(request, request.user.get_absolute_url())


def view(request, userid, junk=''):
    try:
        vuser = User.objects.get(id=userid)
    except:
        raise Http404

    # Confirm that the userid and username in the URL match
    if not clean_username(vuser.username).lower() == junk.lower().replace('.html', ''):
        raise Http404

    d = getCommonDataForMain(request)
    d['vuser'] = vuser

    # get_or_create returns a tuple with the object we want as the first item.
    profile_tuple = BiogpsProfile.objects.get_or_create(user=vuser)
    d['vprofile'] = profile_tuple[0].filter_for_user(request.user)

    d['vplugins'] = BiogpsPlugin.objects.get_available_from(vuser, request.user)

    if not request.user.is_anonymous():
        d['isOwner'] = d['vprofile'].belongs_to(request.user)
        #d['isFriend'] = vuser.is_friends_with(request.user)
        #if not d['isFriend']:
        #   d['inviteStatus'] = vuser.invite_status_with(request.user)
        #   d['inverseInviteStatus'] = request.user.invite_status_with(vuser)

    #d['vfriends'] = friend_set_for(vuser)

    if settings.DEBUG:
        from django.template.context_processors import request as request_processor
        context = RequestContext(request, {}, (request_processor,))
    else:
        context = RequestContext(request)
    return render_to_response('profile/view.html', d, context_instance=context)
