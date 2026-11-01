from django.contrib import admin
from django.core.exceptions import PermissionDenied

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """A limited account-status list for staff with explicit deactivation rights."""

    list_display = ("id", "email", "is_active")
    list_display_links = None
    list_filter = ("is_active",)
    search_fields = ("email",)
    ordering = ("id",)
    actions = ["deactivate_accounts"]
    fields = ("email", "is_active", "is_staff", "groups")
    readonly_fields = ("email",)

    def get_list_display_links(self, request, list_display):
        return ("email",) if request.user.is_superuser else None

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_view_permission(self, request, obj=None):
        user = request.user
        return (
            user.is_active
            and user.is_staff
            and (user.is_superuser or user.has_perm("accounts.deactivate_user"))
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def has_deactivate_permission(self, request):
        return self.has_view_permission(request)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(is_superuser=False)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if not request.user.is_superuser:
            # Business administrators may only use the limited list action.
            raise PermissionDenied
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.action(permissions=["deactivate"], description="Деактивувати обрані акаунти")
    def deactivate_accounts(self, request, queryset):
        queryset.exclude(pk=request.user.pk).filter(is_superuser=False).update(
            is_active=False
        )
