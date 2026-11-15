from django.contrib import admin


def is_active_staff(request) -> bool:
    user = request.user
    return bool(user and user.is_active and user.is_staff)


class AdministratorModelAdmin(admin.ModelAdmin):
    """Require active staff and explicit model permissions; disallow deletion."""

    def has_module_permission(self, request):
        return is_active_staff(request) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return is_active_staff(request) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return is_active_staff(request) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return is_active_staff(request) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
