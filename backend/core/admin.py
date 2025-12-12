from django.contrib import admin
from .models import AgentRun, AgentMessage


admin.site.register(AgentRun)
admin.site.register(AgentMessage)
