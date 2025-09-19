from .models import File, Drop
from rest_framework import serializers

class FileSerializer(serializers.ModelSerializer):
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
        )

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


class DropSerializer(serializers.Serializer):
    class Meta:
        model = Drop
        exclude = ("files",)

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