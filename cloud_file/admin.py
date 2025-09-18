from django.contrib import admin
from .models import File

# Register your models here.
@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'content_type', 'size', 'created_at')
    search_fields = ('name', 'content_type')
    list_filter = ('content_type', 'created_at')
    readonly_fields = ('id', 'created_at')
    ordering = ('-id',)