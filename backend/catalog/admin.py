"""Django Admin configuration for the shared fitness catalog.

Enforces:
- Staff-only access for Administrator role (is_active and is_staff)
- Disabled physical deletion (BR-005)
- Atomic inlines publication and composition validation (BR-002, BR-003, BR-004)
"""

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.options import (
    IS_POPUP_VAR,
    TO_FIELD_VAR,
    DisallowedModelAdminToField,
    flatten_fieldsets,
    unquote,
)
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms import all_valid
from django.http import HttpResponse

from .models import (
    Exercise,
    ProgramTemplate,
    ProgramTemplateWorkout,
    Workout,
    WorkoutExercise,
)
from .services import CatalogPublicationService


class CatalogBaseModelAdmin(admin.ModelAdmin):
    """Base model admin enforcing staff access and disabling physical deletion."""

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_delete_permission(self, request, obj=None):
        # Physical deletion is strictly prohibited by BR-005
        return False


@admin.register(Exercise)
class ExerciseAdmin(CatalogBaseModelAdmin):
    list_display = (
        "name",
        "category",
        "met_value",
        "met_activity_code",
        "met_reference_version",
        "is_archived",
    )
    list_filter = ("is_archived", "category")
    search_fields = ("name", "met_activity_code")
    actions = ["archive_selected"]

    @admin.action(description="Архівувати обрані вправи")
    def archive_selected(self, request, queryset):
        archived_count = 0
        for exercise in queryset:
            try:
                CatalogPublicationService.archive_exercise(exercise=exercise)
                archived_count += 1
            except ValidationError as exc:
                err_msg = exc.message if hasattr(exc, "message") else str(exc)
                self.message_user(
                    request,
                    f"Не вдалося архівувати '{exercise.name}': {err_msg}",
                    level=messages.ERROR,
                )
        if archived_count > 0:
            self.message_user(
                request,
                f"Успішно архівовано вправ: {archived_count}.",
                level=messages.SUCCESS,
            )


class CatalogTabularInline(admin.TabularInline):
    """TabularInline enforcing staff permissions without requiring extra perms."""

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_add_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_staff)


class WorkoutExerciseInline(CatalogTabularInline):
    model = WorkoutExercise
    extra = 1
    min_num = 1
    fields = (
        "position",
        "exercise",
        "recommended_sets",
        "recommended_reps",
        "recommended_load_kg",
        "recommended_duration_min",
        "recommended_distance_km",
    )
    ordering = ("position",)


class AtomicCompositeAdmin(CatalogBaseModelAdmin):
    """ModelAdmin that validates aggregate invariants atomically across inlines."""

    def validate_aggregate(self, instance):
        raise NotImplementedError

    def _changeform_view(
        self, request, object_id, form_url, extra_context
    ) -> HttpResponse:
        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        if to_field and not self.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField(
                f"The field {to_field} cannot be referenced."
            )

        if request.method == "POST" and "_saveasnew" in request.POST:
            object_id = None

        add = object_id is None

        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied
            obj = None
        else:
            obj = self.get_object(request, unquote(object_id), to_field)
            if request.method == "POST":
                if not self.has_change_permission(request, obj):
                    raise PermissionDenied
            else:
                if not self.has_view_or_change_permission(request, obj):
                    raise PermissionDenied
            if obj is None:
                return self._get_obj_does_not_exist_redirect(
                    request, self.opts, object_id
                )

        fieldsets = self.get_fieldsets(request, obj)
        ModelForm = self.get_form(
            request, obj, change=not add, fields=flatten_fieldsets(fieldsets)
        )

        if request.method == "POST":
            form = ModelForm(request.POST, request.FILES, instance=obj)
            formsets, inline_instances = self._create_formsets(
                request,
                form.instance,
                change=not add,
            )
            form_validated = form.is_valid()
            if form_validated:
                new_object = self.save_form(request, form, change=not add)
            else:
                new_object = form.instance

            if all_valid(formsets) and form_validated:
                sid = transaction.savepoint()
                try:
                    self.save_model(request, new_object, form, not add)
                    self.save_related(request, form, formsets, not add)
                    self.validate_aggregate(new_object)
                    transaction.savepoint_commit(sid)
                except ValidationError as exc:
                    transaction.savepoint_rollback(sid)
                    if add:
                        new_object.pk = None
                        form.instance.pk = None
                    if hasattr(exc, "message_dict"):
                        for field, errs in exc.message_dict.items():
                            for err in errs:
                                form.add_error(
                                    field if field in form.fields else None, err
                                )
                    elif hasattr(exc, "messages"):
                        for err in exc.messages:
                            form.add_error(None, err)
                    else:
                        form.add_error(None, str(exc))
                    form_validated = False
                except Exception:
                    transaction.savepoint_rollback(sid)
                    if add:
                        new_object.pk = None
                        form.instance.pk = None
                    raise

            if all_valid(formsets) and form_validated:
                change_message = self.construct_change_message(
                    request, form, formsets, add
                )
                if add:
                    self.log_addition(request, new_object, change_message)
                    return self.response_add(request, new_object)
                else:
                    self.log_change(request, new_object, change_message)
                    return self.response_change(request, new_object)
            else:
                form_validated = False
        else:
            if add:
                initial = self.get_changeform_initial_data(request)
                form = ModelForm(initial=initial)
                formsets, inline_instances = self._create_formsets(
                    request, form.instance, change=False
                )
            else:
                form = ModelForm(instance=obj)
                formsets, inline_instances = self._create_formsets(
                    request, obj, change=True
                )

        admin_form = helpers.AdminForm(
            form,
            list(fieldsets),
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self,
        )
        media = self.media + admin_form.media

        inline_formsets = self.get_inline_formsets(
            request, formsets, inline_instances, obj
        )
        for inline_formset in inline_formsets:
            media = media + inline_formset.media

        context = {
            **self.admin_site.each_context(request),
            "title": (self.opts.verbose_name_plural if add else self.opts.verbose_name),
            "subtitle": str(obj) if obj else None,
            "adminform": admin_form,
            "object_id": object_id,
            "original": obj,
            "is_popup": (IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET),
            "to_field": to_field,
            "media": media,
            "inline_admin_formsets": inline_formsets,
            "errors": helpers.AdminErrorList(form, formsets),
            "preserved_filters": self.get_preserved_filters(request),
            **(extra_context or {}),
        }
        return self.render_change_form(
            request, context, add=add, change=not add, obj=obj, form_url=form_url
        )


