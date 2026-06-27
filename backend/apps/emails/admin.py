from django.contrib import admin
from .models import Email, EmailClassification, ActionLog

admin.site.register(Email)
admin.site.register(EmailClassification)
admin.site.register(ActionLog)
