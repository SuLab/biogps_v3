from django.test import Client
from biogps.test.utils import eq_, json_ok, page_match, content_match


def test_mystuff():
    c = Client()
    res = c.get('/mystuff/')
    eq_(res.status_code, 200)
    assert res.content.find('mystuff_panel') != -1


def test_tickermsgs():
    c = Client()
    res = c.get('/tickermsgs/')
    json_ok(res)


def test_alt_layouts():
    alt_layouts = ['cgdtissuesurvey', 'circadian', 'genewiki',
                   'genewikigenerator', 'naturedb']
    c = Client()
    for i in alt_layouts:
        res = c.get('/%s/' % i)
        eq_(res.status_code, 200)
        assert res.content.find('biogps.alt_defaultlayout')!=-1, i

    # Test arbitrary alt_layout
    res = c.get('/?layout=83')
    eq_(res.status_code, 200)
    assert res.content.find('biogps.alt_defaultlayout = 83')!=-1
    res = c.get('/?layout=foo')   #invalid value
    eq_(res.status_code, 200)
    assert res.content.find('biogps.alt_defaultlayout')==-1

    # Test missing/bad layout as well
    res = c.get('/missinglayout/')
    eq_(res.status_code, 404)


def test_alt_dataset():
    c = Client()
    res = c.get('/?dataset=100')
    eq_(res.status_code, 200)
    assert res.content.find('biogps.alt_defaultdataset = 100')!=-1

    res = c.get('/?dataset=foo')
    eq_(res.status_code, 200)
    assert res.content.find('biogps.alt_defaultdataset')==-1


def test_flatpages():
    c = Client()
    flatpages = ['about', 'terms', 'help', 'help_steps', 'help_openid',
                  'screencasts', 'faq', 'downloads', 'iphone']
    for page in flatpages:
        res = page_match(c, '/%s/' % page, 'Scripps')
        if page == 'faq':
            #test Species data are passed into /faq page correctly
            content_match(res, 'Homo sapiens')
