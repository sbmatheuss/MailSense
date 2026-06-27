from django.urls import path
from . import views

urlpatterns = [
    path("emails/", views.EmailListView.as_view(), name="email-list"),
    path("emails/<int:pk>/", views.EmailDetailView.as_view(), name="email-detail"),
    path("emails/sync/", views.EmailSyncView.as_view(), name="email-sync"),
    path("emails/<int:pk>/reply/", views.EmailReplyView.as_view(), name="email-reply"),
    path("emails/<int:pk>/archive/", views.EmailArchiveView.as_view(), name="email-archive"),
    path("emails/<int:pk>/snooze/", views.EmailSnoozeView.as_view(), name="email-snooze"),
    path("emails/<int:pk>/classification/", views.EmailClassificationUpdateView.as_view(), name="email-classification"),
    path("emails/bulk-action/", views.EmailBulkActionView.as_view(), name="email-bulk-action"),
    path("dashboard/overview/", views.DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("dashboard/by-category/", views.DashboardByCategoryView.as_view(), name="dashboard-by-category"),
    path("dashboard/by-priority/", views.DashboardByPriorityView.as_view(), name="dashboard-by-priority"),
    path("dashboard/trends/", views.DashboardTrendsView.as_view(), name="dashboard-trends"),
    path("dashboard/response-time/", views.DashboardResponseTimeView.as_view(), name="dashboard-response-time"),
    path("dashboard/top-senders/", views.DashboardTopSendersView.as_view(), name="dashboard-top-senders"),
    path("demo/seed/", views.DemoSeedView.as_view(), name="demo-seed"),
    path("demo/reset/", views.DemoResetView.as_view(), name="demo-reset"),
]
