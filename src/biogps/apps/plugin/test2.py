from django.test import Client
from biogps.test.utils import (nottest, istest, get_user_context,
                               eq_, _d, json_ok, xml_ok, ext_ok, ext_fail)
from biogps.plugin.models import BiogpsPlugin


_plugin_data = {"title": "nosetest_plugin",
                "url": "http://www.google.com/search?q={{Symbol}}",
                "type": "iframe",
                "description": "test decription",
                "rolepermission": "biogpsusers",
                "tags": "google gene test"}

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
def test_plugin_get():
    c = Client()
    res = c.get('/plugin/10/')
    eq_(res.status_code, 200)

    res = c.get('/plugin/10/?format=json')
    d = json_ok(res)
    eq_(d["id"], 10)
    eq_(d["name"], "Gene Wiki")

    res = c.get('/plugin/10/?format=xml')
    xml_ok(res)


def test_plugin_update():
    #plugin_upate
    new_plugin_id = _create_test_plugin()
    data = _plugin_data.copy()
    data['plugin_id'] = new_plugin_id
    data['description'] = 'another description'
    c = get_user_context()
    res = c.put('/plugin/%s/' % new_plugin_id, data)
    ext_ok(res)
    _cleanup_test_plugin()


def test_plugin_delete():
    #plugin_delete
    new_plugin_id = _create_test_plugin()
    c = get_user_context()
    res = c.delete('/plugin/%s/' % new_plugin_id,
                   dict(plugin_id=new_plugin_id))
    ext_ok(res)

