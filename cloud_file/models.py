from django.db import models
from cloud_auth.models import User

# Create your models here.
class File(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.IntegerField()
    oss_url = models.URLField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    path = models.CharField(max_length=1024, blank=True, null=True, default='/')
    is_deleted = models.BooleanField(default=False)
