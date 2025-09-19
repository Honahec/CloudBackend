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

class ExpireDaysChoice(models.IntegerChoices):
    ONE_DAY = 1, '1 Day'
    THREE_DAYS = 3, '3 Days'
    SEVEN_DAYS = 7, '7 Days'
    FIFTEEN_DAYS = 15, '15 Days'
class Drop(models.Model):
    files = models.ManyToManyField(File)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expire_days = models.IntegerField(choices=ExpireDaysChoice.choices, default=ExpireDaysChoice.ONE_DAYS)
    expire_time = models.DateTimeField()
    is_expired = models.BooleanField(default=False)
    code = models.CharField(max_length=10)
    require_login = models.BooleanField(default=False)
    download_count = models.IntegerField(default=0)
    max_download_count = models.IntegerField(default=1)
    password = models.CharField(max_length=255, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

