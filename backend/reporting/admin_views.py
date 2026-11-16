import csv

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from .forms import ReportPeriodForm
from .selectors import ReportQueryService


def _require_report_permission(request):
    if not (
        request.user.is_active
        and request.user.is_staff
        and request.user.has_perm("reporting.view_reports")
    ):
        raise PermissionDenied


def _safe_csv_cell(value):
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_csv_cell(value) for value in row])
    return response


def _base_context(request, *, title, form, report_id):
    return {
        **admin.site.each_context(request),
        "title": title,
        "form": form,
        "report_id": report_id,
        "opts": {"app_label": "reporting"},
    }


def workout_popularity_report(request):
    _require_report_permission(request)
    form = ReportPeriodForm(request.GET or None)
    context = _base_context(
        request, title="Популярність тренувань", form=form, report_id="R02"
    )
    if form.is_valid():
        start_at, end_at = form.utc_bounds()
        rows = list(
            ReportQueryService.workout_popularity(start_at=start_at, end_at=end_at)
        )
        if request.GET.get("format") == "csv":
            return _csv_response(
                "workout-popularity.csv",
                ("ID тренування", "Назва", "Архівне", "Кількість завершень"),
                (
                    (
                        row["source_workout_id"],
                        row["source_workout__name"],
                        "так" if row["source_workout__is_archived"] else "ні",
                        row["completed_count"],
                    )
                    for row in rows
                ),
            )
        page = Paginator(rows, 50).get_page(form.cleaned_data.get("page") or 1)
        context.update(
            {
                "rows": page.object_list,
                "page_obj": page,
                "csv_query": request.GET.urlencode().replace("format=csv", ""),
                "chart_rows": page.object_list,
                "chart_max": max(
                    (row["completed_count"] for row in page.object_list), default=0
                ),
                "kind": "popularity",
            }
        )
    return render(request, "admin/reporting/report.html", context)


def average_activity_report(request):
    _require_report_permission(request)
    form = ReportPeriodForm(request.GET or None)
    context = _base_context(
        request, title="Середня активність", form=form, report_id="R03"
    )
    if form.is_valid():
        start_at, end_at = form.utc_bounds()
        result = ReportQueryService.average_activity(start_at=start_at, end_at=end_at)
        rows = [
            ("Усього користувачів", result["total_users"]),
            ("Активні користувачі", result["active_users"]),
            ("Завершені тренування", result["total_completed"]),
            ("Усього хвилин", result["total_minutes"]),
            ("Середня кількість тренувань", result["average_workouts"]),
            ("Середня тривалість, хв", result["average_duration_min"]),
            ("Середнє серед активних", result["average_among_active"]),
        ]
        if request.GET.get("format") == "csv":
            return _csv_response("average-activity.csv", ("Показник", "Значення"), rows)
        context.update(
            {
                "rows": rows,
                "csv_query": request.GET.urlencode().replace("format=csv", ""),
                "chart_rows": rows,
                "chart_max": max((float(value) for _, value in rows), default=0),
                "kind": "average",
            }
        )
    return render(request, "admin/reporting/report.html", context)
