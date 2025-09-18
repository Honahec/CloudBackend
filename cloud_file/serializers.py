from rest_framework import serializers
from .models import File

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = read_only_fields = (
            "id",
            "name",
            "content_type",
            "size",
            "oss_key",
            "oss_url",
            "upload_status",
            "upload_error",
            "created_at",
            "updated_at",
        )

class FileUploadSerializer(serializers.ModelSerializer):
    # 添加文件内容字段（base64编码）
    file_content = serializers.CharField(write_only=True, required=False, help_text="base64编码的文件内容")
    
    class Meta:
        model = File
        fields = (
            "id",
            "name",
            "content_type",
            "size",
            "file_content",
            "upload_status",
        )
        read_only_fields = ("id", "upload_status")