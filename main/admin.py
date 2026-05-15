from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *

# Register your models here.
# class UserAdmin(BaseUserAdmin):
#     ordering = ("login",)
#     list_display = ("login", "name", "age", "is_staff")
#     search_fields = ("login", "name")

#     fieldsets = (
#         (None, {"fields": ("login", "password")}),
#         ("Персональные данные", {"fields": ("name", "age")}),
#         ("Права", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
#     )

#     add_fieldsets = (
#         (None, {
#             "classes": ("wide",),
#             "fields": ("login", "name", "age", "password1", "password2")
#         }),
#     )

#     filter_horizontal = ("groups", "user_permissions")


admin.site.register(User)