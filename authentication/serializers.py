from rest_framework import serializers
from .models import User, JobSeekerProfile, EmployerProfile, VerificationToken
from .tasks import send_verification_email


class UserSerializer(serializers.ModelSerializer):
    """Serializer for retrieving and displaying user details."""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'is_email_verified', 'created_at']
        read_only_fields = ['id', 'created_at', 'is_email_verified']  # Prevent modification

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='job_seeker')
    phone_number = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone_number", "role"]

    def create(self, validated_data):
        # Extract profile-specific data if provided (optional fields)
        role = validated_data.get('role', 'job_seeker')
        
        # Create the User
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            role=role
        )

        # Create associated profile based on role
        if role == 'job_seeker':
            JobSeekerProfile.objects.create(user=user)
        elif role == 'employer':
            EmployerProfile.objects.create(user=user, company_name=f"{user.first_name}'s Company")
        return user
    
    def create(self, validated_data):
        """
        Create a new user instance with a hashed password.

        Uses User.objects.create_user to ensure the password is hashed before
        saving to the database.

        Args:
            validated_data (dict): Validated data from the request.

        Returns:
            User: The newly created user instance.
        """
        user = User.objects.create_user(**validated_data)
        if user.role == 'job_seeker':
            JobSeekerProfile.objects.create(user=user)
        elif user.role == 'employer':
            EmployerProfile.objects.create(user=user)
        
        # Create verification token and send email
        token = VerificationToken.objects.create(user=user)
        send_verification_email.delay(user.id, str(token.token))
        return user

class LoginSerializer(serializers.Serializer):
    """
    Serializer for validating login credentials.

    Used with JWT token generation to authenticate users. The password is
    checked against the hashed value stored in the database.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class EmployerProfileSerializer(serializers.ModelSerializer):
    # Writable fields from User model
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False, allow_blank=True)
    email = serializers.EmailField(source='user.email', read_only=True)  # Keep email read-only to prevent changes
    is_email_verified = serializers.BooleanField(source='user.is_email_verified', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)

    # Add jobs_posted field
    # jobs_posted = JobPostingSerializer(many=True, read_only=True, source='user.jobs_posted')

    class Meta:
        model = EmployerProfile
        fields = [
            "first_name", "last_name", "phone_number", "email", "is_email_verified", "role",
            "company_name", "website"
        ]

    def update(self, instance, validated_data):
        # Extract and update User fields
        user_data = validated_data.pop('user', {})
        if user_data:
            user = instance.user
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.phone_number = user_data.get('phone_number', user.phone_number)
            user.save()

        # Update EmployerProfile fields
        return super().update(instance, validated_data)

class JobSeekerProfileSerializer(serializers.ModelSerializer):
    # Writable fields from User model
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False, allow_blank=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_email_verified = serializers.BooleanField(source='user.is_email_verified', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = JobSeekerProfile
        fields = [
            "first_name", "last_name", "phone_number", "email", "is_email_verified", "role",
            "skills", "resume", "experience"
        ]

    def update(self, instance, validated_data):
        # Extract and update User fields
        user_data = validated_data.pop('user', {})
        if user_data:
            user = instance.user
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            user.phone_number = user_data.get('phone_number', user.phone_number)
            user.save()

        # Update JobSeekerProfile fields
        return super().update(instance, validated_data)
    
class VerificationTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationToken
        fields = ['token']

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)