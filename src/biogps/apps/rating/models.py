from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class Rating(models.Model):
    user = models.ForeignKey(User)
    rating = models.PositiveSmallIntegerField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    submit_date = models.DateTimeField(auto_now=True)
    rating_scale = list([[1, "Very Poor"], [2, "Poor"], [3, "Good"], [4, "Very Good"],
                         [5, "Great"]])
    rating_static = list([i for i in range(1,11)])

    def __unicode__(self):
        return u'%s for %s with ID %s by %s' % (self.rating, self.content_type, self.object_id, self.user)
