from django.test import Client
from biogps.test.utils import (nottest, get_user_context,  _d, _e,
                               ok_, eq_,ext_ok, ext_fail)
from biogps.layout.models import BiogpsGenereportLayout

_test_layout_data = '''
    [{"width": 969, "useroptions": null, "top": 872, "left": 10, "id": 7, "height": 329},
    {"width": 529, "useroptions": null, "top": 0, "left": 10, "id": 9, "height": 829},
    {"width": 969, "useroptions": null, "top": 1244, "left": 10, "id": 10, "height": 405},
    {"width": 441, "useroptions": null, "top": 0, "left": 542, "id": 73, "height": 828}]'''

_test_layout =  {'layout_name': 'nosetest_layout',
                 'layout_data': _d(_test_layout_data),
                 'description': 'test_description'}


@nottest
def _create_test_layout():
    '''create a test plugin based on _plugin_data.'''
    from django.contrib.auth.models import User

    _cleanup_test_layout()

    test_layout = _test_layout.copy()
    test_layout['layout_data'] = _e(test_layout['layout_data'])
    user = User.objects.get(username='cwudemo')
    layout = BiogpsGenereportLayout(layout_name=_test_layout['layout_name'],
                                    ownerprofile=user.profile,
                                    description=_test_layout['description'])
    layout.save()
    layout.layout_data = _test_layout['layout_data']
    return layout.id


@nottest
def _cleanup_test_layout():
    '''remove created test layout.'''
    BiogpsGenereportLayout.objects.filter(layout_name=_test_layout['layout_name']).delete()


@nottest
def teardown_test_environment():
    _cleanup_test_layout()


def test_layout_list():
    #Anonymous
    c = Client()
    res = c.get('/layoutlist/all/', dict(userselected=1))
    eq_(res.status_code, 200)
    d = _d(res.content)
    ok_(d["totalCount"]>=8, d["totalCount"])

   # use default cwudemo account
    c = get_user_context()
    res = c.get('/layoutlist/all/', dict(userselected=1))
    _d(res.content)


def test_layout_get():
    #/layout/<id>
    c = Client()
    res = c.get('/layout/83/', dict(loadplugin=1))
    eq_(res.status_code,200)
    d = _d(res.content)
    eq_(d['items'][0]['pk'], 83)

    d = d['items'][0]['fields']['layout_data']
    eq_(len(d), 3)
    eq_(d[0]['title'], 'Gene expression/activity chart')
    attrs_li = ['description', 'useroptions', 'author', 'author_url', 'url',
                'lastmodified', 'top', 'title', 'height', 'width', 'id',
                'type', 'options', 'left', 'species']
    ok_(set([str(x) for x in d[0].keys()]) == set([str(x) for x in attrs_li]),
        (set([str(x) for x in d[0].keys()]) - set([str(x) for x in attrs_li]),
         set([str(x) for x in attrs_li]) - set([str(x) for x in d[0].keys()])))


def test_layout_add():
    #For layout_add
    BiogpsGenereportLayout.objects.filter(layout_name=_test_layout['layout_name']).delete()

   # use default cwudemo account
    c = get_user_context()
    test_layout = _test_layout.copy()
    test_layout['layout_data'] = _e(test_layout['layout_data'])
    res = c.post('/layout/add/', test_layout)
    ext_ok(res)

    #test save with dup name
    res = c.post('/layout/add/', test_layout)
    ext_fail(res)

    _cleanup_test_layout()


def test_layout_update():
    #test layout_update
    new_layout_id = _create_test_layout()

    c = get_user_context()
    res = c.post('/layout/update/', dict(layout_id=new_layout_id,
                                         layout_name='nosetest_layout_2'))
    ext_ok(res)

    c = get_user_context()
    res = c.post('/layout/update/', dict(layout_id=new_layout_id,
                                         description='test description_2'))
    ext_ok(res)

    c = get_user_context()
    res = c.post('/layout/update/', dict(layout_id=new_layout_id,
                                         layout_data=_e(_test_layout['layout_data'][:-1])))
    ext_ok(res)

    c = get_user_context()
    res = c.post('/layout/update/', dict(layout_id=new_layout_id,
                                         rolepermission='biogpsusers'))
    ext_ok(res)

    c = get_user_context()
    res = c.post('/layout/update/', dict(layout_id=new_layout_id,
                                         layout_name='nosetest_layout',
                                         layout_data=_test_layout_data,
                                         rolepermission='myself',
                                         description='test description'))
    ext_ok(res)

    #For layout_update with null or missing position/size parameters
    data =  '[{"width":null,"useroptions":null,"top":null,"left":null,"id":73,"height":null}, {"id":71}]'
    c = get_user_context()
    res = c.post('/layout/update/', dict(layout_id=new_layout_id,
                                         layout_data=_test_layout_data,
                                         description=u''))
    ext_ok(res)

    #For layout_update with negative position/size parameters
    data =  '[{"id":73,"left":-1,"top":2,"height":499,"width":348}, \
              {"id":71,"left":-1,"top":503,"height":250,"width":350}]'
    c = get_user_context()
    res = c.post('/layout/update/', dict(layout_id=new_layout_id,
                                         layout_data=data))
    ext_ok(res)

    _cleanup_test_layout()


def test_layout_delete():
    #test layout_delete
    new_layout_id = _create_test_layout()
    c = get_user_context()
    res = c.post('/layout/delete/', dict(layout_id=new_layout_id))
    ext_ok(res)

    _cleanup_test_layout()
