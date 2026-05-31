"""
URL configuration for doctors app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'doctors'

router = DefaultRouter()
router.register(r'', views.DoctorViewSet, basename='doctor')

urlpatterns = [
    path('', include(router.urls)),
    # Nested slot routes
    path('<int:doctor_pk>/slots/', views.DoctorSlotViewSet.as_view({'get': 'list', 'post': 'create'}), name='doctor-slots-list'),
    path('<int:doctor_pk>/slots/generate/', views.DoctorSlotViewSet.as_view({'post': 'generate_slots'}), name='doctor-slots-generate'),
    path('<int:doctor_pk>/slots/<int:pk>/', views.DoctorSlotViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='doctor-slots-detail'),
    path('<int:doctor_pk>/slots/<int:pk>/book/', views.DoctorSlotViewSet.as_view({'post': 'book_slot'}), name='doctor-slots-book'),
    path('<int:doctor_pk>/slots/<int:pk>/block/', views.DoctorSlotViewSet.as_view({'patch': 'block_slot'}), name='doctor-slots-block'),
    path('<int:doctor_pk>/slots/<int:pk>/unblock/', views.DoctorSlotViewSet.as_view({'patch': 'unblock_slot'}), name='doctor-slots-unblock'),
]
