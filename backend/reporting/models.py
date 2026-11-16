from django.db import models


class ReportAccess(models.Model):
    """Permission-only model for aggregate reports; it has no database table."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (("view_reports", "Can view aggregate reports"),)
        verbose_name = "агрегований звіт"
        verbose_name_plural = "агреговані звіти"
