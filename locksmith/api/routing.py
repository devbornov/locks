from django.urls import re_path
from .consumers import ServiceRequestConsumer

websocket_urlpatterns = [
    re_path(r'ws/requests/(?P<locksmith_id>\d+)/$', ServiceRequestConsumer.as_asgi()),
]
