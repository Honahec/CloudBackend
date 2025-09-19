from django.contrib import admin
from .models import File, Drop

# Register your models here.
@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'content_type', 'size', 'created_at', 'is_deleted', 'path')
    search_fields = ('name', 'content_type')
    list_filter = ('content_type', 'created_at')
    readonly_fields = ('id', 'created_at', 'is_deleted')
    ordering = ('-id',)

@admin.register(Drop)
class DropAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'expire_days', 'expire_time', 'is_expired', 'code', 'require_login', 'download_count', 'max_download_count', 'is_deleted')
    search_fields = ('code', 'user__username', 'user__email')
    list_filter = ('expire_days', 'is_expired', 'require_login', 'created_at')
    readonly_fields = ('id', 'created_at', 'is_expired', 'download_count')
    ordering = ('-id',)