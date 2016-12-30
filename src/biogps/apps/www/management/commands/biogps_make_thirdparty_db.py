"""
A utility script to make a prod/dev db OK for third-party installation
by stripping all sensitive data.

##USE IT WITH CAUTION##
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "A utility script to make a prod/dev db OK for third-party installation by stripping all sensitive data."

    requires_system_checks = True

    def handle(self, **options):
        make_dev()


def make_dev():
    for attr in ['ENGINE', 'NAME', 'HOST']:
        print '  DATABASE_%s:  %s' % (attr, settings.DATABASES['default'][attr])
    print "CAUTION: double check the DB above. The changes cannot be un-done!"
    s=raw_input('Type "YESYES" to continue:')
    if s == 'YESYES':
        settings.SUSPEND_ES_UPDATE = True
        from django.contrib.sessions.models import Session
        from django.contrib.admin.models import LogEntry
        from django.contrib.sites.models import Site
        from notification.models import Notice
        from django_authopenid.models import Nonce, Association, UserAssociation, UserPasswordQueue
        from urlauth.models import AuthKey
        from biogps.auth2.models import UserFlag, UserMigration
        from django.contrib.auth.models import User

        with transaction.atomic():
            for _model in [Session, LogEntry,
                           Notice,
                           Nonce, Association, UserAssociation,
                           UserPasswordQueue,
                           AuthKey,
                           UserFlag, UserMigration,
                           ]:
                _model.objects.all().delete()

            Site.objects.exclude(id='1').delete()

            # More third-party specific clean-up
            from biogps.genelist.models import BiogpsGeneList
            from biogps.layout.models import BiogpsGenereportLayout
            from biogps.plugin.models import BiogpsPlugin
            from biogps.www.models import BiogpsAltLayout
            from django.contrib.auth.models import Group
            from friends.models import (
                FriendshipInvitation, Friendship, Contact,
                JoinInvitation, FriendshipInvitationHistory,
            )
            # TODO: what about this?? needs to be reviewed
            from django.db.migrations.recorder import MigrationRecorder
            MigrationHistory = MigrationRecorder.Migration
            from flag.models import FlaggedContent, FlagInstance
            for _model in [BiogpsGeneList, BiogpsAltLayout,
                           FriendshipInvitation, Friendship, Contact,
                           JoinInvitation, FriendshipInvitationHistory,
                           MigrationHistory,
                           FlaggedContent, FlagInstance,
                          ]:
                _model.objects.all().delete()
            print 1  # ##

            uu = User.objects.get(username='cwudemo')   # a regular Biogps user
            cwu = User.objects.get(username='cwu')
            asu = User.objects.get(username='asu')
            geo = User.objects.get(username='GEO Uploader')

            public_layouts = BiogpsGenereportLayout.objects.get_available(
                uu, excludemine=True)
            for layout in public_layouts:
                if layout.owner not in [cwu, asu]:
                    layout.owner = asu
                    layout.save()
            print 2  # ##
            # remove all the rest of layouts (private layouts)
            BiogpsGenereportLayout.objects.exclude(
                id__in=[x.id for x in public_layouts]).delete()
            print 3  # ##
            public_plugins = BiogpsPlugin.objects.get_available(
                uu, excludemine=True)
            for plugin in public_plugins:
                if plugin.owner not in [cwu, asu]:
                    plugin.owner = asu
                    plugin.save()
            print 4  # ##
            # remove all the rest of non-public plugins
            BiogpsPlugin.objects.exclude(id__in=[x.id for x in public_plugins]).delete()
            print 5  # ##
            # Now remove all users except cwu/asu/cwudemo
            User.objects.exclude(
                username__in=['cwu', 'asu', 'cwudemo', 'GEO Uploader']).delete()
            print 6  # ##
            for u in User.objects.all():
                u.set_password('123')
                u.save()
            print 7  # ##

            # #clean up Group
            Group.objects.filter(
                name__in=['nvsusers', 'gnfusers', 'adam']).delete()

        print 'Done!'
