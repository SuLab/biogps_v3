# HTML Email Sender for Django
# www/management/commands/mail_users.py
#
# This file is invoked via the command:
#   python manage.py mail_developers --settings=settings_dev
#   python manage.py mail_developers --settings=settings_prod --send
#
# Passing the --send flag will cause the emails to actually be sent out.
# The initial version of this code is highly specialized to send a specific
# email to registered users that have registered at least one plugin.

from django.conf import settings
from django.core.mail import get_connection, send_mail, EmailMessage
from django.template.loader import render_to_string
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class EmailUsersCommand(BaseCommand):
    help = "Sends an HTML email out to a list of users."
    args = ''

    def add_arguments(self, parser):
        parser.add_argument(
            '--send', '-s',
            action='store_true',
            dest='send',
            help='Actually send the emails out to each user.',
        )
        parser.add_argument(
            '--test', '-t',
            dest='test_email',
            help='Send a test email to given test email address.',
        )

    def handle(self, **options):
        self.args = options

        if self.args.get("send", False):
            print "SENDING EMAIL!!"
        else:
            print "TEST RUN - No email will actually be sent"

        # Uncomment the below line to send a test email just to user cwudemo.
        #users = [User.objects.get(id=364),]
        self.send()

    def get_subject(self):
        raise NotImplementedError

    def get_message(self):
        raise NotImplementedError

    def get_recipients(self):
        raise NotImplementedError

    def send(self):
        '''Do the actual sending.'''
        subject = self.get_subject()
        message = self.get_message()

        test_email = self.args.get('test_email', None)
        if test_email:
            recipients = (test_email,)
        else:
            recipients = self.get_recipients()

        print "Sending email to %d recipients ..." % len(recipients)
        self.mail_in_html(recipients, subject, message)
        print "Done."

    def mail_in_html(self, recipient, subject, message, fail_silently=False):
        """Sends a message to the managers, as defined by the MANAGERS setting.
           passed message is a html document.
        """
        connection = get_connection(fail_silently=fail_silently)
        for r in recipient:
            print r,
            msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [r])
            msg.content_subtype = "html"
            if self.args.get("send", False):
                print connection.send_messages([msg])
            else:
                print


class Command(EmailUsersCommand):
    def get_subject(self):
        return 'BioGPS is moving'

    def get_message(self):
        template = 'auth/migration_email_biogpsusers.html'
        #template = 'auth/migration_email_gnfusers.html'
        #template = 'auth/migration_email_nvsusers.html'
        site = 'http://biogps.gnf.org'
        return render_to_string(template, {'site': site})

    def get_recipients(self):
        in_f = file('email_list_bgpsusers.txt')
        email_li = [x.strip() for x in in_f.read().strip().split('\n')]
        in_f.close()
        return email_li



