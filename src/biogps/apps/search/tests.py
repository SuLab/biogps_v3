from django.test import Client
from biogps.test.utils import (json_ok, nottest, get_user_context,  _d, _e,
                               ok_, eq_,ext_ok, ext_fail)



def test_query():
    c = Client()
    res = c.get('/search/?q=cdk2')
    eq_(res.status_code, 302)
    ok_(res['Location'].endswith('?query=cdk2'))
    for url in ['/search/plugin/?q=cancer',
                '/search/layout/?q=pathway',
                '/search/?q=cancer&in=plugin',
                '/search/?q=pathway2&in=layout',
                '/search/?q=cancer&in=dataset',
                '/search/?q=cancer&in=plugin,gene',
                '/search/plugin/?q=cancer&from=10&size=10',
                '/search/plugin/?q=cancer&sort=id',
                '/search/plugin/?q=cancer&sort=popular',
                '/search/plugin/?q=cancer&sort=newest',
                '/search/dataset/?q=cancer&sort=popular',
                '/search/dataset/?q=cancer&sort=newest',

                ]:
        url += '&format=json'
        print url
        res = c.get(url)
        json_ok(res)


def test_mapping():
    pass


def test_status():
    c = Client()
    res = c.get('/search/status/')
    json_ok(res)

    res = c.head('/search/status/')
    eq_(res.status_code, 200)


def test_interval_query():
    pass
