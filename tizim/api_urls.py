from django.urls import include, path
from rest_framework import routers

from .views import BankViewSet

router = routers.DefaultRouter()
router.register(r"banks", BankViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
