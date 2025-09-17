from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'email', 'password', 'is_active', 'permission']
        extra_kwargs = {
            'password': {'write_only': True}
        }