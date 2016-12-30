# -*- coding: utf-8 -*-
# Author: Ian MacLeod (imacleod@scripps.edu)

'''
Use this script for demo-ifying a DB for
external use (GSOC, etc). All plugins are 
assigned to a demo account, then all non-demo
and non-admin users are deleted.
'''

from django.conf import settings
from django.core.management.base import BaseCommand
from biogps.auth2.models import User
from biogps.plugin.models import BiogpsPlugin
from friends.models import (Friendship, FriendshipInvitation, FriendshipInvitationHistory)


class Command(BaseCommand):
    help = '''A utility that demo-ifies a DB for external use (GSOC, etc).
              All plugins are assigned to a demo account, then all non-demo
              and non-admin users are deleted. Manually set the user and DB
              in this script.
           '''

    def handle(self, **options):
        target_DB = settings.DATABASES['default']['NAME']
        target_user = 'demouser'
        keep_users = ['keepuser']
        ans = ask('\n***BE POSITIVE YOU WANT TO DO THIS*** Demo-ify database {} by assigning all plugins to user {} and deleting all non-demo and admin users in database? '.format(target_DB, target_user))
        if ans == 'Y':
            self.stdout.write('\nDemo-ifying...\n')

            try:
                u = User.objects.get(username=target_user)
            except User.DoesNotExist:
                self.stdout.write('Username {} not found in {}, exiting.\n'.format(target_user, target_DB))
                return

            # Assign all plugins to user
            self.stdout.write('Reassigning plugin owners...\n')
            p = BiogpsPlugin.objects.all()
            for i in p:
                i.set_owner(u)
                i.save()

            # Delete all friendships
            Friendship.objects.all().delete()
            FriendshipInvitation.objects.all().delete()
            FriendshipInvitationHistory.objects.all().delete()

            # Delete all non '*demo*' and '*admin*' users
            self.stdout.write('Deleting non-demo and admin users...\n')
            User.objects.exclude(username__in=keep_users).exclude(username__icontains='demo').exclude(username__icontains='admin').delete()

            self.stdout.write('Demo-ifying complete!\n')


def ask(prompt, options='YN'):
    '''Prompt Yes or No, return the upper case 'Y' or 'N'.'''
    options=options.upper()
    while 1:
        s = raw_input(prompt+'[%s]' % '|'.join(list(options))).strip().upper()
        if s in options: break
    return s
