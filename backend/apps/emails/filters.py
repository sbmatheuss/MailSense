import django_filters
from .models import Email


class EmailFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="classification__category", lookup_expr="in", method="filter_in")
    priority = django_filters.CharFilter(field_name="classification__priority", lookup_expr="in", method="filter_priority_in")
    sentiment = django_filters.CharFilter(field_name="classification__sentiment")
    status = django_filters.CharFilter(field_name="status")
    requires_action = django_filters.BooleanFilter(field_name="classification__requires_action")
    date_from = django_filters.DateTimeFilter(field_name="received_at", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="received_at", lookup_expr="lte")

    class Meta:
        model = Email
        fields = ["category", "priority", "sentiment", "status", "requires_action", "date_from", "date_to"]

    def filter_in(self, queryset, name, value):
        values = [v.strip() for v in value.split(",") if v.strip()]
        return queryset.filter(classification__category__in=values)

    def filter_priority_in(self, queryset, name, value):
        values = [v.strip() for v in value.split(",") if v.strip()]
        return queryset.filter(classification__priority__in=values)
