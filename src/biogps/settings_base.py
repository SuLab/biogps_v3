# Django settings for biogps project.
# This file contains common settings for two specific settings files:
#         settings_dev.py         (for dev server)
#         settings_prod.py        (for prod server)
#

import os.path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'rest_framework',
    'tagging',
    'flag',
    'django_extensions',

    #'django_authopenid',
    'urlauth',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.openid',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.twitter',
    'allauth.socialaccount.providers.orcid',

    #our own biogps apps
    'biogps.apps.auth2',
    'biogps.apps.gene',
    'biogps.apps.plugin',
    'biogps.apps.layout',
    'biogps.apps.bgprofile',
    'biogps.apps.search',
    'biogps.apps.rating',
    'biogps.apps.favorite',
    'biogps.apps.www',

)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'biogps.urls'

TEMPLATES_00 = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'biogps', 'apps', 'templates'),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                #'biogps.utils.context_processors.base_processor',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                #'biogps.utils.template.BiogpsLoader',
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]

WSGI_APPLICATION = 'biogps.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

######BioGPS specific settings#########
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

##Get the current version info
import subprocess, os
cwd = os.getcwd()
os.chdir(ROOT_PATH)
git_cmd = "git rev-parse --short HEAD"
BIOGPS_VERSION = subprocess.check_output(git_cmd.split())
os.chdir(cwd)

try:
    import uwsgi
    USE_UWSGI = True
except ImportError:
    USE_UWSGI = False


# Caching with memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# Cache times in seconds
CACHE_DAY = 86400
CACHE_WEEK = 604800


BOT_HTTP_USER_AGENT = ('Googlebot', 'msnbot', 'Yahoo! Slurp')    #The string appearing in HTTP_USER_AGENT header to indicate it is from a web crawler.

# Used in middleware/maintenance.py
MAINTENANCE_PAGE = os.path.join(ROOT_PATH,'src/assets/maintenance.html')

#used in user_tags.py of biogps.app.friends
ACCOUNT_USER_DISPLAY = lambda u: u.get_full_name() or u.username

##ElasticSearch settings
#ES_HOST = ['localhost:9500']   # this is defined in settings_dev.py or settings_prod.py files.
ES_INDEX_NAME = 'biogps'
ES_AVAILABLE_TYPES = {'gene':    {
                                  #The default facets for a specific type
                                  'facets':['_type', 'species'],
                                 },
                      'plugin':  {
                                 'facets':['_type', 'species', 'tag'],
                                 },
                      'layout':  {
                                 'facets':['_type', 'species', 'tag'],
                                 },
                      'genelist':{
                                 'facets':['_type', 'species', 'tag'],
                                 }
                     }
ES_MAX_QUERY_LENGTH = 1000
SUSPEND_ES_UPDATE = False   #set to True if you want to suspend syncing ES index with BioGPS model objects, e.g. when running tests.


######Django specific settings#########
PERSISTENT_SESSION_KEY = 'sessionpersistent'     #used by 'biogps.middleware.DualSession.DualSessionMiddleware'
#SESSION_COOKIE_SECURE = True

AUTHENTICATION_BACKENDS = (
 'django.contrib.auth.backends.ModelBackend',
)

LOGIN_URL = '/auth/login'

AUTH_PROFILE_MODULE = "auth2.UserProfile"

#SERIALIZATION_MODULES = {
#    'myjson': 'biogps.utils.jsonserializer',
#    'jsonfix': 'biogps.utils.jsonserializer2',
#    "extdirect" : "extdirect.django.serializer",
#}


# Absolute path to the directory that holds media.
MEDIA_ROOT = os.path.join(ROOT_PATH, 'src/assets/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/assets/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS_0 = (
    'django.template.loaders.filesystem.Loader',
    'biogps.utils.template.app_prefixed_loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS_0 = ( "django.contrib.auth.context_processors.auth",
                                "django.contrib.messages.context_processors.messages",
                                "django.core.context_processors.debug",
                                "django.core.context_processors.i18n",
                                "django.core.context_processors.media",
                                "django.core.context_processors.request",
                                "biogps.utils.context_processors.base_processor")

MIDDLEWARE_CLASSES_0 = (
    'django.middleware.gzip.GZipMiddleware',
    'biogps.middleware.trimhtml.SpacelessMiddleware',
    'biogps.middleware.maintenance.MaintenanceMiddleware',
    'django.middleware.common.CommonMiddleware',
#    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.middleware.csrf.CsrfResponseMiddleware',
    'biogps.middleware.csrf.CsrfViewMiddleware',
    'biogps.middleware.csrf.CsrfResponseMiddleware',

    #'django.contrib.sessions.middleware.SessionMiddleware',
    'biogps.middleware.DualSession.DualSessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django_authopenid.middleware.OpenIDMiddleware',
    'urlauth.middleware.AuthKeyMiddleware',
    'pagination.middleware.PaginationMiddleware',
    'breadcrumbs.middleware.BreadcrumbsMiddleware'
)

TEMPLATE_DIRS_0 = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ROOT_PATH, 'src/biogps/templates'),
)


INSTALLED_APPS_0 = (
    #Django's buildin apps
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.admindocs',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.comments',

    #third-party apps
    'tagging',
    'flag',
    "pagination",
    "emailconfirmation",
    "notification",
    "friends",
    "timezones",
    "authsub",
    "bbauth",
    'threadedcomments',
    'compress',
    'django_extensions',
    'django_authopenid',
    'urlauth',
    'account',
    'uwsgi_admin',

    #our own biogps apps
    'biogps.www',
    'biogps.apps.auth2',
    'biogps.apps.dataset',
    'biogps.apps.gene',
    'biogps.apps.plugin',
    'biogps.apps.layout',
    'biogps.apps.genelist',
    'biogps.apps.mobile',
    'biogps.apps.ext_plugins',
    'biogps.apps.utils',
    'biogps.apps.bgprofile',
    'biogps.apps.friends',
    'biogps.apps.comment',
    'biogps.apps.rating',
    'biogps.apps.favorite',
    'biogps.apps.stat',
    'biogps.apps.search',
)

# Sensitive settings get imported here.
from .settings_private import *




######Third-party Django Apps specific settings#########

## django_account
#from urlauth.settings import *
#from account.settings import *
#ACCOUNT_REGISTRATION_FORM = 'biogps.apps.auth2.forms.RegistrationForm'


## django_tagging
FORCE_LOWERCASE_TAGS = True
MAX_TAG_LENGTH = 50


REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
        #'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ]
}
