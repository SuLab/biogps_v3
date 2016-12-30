from django.db import models
from django.conf import settings
from biogps.utils.fields.jsonfield import JSONField

OBJECT_TYPE_CHOICES = (
    ('P', 'Plugin'),
    ('L', 'Layout'),
    ('G', 'Genelist'),
    ('D', 'Dataset'),
)

#Mapping object_type to model
#Temp solution here, eventually BiogpsPermission model should be switched
# to use content_type instead
OBJECT_MODEL_MAPPING = {
    'P': ('www', 'biogpsplugin'),
    'L': ('www', 'biogpsgenereportlayout'),
    'G': ('www', 'biogpsgenelist'),
    'D': ('dataset', 'biogpsdataset'),
}

PERMISSION_TYPE_CHOICES = (
    ('R', 'Role'),     # all users with this roles gain the access
    ('U', 'User'),     # specified user gains the access
    ('F', 'Friends'),  # all friends of specified user gains the access
)


class BiogpsPermission(models.Model):
    object_type = models.CharField(max_length=5, choices=OBJECT_TYPE_CHOICES)
    object_id = models.IntegerField()
    permission_type = models.CharField(max_length=2,
                                       choices=PERMISSION_TYPE_CHOICES)
    permission_value = models.CharField(max_length=100)

#    class Meta:
#        unique_together = (('object_type', 'object_id'),)

    @staticmethod
    def get_model(object_type):
        '''Return the corresponding model based on object_type value.'''
        app_label, model_name = OBJECT_MODEL_MAPPING.get(object_type, (None, None))
        if app_label and model_name:
            return models.get_model(app_label, model_name)
        else:
            return None

class BiogpsTip(models.Model):
    html = models.TextField()


class BiogpsRootnode(models.Model):
    '''Stores the rootnode and its corresponding geneids, used for generating
       sitemap.xml
    '''
    id = models.CharField(max_length=50, primary_key=True)
    data_source = models.CharField(max_length=50)
    data_source_rank = models.IntegerField()
    root_node = models.IntegerField()
    flag = models.IntegerField(blank=True)

    def __unicode__(self):
        return u'GeneID "%s"' % self.id

    def get_absolute_url(self):
        return '/gene/%s/' % self.id


class BiogpsInfobox(models.Model):
    # Store info box statistics, quotes, etc in db
    TYPE_CHOICES = (
        (u'statistic', u'statistic'),
        (u'quote', u'quote'),
        (u'featured', u'featured'),
        (u'other', u'other'),
    )
    type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    content = models.TextField()
    detail = models.TextField(blank=True, null=True)
    options = JSONField(blank=True, editable=False, null=True)

    def __unicode__(self):
        return u'"%s"' % (self.content)


class BiogpsAltLayout(models.Model):
    # Alternate layouts for circadian, genewiki, etc
    layout_name = models.CharField(max_length=100)
    layout_number = models.CharField(max_length=50)

    def __unicode__(self):
        return u'"%s: %s"' % (self.layout_name, self.layout_number)


#==============================================================================
# setup logger (logging to syslog)
#==============================================================================
import logging
from biogps.utils import log
if settings.DEBUG:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

if len(log.handlers) == 0:   # only add handler once because this module could
                             # be imported multiple times.
    log_formatter = logging.Formatter('%(name)s: %(levelname)s %(message)s')
    try:
        from logging.handlers import SysLogHandler
        import syslog
        # Log to EC2 central logging server directly
        log_handler = SysLogHandler(address=(settings.LOG_SERVER, 514),
                                    facility=syslog.LOG_LOCAL6)
        #log_handler = SysLogHandler(address='/dev/log',
        #                            facility=syslog.LOG_LOCAL6)
        log_handler.setFormatter(log_formatter)
        log.addHandler(log_handler)
    except:
        log_handler = logging.StreamHandler()
        log_handler.setFormatter(log_formatter)
        log.addHandler(log_handler)
        log.warn('"syslog" not available. Log message will be sent to stderr.')

#==============================================================================
# hook up got_request_exception signal to log uncaught exceptions
#==============================================================================
if not settings.DEBUG:
    from django.core.signals import got_request_exception

    def _log_exc_info(sender, request, **kwargs):
        try:
            import sys
            import traceback
            exc_type, exc_value, exc_tb = sys.exc_info()
            exc_tb_stack = traceback.extract_tb(exc_tb)
            if exc_type and len(exc_tb_stack) > 0:
                log.error('username=%s clientip=%s url=%s exception=%s' + \
                             ' filename=%s lineno=%s name=%s',
                           getattr(request.user, 'username', ''),
                           request.META.get('REMOTE_ADDR', ''),
                           request.path,
                           exc_type.__name__,
                           exc_tb_stack[-1][0],
                           exc_tb_stack[-1][1],
                           exc_tb_stack[-1][2],
                          )
        except:
            #ignore any error within this logging function.
            pass

    #using dispatch_uid to void the signal being bound multiple time.
    got_request_exception.connect(_log_exc_info,
                                  dispatch_uid="global_exception_logging")
