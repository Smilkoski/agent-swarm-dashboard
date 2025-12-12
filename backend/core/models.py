import uuid
from django.db import models

class AgentRun(models.Model):
    run_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, default="Untitled Mission")
    status = models.CharField(max_length=20, default="running")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.run_id})"

    class Meta:
        app_label = 'core'
        db_table = 'core_agent_run'


class AgentMessage(models.Model):
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="messages")
    agent_name = models.CharField(max_length=100)
    content = models.TextField()
    message_type = models.CharField(max_length=20)
    tool_used = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        app_label = 'core'
        db_table = 'core_agent_message'