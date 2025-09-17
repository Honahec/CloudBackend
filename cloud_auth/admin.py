from django.contrib import admin
from .models import User

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'display_name', 'email')
    search_fields = ('username', 'display_name', 'email')