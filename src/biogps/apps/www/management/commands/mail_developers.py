# HTML Email Sender for Django
# www/management/commands/mail_developers.py
#
# Copyright 2010, GNF
# Authors: Marc Leglise
#
# This file is invoked via the command:
#   python manage.py mail_developers --settings=settings_dev
#   python manage.py mail_developers --settings=settings_prod --send
#
# Passing the --send flag will cause the emails to actually be sent out.
# The initial version of this code is highly specialized to send a specific
# email to registered users that have registered at least one plugin.

from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string

from django.core.management.base import BaseCommand
from optparse import make_option

from django.contrib.auth.models import User
from biogps.plugin.models import BiogpsPlugin


class Command(BaseCommand):
    help = "Sends an HTML email out to all plugin developers."
    args = ''

    def add_arguments(self, parser):
        parser.add_argument(
            '--send', '-s',
            action='store_true',
            dest='send',
            help='Actually send the emails out to each user.',
        )

    def handle(self, **options):
        self.args = options

        if self.args.get("send", False):
            print "SENDING EMAIL!!"
        else:
            print "TEST RUN - No email will actually be sent"

        # Retrieve the owner IDs of all registered plugins
        olist = BiogpsPlugin.objects.values_list('ownerprofile')

        # Shrink the list to only unique IDs and flatten the array
        olist = [item for sublist in list(set(olist)) for item in sublist]

        # Retrieve the user objects and send them email
        users = User.objects.filter(userprofile__sid__in=olist)

        # Uncomment the below line to send a test email just to Marc.
        #users = [User.objects.get(id=364),]
        self.send_email_to_users(users)

    def send_email_to_users(self, users):
        subject = 'Increase the visibility of your BioGPS plugin'

        # Keep a list of email addresses we've already hit, to catch users that
        # have multiple accounts with the same address.
        already_sent = []
        send_counter = 0

        for user in users:
            if (not user.email) or (user.email in already_sent): continue
            recipient = (user.email,)
            message = render_to_string('email/plugin_developer.html', {'user': user, 'subject': subject})
            self.mail_in_html(recipient, subject, message)

            already_sent.append(user.email)
            send_counter+=1

        print "Sent out %s emails. DONE." % send_counter

    def mail_in_html(self, recipient, subject, message, fail_silently=False):
        """Sends a message to the managers, as defined by the MANAGERS setting.
           passed message is a html document.
        """
        print "Sending email to: %s" % recipient
        msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, recipient)
        msg.content_subtype = "html"
        if self.args.get("send", False):
            msg.send(fail_silently=fail_silently)

