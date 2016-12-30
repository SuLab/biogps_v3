from django.test import Client
from biogps.test.utils import ok_, eq_, json_ok, ext_ok


def test_gene():
    c = Client()
    res = c.get('/gene/1017/')
    eq_(res.status_code, 302)
    ok_('Location' in res)
    ok_(res['Location'].find('#goto=genereport') !=-1)


def test_gene_bot():
    c = Client()
    res = c.get('/gene/bot/1017/')
    eq_(res.status_code, 200)
    assert res.content.find("cyclin-dependent kinase 2") != -1
    assert res.content.find("GeneAtlas U133A, gcrma") != -1


def test_redirect():
    c = Client()
    # ref for adding extra headers to test client:
    #     http://djangosnippets.org/snippets/850/
    res = c.get('/gene/1017/', **{'HTTP_USER_AGENT': "Googlebot/2.1"})
    eq_(res.status_code, 200)