from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from authentication.models import User, JobSeekerProfile, EmployerProfile  # Adjust if path differs
from rest_framework.authtoken.models import Token

class UserModelTest(TestCase):
    def setUp(self):
        self.user_data = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'phone_number': 'phone_number',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'role': 'job_seeker'
        }
    
    def test_create_user(self):
        """Test creating a user with custom role."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.first_name, 'first_name')
        self.assertTrue(user.last_name, 'last_name')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.check_password('testpassword123'))
        self.assertEqual(user.role, 'job_seeker')

    def test_user_string_representation(self):
        """Test the string representation of the User model."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'testuser@example.com')


class RegisterViewTest(APITestCase):
    def setUp(self):
        self.register_url = '/api/auth/register/'
        self.user_data = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'phone_number': 'phone_number',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'role': 'job_seeker'
        }

    def test_register_success_job_seeker(self):
        """Test successful registration for a job seeker with profile creation."""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'testuser@example.com')
        self.assertEqual(response.data['role'], 'job_seeker')
        
        # Check user and profile creation
        user = User.objects.get(email="testuser@example.com")
        self.assertTrue(user.check_password('testpassword123'))
        self.assertTrue(JobSeekerProfile.objects.filter(user=user).exists())
        self.assertFalse(EmployerProfile.objects.filter(user=user).exists())

    def test_register_success_employer(self):
        """Test successful registration for an employer with profile creation."""
        employer_data = self.user_data.copy()
        employer_data['role'] = 'employer'
        response = self.client.post(self.register_url, employer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'employer')
        
        # Check profile creation
        user = User.objects.get(email="testuser@example.com")
        self.assertTrue(EmployerProfile.objects.filter(user=user).exists())
        self.assertFalse(JobSeekerProfile.objects.filter(user=user).exists())

    def test_register_missing_fields(self):
        """Test registration fails with missing required fields."""
        incomplete_data = {'username': 'incomplete'}
        response = self.client.post(self.register_url, incomplete_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)

    def test_register_duplicate_email(self):
        """Test registration fails with a duplicate email."""
        User.objects.create_user(**self.user_data)
        duplicate_data = self.user_data.copy()
        duplicate_data['email'] = 'testuser@example.com'
        response = self.client.post(self.register_url, duplicate_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_invalid_role(self):
        """Test registration with an invalid role raises an HTTP 400 error."""
        invalid_data = self.user_data.copy()
        invalid_data['role'] = 'invalid_role'
        response = self.client.post(self.register_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)
        self.assertIn('not a valid choice', str(response.data['role']))

class LoginViewTest(APITestCase):
    def setUp(self):
        self.login_url = '/api/auth/token/'
        self.user_data = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'phone_number': 'phone_number',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'role': 'job_seeker'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.token = Token.objects.create(user=self.user)

    def test_login_success(self):
        """Test successful login with correct credentials."""
        login_data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_invalid_credentials(self):
        """Test login fails with incorrect password."""
        login_data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('No active account found with the given credentials', response.data['detail'])

    def test_login_missing_fields(self):
        """Test login fails with missing fields."""
        login_data = {'email': 'testuser@example.com'}
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

class ProfileSignalTest(TestCase):
    def setUp(self):
        self.user_data = {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'phone_number': 'phone_number',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'role': 'job_seeker'
        }

    # def test_job_seeker_profile_creation(self):
    #     """Test JobSeekerProfile is created when a job_seeker user is created."""
    #     user = User.objects.create_user(**self.user_data)
    #     # self.assertTrue(JobSeekerProfile.objects.filter(user_id=user).exists())
    #     profile = JobSeekerProfile.objects.get(user_id=user)
    #     self.assertIn('skills', profile)

    # def test_employer_profile_creation(self):
    #     """Test EmployerProfile is created when an employer user is created."""
    #     employer_data = self.user_data.copy()
    #     employer_data['role'] = 'employer'
    #     user = User.objects.create_user(**employer_data)
    #     self.assertTrue(EmployerProfile.objects.filter(user=user).exists())
    #     profile = EmployerProfile.objects.get(user=user)
    #     self.assertEqual(profile.user, user)
    #     self.assertEqual(profile.company_name, "first_names's Company")

    def test_admin_no_profile(self):
        """Test no profile is created for admin users."""
        admin_data = self.user_data.copy()
        admin_data['role'] = 'admin'
        user = User.objects.create_user(**admin_data)
        self.assertFalse(JobSeekerProfile.objects.filter(user=user).exists())
        self.assertFalse(EmployerProfile.objects.filter(user=user).exists())