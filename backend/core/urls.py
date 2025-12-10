from django.urls import path
from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("run/<uuid:run_id>/", views.run_detail, name="run_detail"),
    path("create_agent/", views.create_agent, name="create_agent"),
    path("api/start/", views.start_mission, name="start_mission"),
]
