from django import forms
from django.contrib import admin

from config.admin import AdministratorModelAdmin

from .models import Achievement, Challenge


class ChallengeAdminForm(forms.ModelForm):
    class Meta:
        model = Challenge
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.participations.exists():
            immutable = ("start_at", "end_at", "goal_kind", "goal_value")
            for field_name in immutable:
                if field_name in self.changed_data:
                    self.add_error(
                        field_name,
                        "Поле не можна змінювати після появи учасників.",
                    )
        return cleaned


@admin.register(Challenge)
class ChallengeAdmin(AdministratorModelAdmin):
    form = ChallengeAdminForm
    list_display = (
        "name",
        "start_at",
        "end_at",
        "goal_kind",
        "goal_value",
        "is_archived",
    )
    list_filter = ("is_archived", "goal_kind")
    search_fields = ("name",)
    readonly_fields = ("is_archived",)
    actions = ("publish_selected", "unpublish_selected")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.participations.exists():
            fields.extend(("start_at", "end_at", "goal_kind", "goal_value"))
        return tuple(fields)

    @admin.action(permissions=["change"], description="Опублікувати обрані челенджі")
    def publish_selected(self, request, queryset):
        queryset.update(is_archived=False)

    @admin.action(
        permissions=["change"], description="Зняти з публікації обрані челенджі"
    )
    def unpublish_selected(self, request, queryset):
        queryset.update(is_archived=True)


@admin.register(Achievement)
class AchievementAdmin(AdministratorModelAdmin):
    list_display = ("code", "name", "rule_code", "is_archived")
    search_fields = ("code", "name")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
