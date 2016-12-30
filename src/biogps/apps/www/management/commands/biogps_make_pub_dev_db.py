"""
A utility script to make a dev db OK for external developers
by stripping all sensitive data.

##USE IT WITH CAUTION##
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "A utility script to make a dev db OK for external developers by stripping all sensitive data."

    requires_system_checks = True

    def handle(self, **options):
        make_dev()


def make_dev():
    for attr in ['ENGINE', 'NAME', 'HOST']:
        print '  DATABASE_%s:  %s' % (attr, settings.DATABASES['default'][attr])
    print "CAUTION: double check the DB above. The changes cannot be un-done!"
    s=raw_input('Type "YESYES" to continue:')
    if s == 'YESYES':
        from django.contrib.sessions.models import Session
        from django.contrib.admin.models import LogEntry
        from django.contrib.sites.models import Site
        from notification.models import Notice
        from django_authopenid.models import Nonce, Association, UserAssociation, UserPasswordQueue
        from urlauth.models import AuthKey
        from biogps.auth2.models import UserProfile, UserFlag, UserMigration
        from django.contrib.auth.models import User

        with transaction.atomic():
            for _model in [Session, LogEntry, Notice, Nonce, Association,
                           UserAssociation, UserPasswordQueue, AuthKey,
                           UserFlag, UserMigration]:
                _model.objects.all().delete()

            Site.objects.exclude(id='1').delete()

            for u in UserProfile.objects.all():
                if u.affiliation:
                    u.affiliation = 'affiliation_masked'
                    u.save()

            for u in User.objects.all():
                if u.username in ['cwu', 'asu', 'x0xMaximus'] or \
                        u.username.find('demo') != -1:
                    u.set_password('123')
                    continue
                if u.email:
                    u.email = "email_masked@dummy.com"
                    u.set_unusable_password()
                u.save()

        print 'Done!'
