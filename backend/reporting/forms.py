from django import forms

from accounts.selectors import kyiv_date_range_to_utc


class ReportPeriodForm(forms.Form):
    start_date = forms.DateField(
        label="Початкова дата", widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        label="Кінцева дата", widget=forms.DateInput(attrs={"type": "date"})
    )
    page = forms.IntegerField(
        required=False, min_value=1, initial=1, widget=forms.HiddenInput
    )

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date is not None and end_date is not None and start_date >= end_date:
            self.add_error("end_date", "Кінцева дата має бути пізнішою за початкову.")
        return cleaned

    def utc_bounds(self):
        return kyiv_date_range_to_utc(
            self.cleaned_data["start_date"], self.cleaned_data["end_date"]
        )
