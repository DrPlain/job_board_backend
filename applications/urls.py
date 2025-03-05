# applications/urls.py
from django.urls import path
from .views import JobApplicationListCreate, JobApplicationDetail



urlpatterns = [
    path('', JobApplicationListCreate.as_view(), name='application_list_create'),
    path('<int:pk>/', JobApplicationDetail.as_view(), name='application_detail'),
]