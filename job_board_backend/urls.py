from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from applications.views import JobApplicationsView

# Swagger documentation schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Job Board API",
        default_version='v1',
        description="API documentation for the Job Board project",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    url="https://jobboardbackend-production-8f2e.up.railway.app/api/docs/",
    permission_classes=(permissions.AllowAny,),
)



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pain'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/jobs/', include('jobs.urls')),
    path('api/jobs/<uuid:job_id>/applications/', JobApplicationsView.as_view(), name='job_applications'),
    path('api/applications/', include('applications.urls')),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
