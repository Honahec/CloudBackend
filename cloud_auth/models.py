from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class permission(models.Model):
    admin_user = models.BooleanField(default=False)
    admin_file = models.BooleanField(default=False)
    admin_drop = models.BooleanField(default=False)
class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    display_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    permission = models.OneToOneField(permission, on_delete=models.PROTECT)