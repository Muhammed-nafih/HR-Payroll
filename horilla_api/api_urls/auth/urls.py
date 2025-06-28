from django.urls import path

from ...api_views.auth.views import LoginAPIView

urlpatterns = [path("login-api/", LoginAPIView.as_view())]
