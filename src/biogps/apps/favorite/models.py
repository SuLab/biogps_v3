from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class Favorite(models.Model):
    user = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    submit_date = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'%s with ID %s is favorite of %s' % (self.content_type, self.object_id, self.user)
