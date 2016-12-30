"""
This is taken and modified from ragendja (snippet library) at
http://code.google.com/p/app-engine-patch/

The app_prefixed_loader is a template loader that loads directly from the app's
'templates' folder when you specify an app prefix ('app/template.html').
"""
import os.path

from apputils import get_app_dirs

from django.conf import settings
from django.template.base import TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader


class BiogpsLoader(BaseLoader):
    is_usable = True

    def load_template_source(self, template_name, template_dirs=None):
        packed = template_name.split('/', 1)
        if len(packed) == 2 and packed[0] in app_template_dirs:
            path = os.path.join(app_template_dirs[packed[0]], packed[1])
            try:
                return (open(path).read().decode(settings.FILE_CHARSET), path)
            except IOError:
                pass
        raise TemplateDoesNotExist(template_name)

# This is needed by app_prefixed_loader.
app_template_dirs = get_app_dirs('templates')
