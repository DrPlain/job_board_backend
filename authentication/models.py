from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid

class CustomUserManager(BaseUserManager):
    """
    Custom user manager to handle creation of users with email instead of username.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and return a regular user with an email and password.

        Args:
            email (str): The user's email address.
            password (str, optional): The user's password (hashed before saving).
            **extra_fields: Additional fields for the User model (e.g., phone_number, role).

        Returns:
            User: The created user instance.
        """
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Hash the password
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with an email and password.

        Args:
            email (str): The superuser's email address.
            password (str, optional): The superuser's password (hashed before saving).
            **extra_fields: Additional fields (defaults role to 'admin').

        Returns:
            User: The created superuser instance.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # Default to admin role

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    Custom user model extending AbstractUser for role-based authentication.

    This model replaces the default username with email as the unique identifier,
    adds a role field for distinguishing between admins and regular users,
    includes a phone number, and tracks email verification status. The password
    field (inherited from AbstractUser) is automatically hashed using Django's
    built-in password hashing system when set via create_user or set_password.
    """
    ROLE_CHOICES = (
        ('admin', 'Admin'),  # Can manage jobs and categories
        ('job_seeker', 'Job Seeker'),    # Can apply to jobs
        ('employer', 'Employer'), # Can create jobs
    )
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Optional phone number
    is_email_verified = models.BooleanField(default=False)  # Tracks email verification
    created_at = models.DateTimeField(auto_now_add=True)

    # Custom manager
    objects = CustomUserManager()

    # Override username field behavior
    USERNAME_FIELD = 'email'  # Use email for authentication instead of username
    REQUIRED_FIELDS = ['first_name', 'last_name']      # No additional fields required beyond email/password

    def __str__(self):
        """Return a string representation of the user."""
        return self.email

    class Meta:
        """Metadata for the User model."""
        verbose_name = "User"
        verbose_name_plural = "Users"

class JobSeekerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='job_seeker_profile')
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    skills = models.TextField()
    experience = models.IntegerField(default=0)

class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

class VerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification_token')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.username}"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True)  # Optional: Add expiration logic

    def __str__(self):
        return f"Reset token for {self.user.username}"