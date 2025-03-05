from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import User, EmployerProfile, JobSeekerProfile, VerificationToken, PasswordResetToken
from .serializers import UserSerializer, RegisterSerializer, VerificationTokenSerializer, JobSeekerProfileSerializer, EmployerProfileSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer
from .tasks import send_password_reset_email
from drf_yasg.utils import swagger_auto_schema
from django.http import Http404
from drf_yasg import openapi

class RegisterView(generics.CreateAPIView):
    """
    API view for registering a new user.

    Accepts email, password, first_name, last_name, optional phone_number, and optional role in the request body.
    Creates a user and associated profile, returning the profile details and a success message.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Determine the profile serializer based on role
        if user.role == 'job_seeker':
            profile = JobSeekerProfile.objects.get(user=user)
            profile_serializer = JobSeekerProfileSerializer(profile)
        elif user.role == 'employer':
            profile = EmployerProfile.objects.get(user=user)
            profile_serializer = EmployerProfileSerializer(profile)
        elif user.role == 'admin':
            profile_serializer = UserSerializer(user)
        else:
            raise ValueError("Invalid role for profile creation")

        # Combine profile data with message
        response_data = profile_serializer.data
        return Response(response_data, status=status.HTTP_201_CREATED)

class LogoutView(generics.GenericAPIView):
    """
    API view to log out a user by blacklisting their refresh token.

    This endpoint requires JWT authentication and expects a POST request with a valid
    refresh token in the request body. Upon success, the refresh token is blacklisted,
    preventing further use and effectively logging out the user. Only authenticated
    users can access this endpoint.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Log out a user by blacklisting their refresh token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={
                'refresh': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The refresh token to blacklist",
                    example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Logout successful",
                examples={'application/json': {"message": "Logged out successfully"}}
            ),
            400: openapi.Response(
                description="Invalid token",
                examples={'application/json': {"error": "Invalid or missing refresh token"}}
            ),
            401: "Authentication required"
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to blacklist a refresh token.

        Args:
            request: The incoming HTTP request containing the refresh token.

        Returns:
            Response: JSON response with success message or error details.
        """
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the refresh token
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

        except TokenError:
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Logout failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving the authenticated user's profile.

    Requires JWT authentication via the Authorization header.
    Includes phone_number and email verification status in the response.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Return the currently authenticated user.

        Returns:
            User: The user instance associated with the request.
        """
        return self.request.user

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API view for retrieving and updating the authenticated user's profile.

    Requires JWT authentication via the Authorization header.
    Supports 'job_seeker' (JobSeekerProfile) and 'employer' (EmployerProfile) roles.
    Returns phone_number and email verification status in the response.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Retrieve the authenticated user's profile based on their role.

        - Job Seekers: Returns or creates a JobSeekerProfile.
        - Employers: Returns or creates an EmployerProfile with a default company name.
        - Admins: Raises 404 as they have no profile.

        Raises:
            Http404: If the user is not authenticated or has an invalid role.
        """
        user = self.request.user
        if not user.is_authenticated:
            raise Http404("Authentication required")  # Triggers 401 via IsAuthenticated
        if user.role == 'job_seeker':
            profile, created = JobSeekerProfile.objects.get_or_create(user=user)
            return profile
        elif user.role == 'employer':
            profile, created = EmployerProfile.objects.get_or_create(
                user=user, defaults={'company_name': f"{user.first_name}'s Company"}
            )
            return profile
        elif user.role == 'admin':
            raise Http404("Admins do not have profiles")
        raise Http404("No profile exists for this user's role")

    def get_serializer_class(self):
        """
        Dynamically return the appropriate serializer based on the user's role.

        - Job Seekers: JobSeekerProfileSerializer.
        - Employers: EmployerProfileSerializer.
        - Admins: Raises 404.

        Handles Swagger schema generation by defaulting to JobSeekerProfileSerializer.
        """
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return JobSeekerProfileSerializer  # Default for Swagger
        if user.role == 'job_seeker':
            return JobSeekerProfileSerializer
        elif user.role == 'employer':
            return EmployerProfileSerializer
        elif user.role == 'admin':
            raise Http404("Admins do not have profiles")
        raise Http404("Invalid role for profile access")

    @swagger_auto_schema(
        operation_summary="Retrieve User Profile",
        operation_description="""
        Retrieves the authenticated user's profile based on their role:
        - Job Seekers: Returns JobSeekerProfile with skills, resume, and experience.
        - Employers: Returns EmployerProfile with company_name and website.
        - Admins: Not supported (404).
        Includes user details (first_name, last_name, phone_number, email, is_email_verified, role).
        Requires JWT authentication via the `Authorization` header (e.g., `Bearer <token>`).
        """,
        responses={
            200: openapi.Response(
                description="User profile retrieved successfully",
                examples={
                    'application/json': {
                        'job_seeker': {
                            "id": "ae6e63e2-618d-4957-90b7-dba945cc3c81",
                            "first_name": "Jane",
                            "last_name": "Doe",
                            "phone_number": "1234567890",
                            "email": "jane@example.com",
                            "is_email_verified": False,
                            "role": "job_seeker",
                            "skills": "Python, Django",
                            "resume": "file",
                            "experience": "5 years"
                        },
                        'employer': {
                            "id": "ae6e63e2-618d-4957-90b7-dba945cc3c81",
                            "first_name": "Tobenna",
                            "last_name": "Obiasor",
                            "phone_number": "07068669403",
                            "email": "tobennaobiasor@gmail.com",
                            "is_email_verified": False,
                            "role": "employer",
                            "company_name": "ABCD company",
                            "website": None
                        }
                    }
                }
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            404: openapi.Response(
                description="Not Found - Profile not available for this role (e.g., admin)",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve the user's profile."""
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update User Profile",
        operation_description="""
        Updates the authenticated user's profile (partial updates allowed). Fields depend on role:
        - Job Seekers: Can update user fields (first_name, last_name, phone_number) and profile fields (skills, resume, experience).
        - Employers: Can update user fields and profile fields (company_name, website).
        - Admins: Not supported (404).
        Requires JWT authentication via the `Authorization` header (e.g., `Bearer <token>`).
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="User's first name", example="Tobenna"),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="User's last name", example="Obiasor"),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="User's phone number", example="07068669403"),
                'skills': openapi.Schema(type=openapi.TYPE_STRING, description="Skills for Job Seeker profile", example="Python, Django"),
                'resume': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY, description="Resume file for Job Seeker profile"),
                'experience': openapi.Schema(type=openapi.TYPE_STRING, description="Experience for Job Seeker profile", example="5 years"),
                'company_name': openapi.Schema(type=openapi.TYPE_STRING, description="Company name for Employer profile", example="ABCD company"),
                'website': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, description="Website for Employer profile", example="https://abcd.com"),
            },
            description="Fields depend on role: 'job_seeker' uses skills/resume/experience, 'employer' uses company_name/website. User fields are editable."
        ),
        responses={
            200: openapi.Response(
                description="Profile updated successfully",
                examples={
                    'application/json': {
                        'job_seeker': {
                            "user": {
                                "id": "ae6e63e2-618d-4957-90b7-dba945cc3c81",
                                "first_name": "Jane",
                                "last_name": "Doe",
                                "phone_number": "1234567890",
                                "email": "jane@example.com",
                                "is_email_verified": False,
                                "role": "job_seeker"
                            },
                            "skills": "Python, Django",
                            "resume": "file",
                            "experience": "5 years"
                        },
                        'employer': {
                            "user": {
                                "id": "ae6e63e2-618d-4957-90b7-dba945cc3c81",
                                "first_name": "Tobenna",
                                "last_name": "Obiasor",
                                "phone_number": "07068669403",
                                "email": "tobennaobiasor@gmail.com",
                                "is_email_verified": False,
                                "role": "employer"
                            },
                            "company_name": "ABCD company",
                            "website": None
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Bad request - Invalid data provided",
                examples={"application/json": {"phone_number": "Invalid format."}}
            ),
            401: openapi.Response(
                description="Unauthorized - Invalid or missing JWT token",
                examples={"application/json": {"detail": "Authentication credentials were not provided."}}
            ),
            404: openapi.Response(
                description="Not Found - Profile not available for this role (e.g., admin)",
                examples={"application/json": {"detail": "Not found."}}
            )
        }
    )
    def patch(self, request, *args, **kwargs):
        """
        Handle PATCH request to partially update the user's profile.

        Allows partial updates to fields based on the user's role.
        """
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Allows partial updates to the user's profile."""
        kwargs["partial"] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
