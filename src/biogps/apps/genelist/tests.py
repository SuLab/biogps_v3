import copy
from biogps.test.utils import (nottest, get_user_context,
                               eq_, ok_, _d, _e, json_ok, ext_ok, ext_fail)
from django.contrib.auth.models import User
from biogps.genelist.models import BiogpsGeneList


_test_genelist_list = [dict(name='nosetest_genelist_1',
                           data=["113", "119", "1510", "1633", "1654", "2039",
                                 "3386", "3783"]),
                      dict(name='nosetest_genelist_2',
                           data=["113", "119", "2039", "3386", "6521", "6954",
                                 "7037", "3783"]),
                      dict(name='nosetest_genelist_3',
                           data=["365601", "390916", "391059", "730528",
                                 "ENSMUSG00000020527", "ENSMUSG00000024528"])]


@nottest
def _create_test_genelist(i=0):
    '''create a test genelist based on _test_genelist_list[i].'''
    s = _test_genelist_list[i]
    user = User.objects.get(username='cwudemo')
    genelist = BiogpsGeneList(name=s['name'],
                            data=s['data'],
                            size=len(s['data']),
                            ownerprofile=user.profile)
    genelist.save()
    return genelist.id


@nottest
def _cleanup_test_genelist():
    '''remove created test genelists.'''
    user = User.objects.get(username='cwudemo')
    BiogpsGeneList.objects.filter(name__startswith='nosetest_genelist',
                                 ownerprofile=user.profile.sid).delete()


@nottest
def teardown_test_environment():
    _cleanup_test_genelist()


def test_genelist_get():
    #/genelist/<id>/?geneinfo=1 via GET
    _cleanup_test_genelist()
    s1 = _test_genelist_list[0]
    id1 = _create_test_genelist(0)
    c = get_user_context()
    res = c.get('/geneset/%d/' % id1)
    eq_(res.status_code, 200)
    obj = _d(res.content)
    for k in ['name', 'data', 'size', 'author', 'description', 'options',
              'permission', 'tags']:
        assert k in obj, 'Attribute "%s" not found in genelist "%s".' % (k, id1)
    res = c.get('/geneset/%d/' % id1, dict(geneinfo=1))
    eq_(res.status_code, 200, res.content)
    obj = _d(res.content)
    eq_(len(obj['data']), len(s1['data']))
    for k in ['symbol', 'taxid', 'id', 'name']:
        assert k in obj['data'][0], 'Attribute "%s" not found in genelist "%s".' % (k, id1)


def test_genelist_add():
    #/genelist/ add via POST

    #Remove existing ones if any
    _cleanup_test_genelist()
    s1, s2, s3 = copy.deepcopy(_test_genelist_list)
    s1['data'] = _e(s1['data'])
    s2['data'] = _e(s2['data'])
    s3['data'] = _e(s3['data'])

    c = get_user_context()
    res = c.post('/geneset/', s1)
    ext_ok(res)

    c = get_user_context()
    res = c.post('/geneset/', s2)
    ext_ok(res)

    c = get_user_context()
    res = c.post('/geneset/', s3)
    ext_ok(res)

    _cleanup_test_genelist()


def test_genelist_update():
    #/genelist/<id>/ update via PUT
    s1 = _test_genelist_list[0]
    _cleanup_test_genelist()
    id1 = _create_test_genelist(0)

    c = get_user_context()
    res = c.put('/geneset/%d/' % id1, dict(name='nosetest_genelist_1_new',
                                           data=_e(s1['data']),
                                           description='test description',
                                           rolepermission='gnfusers'))
    ext_ok(res)

    _cleanup_test_genelist()


def test_genelist_union():
    #/genelist/union/
    s1, s2, s3 = copy.copy(_test_genelist_list)
    _cleanup_test_genelist()
    id1 = _create_test_genelist(0)
    id2 = _create_test_genelist(1)

    c = get_user_context()
    res = c.post('/geneset/union/', dict(genelistid=[id1, id2]))
    ext_ok(res)
    eq_(sorted(set(_d(res.content)['genes'])),
        sorted(set(s1['data']) | set(s2['data'])))

    res = c.post('/geneset/union/', dict(genelistid=[id1, id2], geneinfo=1))
    ext_ok(res)
    obj = _d(res.content)
    for k in ['symbol', 'taxid', 'id', 'name']:
        assert k in obj['genes'][0], 'Attribute "%s" not found in genelist "%s".' % (k, id1)

    res = c.post('/geneset/union/', dict(genelistid=[id1, id2], validate=1))
    ext_ok(res)

    res = c.post('/geneset/union/', dict(genelistid=[id1, id2], saveasnew=1))
    ext_ok(res)
    new_genelist_id = _d(res.content)['genelist_id']

    #cleanup
    BiogpsGeneList.objects.get(id=new_genelist_id).delete()

def test_genelist_intersection():
    #/genelist/intersection/
    s1, s2, s3 = copy.copy(_test_genelist_list)
    _cleanup_test_genelist()
    id1 = _create_test_genelist(0)
    id2 = _create_test_genelist(1)

    c = get_user_context()
    res = c.post('/geneset/intersection/', dict(genelistid=[id1, id2]))
    ext_ok(res)
    eq_(sorted(set(_d(res.content)['genes'])),
        sorted((set(s1['data']) & set(s2['data']))))

    res = c.post('/geneset/intersection/', dict(genelistid=[id1, id2],
                                                geneinfo=1))
    ext_ok(res)
    obj = _d(res.content)
    for k in ['symbol', 'taxid', 'id', 'name']:
        assert k in obj['genes'][0], 'Attribute "%s" not found in genelist "%s".' % (k, id1)

    res = c.post('/geneset/intersection/', dict(genelistid=[id1, id2],
                                                validate=1))
    ext_ok(res)

    res = c.post('/geneset/intersection/', dict(genelistid=[id1, id2],
                                                saveasnew=1))
    ext_ok(res)
    new_genelist_id = _d(res.content)['genelist_id']
    #cleanup
    BiogpsGeneList.objects.get(id=new_genelist_id).delete()


def test_genelist_delete():
    #/genelist/<id>/ delete via DELETE
    _cleanup_test_genelist()
    id1 = _create_test_genelist(0)
    c = get_user_context()
    res = c.delete('/geneset/%d/' % id1)
    ext_ok(res)


def test_get_mygenelists():
    #/getmygenelists
    c = get_user_context()
    res = c.get('/getmygenesets/')
    json_ok(res)

    c.logout()
    res = c.get('/getmygenesets/')
    ext_fail(res)


def test_genelist_export():
    #/genelist/download?genelistid=23&genelistid=25
    c = get_user_context()
    res = c.get('/geneset/download/?genelistid=23&genelistid=25')
    eq_(res['content-type'], 'text/csv')
    ok_(res.has_header('content-disposition'))
    eq_(len(set([line.split(',')[1] for line in res.content.split('\r\n')])), 2)

