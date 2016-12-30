import textwrap
import tempfile
import os.path
import string
import re

from django.conf import settings
from django.utils import timezone

from .const import ROLEPERMISSION_VALUES

import logging
log = logging.getLogger('biogps_prod' if settings.RELEASE_MODE == 'prod' else 'biogps_dev')


# Misc. utility functions
def list2dict(list, keyitem, alwayslist=False):
    '''Return a dictionary with specified keyitem as key, others as values.
       keyitem can be an index or a sequence of indexes.
       For example: li=[['A','a',1],
                        ['B','a',2],
                        ['A','b',3]]
                    list2dict(li,0)---> {'A':[('a',1),('b',3)],
                                         'B':('a',2)}
       if alwayslist is True, values are always a list even there is only one item in it.
                    list2dict(li,0,True)---> {'A':[('a',1),('b',3)],
                                              'B':[('a',2),]}
    '''
    _dict = {}
    for x in list:
        if isinstance(keyitem, int):      # single item as key
            key = x[keyitem]
            value = tuple(x[:keyitem]+x[keyitem+1:])
        else:
            key = tuple([x[i] for i in keyitem])
            value = tuple(sublist(x, keyitem, mode='-'))
        if len(value) == 1:      # single value
            value = value[0]
        if key not in _dict:
            if alwayslist:
                _dict[key] = [value, ]
            else:
                _dict[key] = value
        else:
            current_value = _dict[key]
            if not isinstance(current_value, list):
                current_value = [current_value, ]
            current_value.append(value)
            _dict[key] = current_value
    return _dict


def sublist(list, idx, mode='+'):
    '''Return a sublist containing all elements with index specified in idx(a list of index) , if mode == '+'.
                                   all elements except those index sepecified in idx(a list of index) , if mode == '-'.
    '''
    if mode == '-':
        keepidx = range(len(list))
        for i in idx:
            keepidx.remove(i)
        return [list[i] for i in keepidx]
    else:
        return [list[i] for i in idx]


def list_nondup(list):
    x = {}
    for item in list:
        x[item] = None
    return x.keys()

class attrdict(dict):
    """A dict whose items can also be accessed as member variables.
        ref: http://code.activestate.com/recipes/361668/

    >>> d = attrdict(a=1, b=2)
    >>> d['c'] = 3
    >>> print d.a, d.b, d.c
    1 2 3
    >>> d.b = 10
    >>> print d['b']
    10

    # but be careful, it's easy to hide methods
    >>> print d.get('c')
    3
    >>> d['get'] = 4
    >>> print d.get('a')
    Traceback (most recent call last):
    TypeError: 'int' object is not callable

    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class dotdict(dict):
    def __getattr__(self, attr):
        value = self.get(attr, None)
        if type(value) is dict:
            return dotdict(value)
        else:
            return value
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def ask(prompt, options='YN'):
    '''Prompt Yes or No,return the upper case 'Y' or 'N'.'''
    options = options.upper()
    while 1:
        s = input(prompt+'[%s]' % '|'.join(list(options))).strip().upper()
        if s in options:
            break
    return s


def wrap_str(_str, max_len):
    """ Textwrap _str to provided max length """
    len_str = len(_str)
    if len_str > max_len and len_str > 3:
        _str = textwrap.wrap(_str, max_len - 3)[0] + '...'
    return _str


def alwayslist(value):
    """If input value if not a list/tuple type, return it as a single value list."""
    if isinstance(value, (list, tuple)):
        return value
    else:
        return [value]


def is_int(s):
    """return True or False if input string is integer or not."""
    try:
        int(s)
        return True
    except ValueError:
        return False

def is_admin_ip(addr):
    '''Given an IP address as a string, returns true if it matches a known developer IP.
    This check is only secure enough for basic uses, like toggling a notice.  It should NOT
    be used for any kind of security.'''
    return addr in settings.INTERNAL_IPS

def is_gnf_email(email):
    return email.lower().find('@gnf.org') != -1

def is_nov_email(email):
    _email = email.lower()
    return _email.find('@novartis.com') != -1 or _email.find('@chiron.com') != -1

def mkErrorReport(err):
    errfile = tempfile.mktemp(prefix='biogps_error_report_', dir=os.path.join(settings.ROOT_PATH, ".tmp"))
    err_f = open(errfile, 'w')
    err_f.write(err)
    err_f.close()
    return os.path.split(errfile)[1]

def is_valid_geneid(value):
    #digits only (NCBI) or start with ENS
    #return (type(value) is not types.StringType) and (value.isdigit() or value.startswith('ENS') or value.startswith('FBgn')) and len(value)<30

    #Either an integer or a string shorter than 30 char
    #return (value != '') and ((type(value) is types.IntType) or (type(value) in types.StringTypes and len(value)<30))

    #Either an integer or a string shorter than 30 char and within pre-defined char-set.
    chr_set = string.ascii_letters + string.digits + '_.-'
    pattern = re.compile('[{}]+$'.format(chr_set))
    return (isinstance(value, int) or (isinstance(value, str) and len(value) < 30 and re.match(pattern, value)))


def is_valid_parameter(value, maxlen=30):
    #allow digit, letter and hypen, understore
    import string
    return len(set(value) - set(string.ascii_letters+string.digits+'_-')) == 0 and len(value) <= maxlen


def setObjectPermission(object, roles=None, users=None, sep=','):
    '''
    A convenient function for set object role and user permissions.
       roles is a string for "shortcut" word defined in ROLEPERMISSION_VALUES,
               or can be multiple words seperated by sep.
                 e.g. 'myself', 'gnfusers, novartisusers'
               or can be special keywords:
                 'friendusers' or 'novartisusers'
            #TODO: need to expand to any role.

       users is a string with allowed usernames.
                 e.g. 'cwudemo', 'cwudemo1, cwuemo2'

            #TODO: need to check if user exists

       if both roles and users are None, existing permissions will be cleaned
    '''
    permissions = []
    if isinstance(roles, str):
        # Special handling for 'friends' since it's not really a role
        if roles.strip() == 'friendusers':
            permissions.append(dict(permission_type="F", permission_value=object.owner.username))
        else:
            # Special handling because 'novartisusers' implies both Novartis & GNF
            if roles.strip() == 'novartisusers':
                roles = 'gnfusers, novartisusers'

            for _rolepermission in roles.strip().split(','):
                rolepermission = ROLEPERMISSION_VALUES.get(_rolepermission.strip(), None)
                if rolepermission:
                    permissions.append(dict(permission_type="R", permission_value=rolepermission))

    if isinstance(users, str):
        for _user in users.strip().split(','):
            userpermission = _user.strip()
            if userpermission:
                permissions.append(dict(permission_type="U", permission_value=userpermission))
    if permissions:
        object.permission = permissions
    else:
        del object.permission

def cvtPermission(permission):
    '''    convert [{'R': 'GNF Users'}, {'U': 'cwu'}] into
            {'R': ['GNF Users'], 'U': ['cwu']}
    '''
    return list2dict([(x['permission_type'], x['permission_value']) for x in permission], 0, alwayslist=1)

def formatDateTime(o):
    '''Convert datatime object into a string representation as jsonserialier does.'''
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    if isinstance(o, timezone.datetime):
        return o.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))


if settings.DEBUG:
    def get_test_client():
        '''A shortcut for returning a django test client.'''
        from django.test.client import Client
        return Client()

    def get_sql_queries():
        '''A shortcut for raw sql queries.'''
        from django.db import connection
        return connection.queries
