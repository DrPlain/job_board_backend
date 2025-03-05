from django.urls import path
from .views import JobPostingListCreateView, JobPostingDetailView

urlpatterns = [
    path('', JobPostingListCreateView.as_view(), name='job-list-create'),
    path('<uuid:id>/', JobPostingDetailView.as_view(), name='job-detail-crud'),
]