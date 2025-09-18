from .models import File
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