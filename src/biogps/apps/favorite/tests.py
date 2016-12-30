from django.test import Client
from biogps.test.utils import eq_, json_ok


def test_favorite_submit():
    c = Client()
    c.login(username='cwudemo', password='123')
    res = c.post('/favorite/plugin/9/', {'choice': 'true'})
    eq_(res.status_code, 200)
    json_ok(res)
