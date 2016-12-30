from biogps.test.utils import eq_, get_user_context, json_ok


def test_rating_submit():
    c = get_user_context()
    res = c.post('/rating/plugin/641/', {'rating': '5'})
    eq_(res.status_code, 200)
    json_ok(res)
