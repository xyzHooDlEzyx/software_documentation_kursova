from datetime import timezone as dt_timezone

from rest_framework import serializers

from accounts.serializers import StrictIntegerField, StrictSerializer


class RequiredPeriodQuerySerializer(StrictSerializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": ["Кінцева дата має бути пізнішою за початкову."]}
            )
        return attrs


class WeightChartPointSerializer(serializers.Serializer):
    measured_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc
    )
    weight_kg = serializers.DecimalField(
        max_digits=4, decimal_places=1, coerce_to_string=True
    )


class LeaderboardQuerySerializer(StrictSerializer):
    period = serializers.ChoiceField(choices=("week", "month", "all"), default="all")
    anchor_date = serializers.DateField(required=False)
    page = StrictIntegerField(min_value=1, default=1)
    page_size = StrictIntegerField(min_value=1, max_value=100, default=20)

    def validate(self, attrs):
        if attrs["period"] == "all" and "anchor_date" in attrs:
            raise serializers.ValidationError(
                {"anchor_date": ["anchor_date не застосовується до period=all."]}
            )
        return attrs
