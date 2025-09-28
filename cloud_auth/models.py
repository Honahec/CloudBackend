from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class Permission(models.Model):
    admin_user = models.BooleanField(default=False)
    admin_file = models.BooleanField(default=False)
    admin_drop = models.BooleanField(default=False)

class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    display_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    permission = models.OneToOneField(Permission, on_delete=models.PROTECT, null=True, blank=True)
    quota = models.BigIntegerField(default=10 * 1024 * 1024 * 1024)
    used_space = models.BigIntegerField(default=0)