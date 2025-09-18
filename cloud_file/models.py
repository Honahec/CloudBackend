from django.db import models
from cloud_auth.models import User
from uuid import uuid4

def uuid():
    return uuid4().hex.replace('-', '')

# Create your models here.
class File(models.Model):
    UPLOAD_STATUS_CHOICES = [
        ('pending', '待上传'),
        ('uploading', '上传中'),
        ('completed', '上传完成'),
        ('failed', '上传失败'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255)
    size = models.IntegerField()
    
    # OSS相关字段
    oss_key = models.CharField(max_length=511, null=True, blank=True, help_text="OSS对象键")
    oss_url = models.URLField(null=True, blank=True, help_text="OSS文件访问URL")
    
    # 上传状态跟踪
    upload_status = models.CharField(
        max_length=20, 
        choices=UPLOAD_STATUS_CHOICES, 
        default='pending',
        help_text="文件上传状态"
    )
    upload_error = models.TextField(null=True, blank=True, help_text="上传错误信息")
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cloud_file'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else 'Unknown'})"