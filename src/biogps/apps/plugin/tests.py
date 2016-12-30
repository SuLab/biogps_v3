from django.test import Client
from biogps.test.utils import (nottest, istest, get_user_context,
                               eq_, _d, ext_ok, ext_fail)
from biogps.plugin.models import BiogpsPlugin


_plugin_data = {"title": "nosetest_plugin",
        "url": "http://www.google.com/search?q={{Symbol}}",
        "type": "iframe",
        "description": "test decription",
        "rolepermission": "biogpsusers",
        "tags": "google gene test"}


@nottest
#def _create_test_plugin():
#    '''create a test plugin based on _plugin_data.'''
#    data = _plugin_data.copy()
#    #clean up existing ones if any
#    BiogpsPlugin.objects.filter(title=data['title'], url=data['url']).delete()
#    data.update({'allowdup': '1'})
#    c = get_user_context()
#    res = c.post('/plugin_v1/add/', data)
#    ext_ok(res)
#    new_plugin_id = _d(res.content)['plugin_id']
#    time.sleep(5)
#    print new_plugin_id, BiogpsPlugin.objects.filter(title=data['title'],
#                                                     url=data['url']).count()
#    return new_plugin_id


@nottest
def _create_test_plugin():
    '''create a test plugin based on _plugin_data.'''
    from django.contrib.auth.models import User
    data = _plugin_data.copy()
    #clean up existing ones if any
    BiogpsPlugin.objects.filter(title=data['title'], url=data['url']).delete()

    user = User.objects.get(username='cwudemo')
    plugin = BiogpsPlugin(title=data['title'],
                          url=data['url'],
                          type=data['type'],
                          ownerprofile=user.profile,
                          description=data['description'])
    plugin.save()
#    setObjectPermission(plugin, data['rolepermission'])
#    plugin.tags = data['tags']
    return plugin.id


@nottest
def _cleanup_test_plugin():
    '''remove created test plugin.'''
    BiogpsPlugin.objects.filter(title=_plugin_data['title'],
                                url=_plugin_data['url']).delete()


@nottest
def teardown_test_environment():
    _cleanup_test_plugin()


#==============================================================================
# test functions starts here
#==============================================================================
def test_plugin_browse():
    c = Client()
    res = c.get('/plugin_v1/browse/')
    eq_(res.status_code, 200)


def test_plugin_get():
    c = Client()
    res = c.get('/plugin_v1/10/')
    eq_(res.status_code, 200)
    d = _d(res.content)
    eq_(d['items'][0]["pk"], 10)
    eq_(d['items'][0]["fields"]["title"], "Gene Wiki")


def test_plugin_search():
    c = Client()
    res = c.get('/plugin_v1/', dict(search="gene", scope="all", start=0,
                                 limit=50, dir='DESC', sort='popularity'))
    eq_(res.status_code, 200)
    d = _d(res.content)
    assert 'totalCount' in d
    assert 'items' in d


def test_plugin_add():
    #plugin_add

    c = get_user_context()
    data = _plugin_data

    #clean up existing ones if any
    BiogpsPlugin.objects.filter(title=data['title'], url=data['url']).delete()
    res = c.post('/plugin_v1/add/', data)
    #failed due to duplicated URL
    ext_fail(res)
    assert 'dup_plugins' in _d(res.content)
    #c.logout()

    #re-submit with allowdup as true
    c = get_user_context()
    _data = {'allowdup': '1'}
    _data.update(data)
    res = c.post('/plugin_v1/add/', _data)
    ext_ok(res)
#    new_plugin_id = _d(res.content)['plugin_id']

    #test with dup title
    c = get_user_context()
    res = c.post('/plugin_v1/add/', data)
    ext_fail(res)

    _cleanup_test_plugin()


def test_plugin_update():
    #plugin_upate
    new_plugin_id = _create_test_plugin()
    data = _plugin_data.copy()
    data['plugin_id'] = new_plugin_id
    data['description'] = 'another description'
    c = get_user_context()
    res = c.post('/plugin_v1/update/', data)
    ext_ok(res)
    _cleanup_test_plugin()


def test_plugin_delete():
    #plugin_delete
    new_plugin_id = _create_test_plugin()
    c = get_user_context()
    res = c.post('/plugin_v1/delete/', dict(plugin_id=new_plugin_id))
    ext_ok(res)


def test_plugin_usage():
    #/plugin_v1/<id>/usage/
    c = Client()
    res = c.get('/plugin_v1/10/usage/')
    eq_(res.status_code, 200)
    eq_(len(_d(res.content)), 2)


def test_plugin_flag():
    #/plugin_v1/<id>/flag/

#    test_plugin_id = _create_test_plugin()
#    print BiogpsPlugin.objects.get(id=test_plugin_id)
#    c = get_user_context()
#    print c.session.values()
#    print test_plugin_id
    from django.conf import settings
    test_plugin_id = 10
    c = get_user_context()
    res = c.post('/plugin_v1/%s/flag/' % test_plugin_id, dict(reason="broken", comment="This plugin is broken"))
    ext_ok(res)
    c = get_user_context()
    print c.session.values()
    res = c.post('/plugin_v1/%s/flag/' % test_plugin_id, dict(reason="inappropriate", comment=""))
    ext_ok(res)

    _cleanup_test_plugin()
    c.logout()
