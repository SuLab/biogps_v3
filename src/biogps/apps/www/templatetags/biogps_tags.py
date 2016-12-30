import types

from django.utils import timezone
from django.conf import settings
from django.template.base import Library

register = Library()


@register.simple_tag
def jqueryjsfiles():
    MAIN_JAVASCRIPT_PROD = '''
    <script type="text/javascript" src="/assets/js/jquery/jquery-%(jqver)s.min.js"></script>
    '''

    MAIN_JAVASCRIPT_DEBUG = '''
    <script type="text/javascript" src="/assets/js/jquery/jquery-%(jqver)s.js"></script>
    '''

    if settings.DEBUG:
        main_javascript = MAIN_JAVASCRIPT_DEBUG % {'jqver': settings.JQUERY_VERSION}
    else:
        main_javascript = MAIN_JAVASCRIPT_PROD % {'jqver': settings.JQUERY_VERSION}

    return main_javascript


@register.simple_tag
def extcorejsfile():
    extcorejs = '''
    <script type="text/javascript" src="/assets/js/ext/%(extver)s/ext-core.js"></script>
    '''
    return extcorejs % {'extver': settings.EXT_VERSION}


@register.simple_tag
def extcssfiles():
    extcss = '''
    <link rel="stylesheet" type="text/css" href="/assets/js/ext/%(extver)s/resources/css/ext-all.css" />
    '''
    return extcss % {'extver': settings.EXT_VERSION}


@register.simple_tag
def biogps_ver():
    '''return a current biogps version number.
      e.g. ver 0.9.7.2964
    '''
    return 'ver ' + settings.BIOGPS_VERSION


@register.simple_tag
def this_year():
    '''return the current year.
       used to alleviate the need to update the copyright notice every year.
    '''
    return timezone.now().year


@register.simple_tag
def rating_percentage(rating=5):
    return rating / 5.0 * 100


@register.simple_tag
def emailus(text="'+ out.join('') +'"):
    '''return a email link to biogps@googlegroups.com, which prevents email spoofing.
       if no text variable is supplied, it will output the email address.

       convert a normal string: ''.join([chr(ord(x)-8) for x in s])

       'help@biogps.org' = '`]dh8Zag_hk&gj_'
       'biogps@googlegroups.com'  ==> 'Zag_hk8_gg_d]_jgmhk&[ge'
    '''
    tpl = """<span id='emailuslink'></span>
<script>
var _addr = 'Zag_hk8_gg_d]_jgmhk&[ge';
var out = [];
for (var i=0;i<_addr.length;i++){
    out.push(String.fromCharCode(_addr.charCodeAt(i)+8));
}
var e = document.getElementById('emailuslink');
e.innerHTML = '<a href="mailto:' + out.join('') + '">' + '%s' + '</a>';
</script>"""
    return (tpl % text).replace('\n', '')


@register.simple_tag
def emailus2(text="'+ out.join('') +'"):
    '''return a email link to help@biogps.org, which prevents email spoofing.
       if no text variable is supplied, it will output the email address.

       convert a normal string: ''.join([chr(ord(x)-8) for x in s])

       'help@biogps.org' = '`]dh8Zag_hk&gj_'
       'biogps@googlegroups.com'  ==> 'Zag_hk8_gg_d]_jgmhk&[ge'
    '''
    tpl = """<span id='emailus2link'></span>
<script>
var _addr = '`]dh8Zag_hk&gj_';
var out = [];
for (var i=0;i<_addr.length;i++){
    out.push(String.fromCharCode(_addr.charCodeAt(i)+8));
}
var e = document.getElementById('emailus2link');
e.innerHTML = '<a href="mailto:' + out.join('') + '">' + '%s' + '</a>';
</script>"""
    return (tpl % text).replace('\n', '')


@register.simple_tag
def ga_header(usertype=None):
    '''!!This is deprecated after upgraded to Google Universal Analytics!!
       usertype is a optional custom variable for something like
       Anonymous, BioGPS User, GNF User, Novartis User
       This makes use of Google Analytics Custom Variables
       http://code.google.com/apis/analytics/docs/tracking/gaTrackingCustomVariables.html
    '''
    trackercode = '''<script type="text/javascript">
        var _gaq = _gaq || [];
        _gaq.push(['_setAccount', '%s']);'''
    trackercode = trackercode % settings.GA_ACCOUNT
    if usertype:
        trackercode += "_gaq.push(['_setCustomVar', 1, 'UserType', '%s', 2]);" % usertype
    trackercode += '''_gaq.push(['_trackPageview']);
        </script>'''
    return trackercode


@register.simple_tag
def ga(usertype=None):
    '''usertype is a optional custom variable for something like
       Anonymous, BioGPS User, GNF User, Novartis User
       This makes use of Google Universal Analytics Custom Metrics tracking
       https://developers.google.com/analytics/devguides/collection/analyticsjs/custom-dims-mets
    '''
    if settings.RELEASE_MODE == 'dev':
        trackercode = '<script>var ga=function(){};</script>'
    else:
        trackercode = '''<script>
    (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
    (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
    m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
    })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
    '''
        trackercode += "ga('create', '{}', 'biogps.org');\n".format(settings.GA_ACCOUNT)
        trackercode += "ga('send', 'pageview');\n"
        if usertype:
            trackercode += "ga('set', 'UserType', '{}');\n".format(usertype)
        trackercode += '</script>'
    return trackercode


@register.simple_tag
def biogpstips():
    '''return a javascript array for tips.'''
    from biogps.www.models import BiogpsTip
    return '[' + ', '.join(['"' + tip.html.strip().replace('"', '\\"') + '"' for tip in BiogpsTip.objects.all().order_by('id')]) + ']'


@register.simple_tag
def extdirect_api():
    '''return a block of js code contains dynamic extdirect descriptor.'''
    from biogps.extdirect.views import remote_provider
    js_code = '<script type="text/javascript">%s    </script>' % remote_provider.api2()
    return js_code


@register.simple_tag
def sample_geneid(species=None):
    """return a proper sample gene id based on first species setting.
       sepcies can be a string or a list (take the first one).
    """
    from biogps.utils import const
    if species:
        if type(species) is types.ListType and len(species) > 0:
            _species = species[0]
        else:
            _species = species
        sample_gene = const.sample_gene.get(_species, 1017)
    else:
        sample_gene = 1017
    return sample_gene
