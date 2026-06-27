import django_filters
from .models import Email


class EmailFilter(django_filters.FilterSet):
    # Multi-value filters: ?category=support,billing
    category = django_filters.CharFilter(method="filter_csv_in")
    priority = django_filters.CharFilter(method="filter_csv_in")
    # Exact match filters
    sentiment = django_filters.CharFilter(field_name="classification__sentiment")
    status = django_filters.CharFilter(field_name="status")
    requires_action = django_filters.BooleanFilter(field_name="classification__requires_action")
    is_archived = django_filters.BooleanFilter(field_name="is_archived")
    user_corrected = django_filters.BooleanFilter(field_name="classification__user_corrected")
    # Date range filters
    date_from = django_filters.DateTimeFilter(field_name="received_at", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="received_at", lookup_expr="lte")

    class Meta:
        model = Email
        fields = [
            "category", "priority", "sentiment", "status",
            "requires_action", "is_archived", "user_corrected",
            "date_from", "date_to",
        ]

    def filter_csv_in(self, queryset, name, value):
        """Filter by comma-separated values. `name` maps to the field via field_map."""
        field_map = {
            "category": "classification__category__in",
            "priority": "classification__priority__in",
        }
        lookup = field_map.get(name)
        if not lookup:
            return queryset
        values = [v.strip() for v in value.split(",") if v.strip()]
        return queryset.filter(**{lookup: values})
