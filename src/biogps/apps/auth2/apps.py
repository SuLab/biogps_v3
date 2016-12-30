from django.apps import AppConfig


class Auth2Config(AppConfig):
    name = 'biogps.apps.auth2'

    def ready(self):
        from biogps.apps.auth2 import signals
