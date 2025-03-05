# jobs/views.py (assuming this is the file based on context)
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsEmployer, IsJobOwner
from .models import JobPosting
from .serializers import JobPostingSerializer
from .filters import JobPostingFilter
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.cache import cache

class JobPostingListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating job postings.

    - GET: Returns a list of job postings with nested location.
    - POST: Creates a job posting with flat location fields.
    Requires JWT authentication.
    """
    serializer_class = JobPostingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = JobPostingFilter

    def get_permissions(self):
        """
        Dynamically assign permissions based on the HTTP method.
        """
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsEmployer()]  # Only employers can create
        return [IsAuthenticated()]  # Anyone authenticated can list

    def get_queryset(self):
        """
        Filter queryset based on user role:
        - Employers: See only their own jobs.
        - Job Seekers/Admins: See all active jobs.
        """
        user = self.request.user
        base_queryset = JobPosting.objects.select_related('employer', 'location')

        if user.role == 'employer':
            # Employer-specific queryset: filter by user, no caching needed as it’s user-specific
            return base_queryset.filter(employer=user).order_by('-created_at')
        else:
            # Job seekers and admins: fetch active jobs, cache for performance
            cache_key = 'active_jobs_queryset'
            cached_queryset = cache.get(cache_key)
            if cached_queryset is None:
                cached_queryset = base_queryset.filter(is_active=True).order_by('-created_at')
                # Cache for 15 minutes (adjust based on update frequency)
                cache.set(cache_key, cached_queryset, 15 * 60)
            return cached_queryset

    def perform_create(self, serializer):
        """Save a new job posting and invalidate the active jobs cache."""
        job = serializer.save(employer=self.request.user)
        # Invalidate cache since a new active job is added
        cache.delete('active_jobs_queryset')
        return job
    
    @swagger_auto_schema(
        operation_summary="List Job Postings",
        operation_description="""
        Retrieves a list of job postings based on the authenticated user's role:
        - Employers: See only their own job postings.
        - Job Seekers/Admins: See all active job postings.
        - Allow filtering via query parameters for `title`, `description`, `category`, `country`, `city`, `salary` (returns all values greater than or equal to given value)
        Returns job postings with nested location details (country, city, address).
        Requires JWT authentication via the `Authorization` header (e.g., `Bearer <token>`).
        """,
        responses={
            200: openapi.Response(
                description="A list of job postings",
                schema=JobPostingSerializer(many=True)
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a Job Posting",
        operation_description="""
        Creates a new job posting. Only authenticated users with the `employer` role can create job postings.
        The request must include flat location fields (location_country, location_city, location_address),
        which are used to create or link a Location object. Requires JWT authentication via the `Authorization`
        header (e.g., `Bearer <token>`).
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Job title'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Job description'),
                'category': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['engineering', 'sales', 'marketing', 'design', 'management', 'other'],
                    description='Job category'
                ),
                'location_country': openapi.Schema(type=openapi.TYPE_STRING, description='Country of the job location'),
                'location_city': openapi.Schema(type=openapi.TYPE_STRING, description='City of the job location'),
                'location_address': openapi.Schema(type=openapi.TYPE_STRING, description='Address of the job location', nullable=True),
                'salary_min': openapi.Schema(type=openapi.TYPE_NUMBER, format='float', description='Minimum salary', nullable=True),
                'salary_max': openapi.Schema(type=openapi.TYPE_NUMBER, format='float', description='Maximum salary', nullable=True)
            },
            required=['title', 'description', 'category', 'location_country', 'location_city']
        ),
        responses={
            201: JobPostingSerializer,
            400: openapi.Response(
                description="Bad request - Invalid input",
                examples={
                    "application/json": [
                        {"title": "This field is required."},
                        {"location_country": "This field is required."}
                    ]
                }
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User lacks `employer` role",
                examples={"application/json": {"detail": "You do not have permission to perform this action."}}
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class JobPostingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting a specific job posting.

    - GET: Returns a single job posting with nested location.
    - PUT: Updates a job posting (full update) with flat location fields.
    - PATCH: Updates a job posting (partial update) with flat location fields.
    - DELETE: Deletes a job posting.
    Requires JWT authentication.
    """
    serializer_class = JobPostingSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Dynamically assign permissions based on the HTTP method.
        """
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsEmployer(), IsJobOwner()]  # Only job owner can update/delete
        elif self.request.user.role == 'employer':
            return [IsAuthenticated(), IsJobOwner()]
        return [IsAuthenticated()]  # Anyone authenticated can retrieve

    def get_queryset(self):
        """
        Filter queryset based on user role:
        - Employers: See only their own jobs.
        - Job Seekers/Admins: See all active jobs.
        """
        user = self.request.user
        if user.role == 'employer':
            return JobPosting.objects.filter(employer=user)
        return JobPosting.objects.filter(is_active=True)

    def get_object(self):
        """
        Retrieve a specific job posting, respecting permissions.
        """
        obj = generics.get_object_or_404(JobPosting, id=self.kwargs['id'])
        self.check_object_permissions(self.request, obj)
        return obj

    @swagger_auto_schema(
        operation_summary="Retrieve a Job Posting",
        operation_description="""
        Retrieves details of a specific job posting based on the authenticated user's role:
        - Employers: Can only view their own job postings.
        - Job Seekers/Admins: Can view any active job posting.
        Returns the job posting with nested location details (country, city, address).
        Requires JWT authentication via the `Authorization` header (e.g., `Bearer <token>`).
        """,
        responses={
            200: JobPostingSerializer,
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            404: openapi.Response(
                description="Not Found - Job posting does not exist or is inaccessible",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update a Job Posting (Full)",
        operation_description="""
        Fully updates a specific job posting. Only the employer who owns the job can update it.
        The request must include flat location fields (location_country, location_city, location_address),
        which are used to update or link a Location object. Requires JWT authentication via the
        `Authorization` header (e.g., `Bearer <token>`).
        """,
        request_body=JobPostingSerializer,
        responses={
            200: JobPostingSerializer,
            400: openapi.Response(
                description="Bad request - Invalid input",
                examples={"application/json": {"category": "Invalid choice."}}
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User is not the job owner or lacks `employer` role",
                examples={"application/json": {"detail": "You do not have permission to perform this action."}}
            ),
            404: openapi.Response(
                description="Not Found - Job posting does not exist",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update a Job Posting",
        operation_description="""
        Partially updates a specific job posting (e.g., just the status or title). Only the employer
        who owns the job can update it. Flat location fields (location_country, location_city,
        location_address) can be included to update the location. Requires JWT authentication via
        the `Authorization` header (e.g., `Bearer <token>`).
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='Job title', nullable=True),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Job description', nullable=True),
                'category': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['engineering', 'sales', 'marketing', 'design', 'management', 'other'],
                    description='Job category',
                    nullable=True
                ),
                'location_country': openapi.Schema(type=openapi.TYPE_STRING, description='Country of the job location', nullable=True),
                'location_city': openapi.Schema(type=openapi.TYPE_STRING, description='City of the job location', nullable=True),
                'location_address': openapi.Schema(type=openapi.TYPE_STRING, description='Address of the job location', nullable=True),
                'salary_min': openapi.Schema(type=openapi.TYPE_NUMBER, format='float', description='Minimum salary', nullable=True),
                'salary_max': openapi.Schema(type=openapi.TYPE_NUMBER, format='float', description='Maximum salary', nullable=True)
            }
        ),
        responses={
            200: JobPostingSerializer,
            400: openapi.Response(
                description="Bad request - Invalid input",
                examples={"application/json": {"category": "Invalid choice."}}
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User is not the job owner or lacks `employer` role",
                examples={"application/json": {"detail": "You do not have permission to perform this action."}}
            ),
            404: openapi.Response(
                description="Not Found - Job posting does not exist",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def patch(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete a Job Posting",
        operation_description="""
        Deletes a specific job posting. Only the employer who owns the job can delete it.
        Requires JWT authentication via the `Authorization` header (e.g., `Bearer <token>`).
        """,
        responses={
            204: openapi.Response(description="No Content - Job posting deleted successfully"),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User is not the job owner or lacks `employer` role",
                examples={"application/json": {"detail": "You do not have permission to perform this action."}}
            ),
            404: openapi.Response(
                description="Not Found - Job posting does not exist",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)