@admin.register(Workout)
class WorkoutAdmin(AtomicCompositeAdmin):
    list_display = ("name", "category", "is_archived")
    list_filter = ("is_archived", "category")
    search_fields = ("name",)
    inlines = [WorkoutExerciseInline]
    actions = ["archive_selected"]

    def validate_aggregate(self, instance):
        CatalogPublicationService.validate_persisted_workout(instance)

    @admin.action(description="Архівувати обрані тренування")
    def archive_selected(self, request, queryset):
        archived_count = 0
        for workout in queryset:
            try:
                CatalogPublicationService.archive_workout(workout=workout)
                archived_count += 1
            except ValidationError as exc:
                err_msg = exc.message if hasattr(exc, "message") else str(exc)
                self.message_user(
                    request,
                    f"Не вдалося архівувати '{workout.name}': {err_msg}",
                    level=messages.ERROR,
                )
        if archived_count > 0:
            self.message_user(
                request,
                f"Успішно архівовано тренувань: {archived_count}.",
                level=messages.SUCCESS,
            )


class ProgramTemplateWorkoutInline(CatalogTabularInline):
    model = ProgramTemplateWorkout
    extra = 1
    min_num = 1
    fields = ("position", "workout", "suggested_weekday")
    ordering = ("position",)


@admin.register(ProgramTemplate)
class ProgramTemplateAdmin(AtomicCompositeAdmin):
    list_display = (
        "name",
        "fitness_goal",
        "experience_level",
        "workouts_per_week",
        "status",
    )
    list_filter = ("status", "fitness_goal", "experience_level", "workouts_per_week")
    search_fields = ("name",)
    inlines = [ProgramTemplateWorkoutInline]
    actions = ["archive_selected"]

    def validate_aggregate(self, instance):
        CatalogPublicationService.validate_persisted_program_template(instance)

    @admin.action(description="Архівувати обрані шаблони програм")
    def archive_selected(self, request, queryset):
        archived_count = 0
        for template in queryset:
            try:
                CatalogPublicationService.archive_program_template(template=template)
                archived_count += 1
            except ValidationError as exc:
                err_msg = exc.message if hasattr(exc, "message") else str(exc)
                self.message_user(
                    request,
                    f"Не вдалося архівувати '{template.name}': {err_msg}",
                    level=messages.ERROR,
                )
        if archived_count > 0:
            self.message_user(
                request,
                f"Успішно архівовано шаблонів програм: {archived_count}.",
                level=messages.SUCCESS,
            )


@admin.register(WorkoutExercise)
class WorkoutExerciseAdmin(CatalogBaseModelAdmin):
    list_display = ("id", "workout", "exercise", "position")
    list_filter = ("workout__category", "exercise__category")
    search_fields = ("workout__name", "exercise__name")


@admin.register(ProgramTemplateWorkout)
class ProgramTemplateWorkoutAdmin(CatalogBaseModelAdmin):
    list_display = (
        "id",
        "program_template",
        "workout",
        "position",
        "suggested_weekday",
    )
    list_filter = (
        "program_template__fitness_goal",
        "program_template__experience_level",
    )
    search_fields = ("program_template__name", "workout__name")