class VerifyEmailView(generics.GenericAPIView):
    """
    A view for verifying a user's email address using a token.

    This view handles GET requests to verify a user's email address by validating a unique token
    provided as a query parameter.

    A query parameter named `token` must be passed to the view
    """
    serializer_class = VerificationTokenSerializer
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        token = request.query_params.get('token')
        try:
            verification_token = VerificationToken.objects.get(token=token)
            user = verification_token.user
            if not user.is_email_verified:
                user.is_email_verified = True
                user.save()
                verification_token.delete()  # Token is single-use
                return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)
            return Response({"message": "Email already verified"}, status=status.HTTP_200_OK)
        except VerificationToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        
class PasswordResetRequestView(generics.GenericAPIView):
    """
    A view for requesting a password reset.

    Accepts an email address, generates a reset token if the email exists, 
    and sends a reset email asynchronously. Returns success even if the email 
    doesn’t exist to prevent email enumeration attacks.
    """
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]  # Open to anyone

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            token = PasswordResetToken.objects.create(user=user)
            send_password_reset_email.delay(user.id, str(token.token))
            return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "Password reset email sent"}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(generics.GenericAPIView):
    """
    A view for confirming a password reset.

    Accepts a reset token and new password, verifies the token, updates the 
    user’s password if valid, and deletes the token to prevent reuse.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]  # Open to anyone with a valid token

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            reset_token.delete()
            return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)
        except PasswordResetToken.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)