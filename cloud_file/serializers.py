from .models import File, Drop
from rest_framework import serializers

class FileSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    
    class Meta:
        model = File
        fields = read_only_fields = (
            "id",
            "name",
            "content_type",
            "size",
            "oss_url",
            "created_at",
            "path",
            "user_id",
        )
        
    def get_user_id(self, obj):
        """
        安全地获取用户ID，处理user字段可能为null的情况
        """
        if obj.user and hasattr(obj.user, 'id'):
            return obj.user.id
        return None

class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = (
            "id",
            "name",
            "content_type",
            "size",
            "oss_url",
            "path",
        )
        read_only_fields = ("id",)


class DropSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Drop
        exclude = ("files", "user")
        
    def get_user_id(self, obj):
        """
        安全地获取用户ID，处理user字段可能为null的情况
        """
        if obj.user and hasattr(obj.user, 'id'):
            return obj.user.id
        return None

class DropCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drop
        fields = (
            "id",
            "expire_days",
            "code",
            "require_login",
            "max_download_count",
            "password",
        )
        read_only_fields = ("id",)