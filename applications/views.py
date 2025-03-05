# applications/views.py
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import JobApplication
from jobs.models import JobPosting
from .serializers import JobApplicationSerializer
from authentication.permissions import IsJobSeeker, IsEmployer, IsAdminUser  # Adjust import path as needed
from .tasks import send_application_submitted_email, send_application_accepted_email

class JobApplicationListCreate(generics.ListCreateAPIView):
    """
    A view for listing and creating job applications.

    This view allows authenticated users to list job applications based on their role and enables
    job seekers to create new applications. It supports GET requests to retrieve a filtered list
    of applications and POST requests to submit a new application.

    Attributes:
        serializer_class (JobApplicationSerializer): The serializer used to handle input/output data.
    """
    serializer_class = JobApplicationSerializer

    def get_queryset(self):
        """
        Return a filtered queryset of job applications based on the user's role.

        - Job Seekers: Returns applications they submitted.
        - Employers: Returns applications for jobs they posted.
        - Admins: Returns all applications.
        - Others: Returns an empty queryset.

        Returns:
            QuerySet: A filtered set of JobApplication objects.
        """
        user = self.request.user
        if user.role == 'job_seeker':  # Adjusted 'role' to 'role' based on prior User model
            return JobApplication.objects.filter(job_seeker=user)
        elif user.role == 'employer':
            return JobApplication.objects.filter(job__employer=user)
        elif user.role == 'admin':
            return JobApplication.objects.all()
        return JobApplication.objects.none()

    def get_permissions(self):
        """
        Determine permissions based on the HTTP method.

        - POST: Restricted to job seekers only, allowing them to apply for jobs.
        - GET: Available to all authenticated users, with results filtered by role.

        Returns:
            list: A list of permission classes to apply.
        """
        if self.request.method == 'POST':
            return [IsJobSeeker()]
        return [permissions.IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="List Job Applications",
        operation_description="""
        Retrieves a list of job applications based on the authenticated user's role:
        - Job Seekers: See their own applications.
        - Employers: See applications to their jobs.
        - Admins: See all applications.
        Requires authentication via a token in the `Authorization` header.
        """,
        responses={
            200: openapi.Response(
                description="A list of job applications",
                schema=JobApplicationSerializer(many=True)
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing authentication token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """
        Handle GET requests to list job applications.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create a Job Application",
        operation_description="""
        Creates a new job application for a specified job. Only authenticated users with the
        `job_seeker` role can submit applications. The `job_id` must correspond to an existing job,
        and job seekers cannot apply to their own jobs.
        Requires authentication via a token in the `Authorization` header.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'job_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the job to apply to')
            },
            required=['job_id']
        ),
        responses={
            201: JobApplicationSerializer,
            400: openapi.Response(
                description="Bad request - Invalid input",
                examples={
                    "application/json": [
                        {"job_id": "This field is required."},
                        {"detail": "You cannot apply to your own job."}
                    ]
                }
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing authentication token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User lacks `job_seeker` role",
                examples={"application/json": {"detail": "You do not have permission to perform this action."}}
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to create a new job application.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Trigger email task
        job_seeker_email = request.user.email
        job_title = serializer.validated_data['job'].title
        send_application_submitted_email.delay(job_seeker_email, job_title)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        Save a new job application with the authenticated user as the job seeker.

        Args:
            serializer (JobApplicationSerializer): The serializer instance with validated data.
        """
        serializer.save(job_seeker=self.request.user)


class JobApplicationDetail(generics.RetrieveUpdateAPIView):
    """
    A view for retrieving and updating individual job applications.

    This view allows authenticated users to view application details and permits employers or
    admins to update the application status. Access is restricted based on user role to ensure
    privacy and proper authorization.

    - GET: Allowed for authenticated users (job seekers for their own applications,
          employers for their jobs, admins for all).
    - PUT: Restricted to employers (for their jobs) or admins to update the status.

    Attributes:
        queryset (QuerySet): All JobApplication objects, filtered by get_object().
        serializer_class (JobApplicationSerializer): The serializer for handling application data.
    """
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer

    def get_permissions(self):
        """
        Determine permissions based on the HTTP method.

        - GET: Allowed for authenticated users (job seekers for their own applications,
          employers for their jobs, admins for all).
        - PUT: Restricted to employers (for their jobs) or admins to update the status.

        Returns:
            list: A list of permission classes to apply.
        """
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        elif self.request.method == 'PUT':
            return [permissions.IsAuthenticated(), IsEmployer() or IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @swagger_auto_schema(
        operation_summary="Retrieve a Job Application",
        operation_description="""
        Retrieves details of a specific job application. Access is restricted by role:
        - Job Seekers: Can only view their own applications.
        - Employers: Can only view applications for their jobs.
        - Admins: Can view all applications.
        Requires authentication via a token in the `Authorization` header.
        """,
        responses={
            200: JobApplicationSerializer,
            401: openapi.Response(
                description="Unauthorized - Invalid or missing authentication token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User lacks permission to view this application",
                examples={
                    "application/json": [
                        {"detail": "You can only view your own applications."},
                        {"detail": "You can only view applications for your jobs."}
                    ]
                }
            ),
            404: openapi.Response(
                description="Not Found - Application does not exist",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """
        Handle GET requests to retrieve a job application.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Update a Job Application",
        operation_description="""
        Updates the status of a specific job application. Only employers (for their jobs) or
        admins can update the status. Requires authentication via a token in the `Authorization` header.
        """,
        request_body=JobApplicationSerializer,
        responses={
            200: JobApplicationSerializer,
            400: openapi.Response(
                description="Bad request - Invalid input",
                examples={"application/json": {"status": "Invalid choice."}}
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing authentication token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User lacks permission to update this application",
                examples={"application/json": {"detail": "You do not have permission to perform this action."}}
            ),
            404: openapi.Response(
                description="Not Found - Application does not exist",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def put(self, request, *args, **kwargs):
        """
        Handle PUT requests to update a job application.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_summary="Partially Update a Job Application",
        operation_description="""
        Partially updates a specific job application (e.g., just the status). Only employers (for their jobs)
        or admins can update the application. Requires authentication via a token in the `Authorization` header.
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['submitted', 'reviewed', 'accepted', 'rejected'],
                    description='The new status of the application'
                )
            }
        ),
        responses={
            200: JobApplicationSerializer,
            400: openapi.Response(
                description="Bad request - Invalid input",
                examples={"application/json": {"status": "Invalid choice."}}
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing authentication token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            403: openapi.Response(
                description="Forbidden - User lacks permission to update this application",
                examples={"application/json": {"detail": "You do not have permission to perform this action."}}
            ),
            404: openapi.Response(
                description="Not Found - Application does not exist",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def patch(self, request, *args, **kwargs):
        """
        Handle PATCH requests to partially update a job application.

        Allows partial updates, such as changing the status, without requiring a full representation.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Check if status is changing to 'accepted'
        old_status = instance.status
        self.perform_update(serializer)
        new_status = serializer.instance.status
        
        if old_status != 'accepted' and new_status == 'accepted':
            job_seeker_email = instance.job_seeker.email
            job_title = instance.job.title
            send_application_accepted_email.delay(job_seeker_email, job_title)

        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_object(self):
        """
        Retrieve and restrict access to a specific job application based on user role.

        - Job Seekers: Can only access their own applications.
        - Employers: Can only access applications for their jobs.
        - Admins: Have unrestricted access.

        Raises:
            PermissionDenied: If the user lacks permission to view the application.

        Returns:
            JobApplication: The requested application object.
        """
        obj = super().get_object()
        user = self.request.user
        if user.role == 'job_seeker' and obj.job_seeker != user:
            self.permission_denied(self.request, message="You can only view your own applications.")
        elif user.role == 'employer' and obj.job.employer != user:
            self.permission_denied(self.request, message="You can only view applications for your jobs.")
        elif user.role == 'admin':
            return obj  # Admins can access all
        return obj

    def perform_update(self, serializer):
        """
        Update an existing job application, typically to change its status.

        Args:
            serializer (JobApplicationSerializer): The serializer instance with validated data.
        """
        serializer.save()

class JobApplicationsView(generics.ListAPIView):
    """
    A view for retrieving all applications to a specific job.

    This view allows an employer to see all applications to a particular job posted by him
    Only Employers and Admin can access this view
    """
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer or IsAdminUser]

    def get_queryset(self):
        job_id = self.kwargs.get('job_id')  # Safely get job_id
        if not job_id:
            return JobApplication.objects.none()  # Return empty if no job_id
        user = self.request.user
        try:
            job = JobPosting.objects.get(id=job_id, employer=user)
            return JobApplication.objects.filter(job=job)
        except JobPosting.DoesNotExist:
            return JobApplication.objects.none()