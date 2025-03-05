from django.test import TestCase

# Create your tests here.
# jobs/tests.py
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from authentication.models import User
from .models import JobPosting, Location

class JobPostingFilterTest(APITestCase):
    def setUp(self):
        self.job_list_url = '/api/jobs/'
        self.token_url = '/api/auth/token/'
        
        # Create test users
        self.employer = User.objects.create_user(
             email='employer@example.com', password='pass123', role='employer'
        )
        self.job_seeker = User.objects.create_user(
            email='seeker@example.com', password='pass123', role='job_seeker'
        )
        
        # Obtain JWT tokens
        employer_response = self.client.post(
            self.token_url, {'email': 'employer@example.com', 'password': 'pass123'}, format='json'
        )
        seeker_response = self.client.post(
            self.token_url, {'email': 'seeker@example.com', 'password': 'pass123'}, format='json'
        )
        self.employer_access_token = employer_response.data['access']
        self.seeker_access_token = seeker_response.data['access']
        
        # Create test locations and jobs
        self.loc1 = Location.objects.create(country='US', city='San Francisco', address='address 1')
        self.loc2 = Location.objects.create(country='Canada', city='Toronto', address='address 2')
        self.job1 = JobPosting.objects.create(
            employer=self.employer, title='Software Engineer', description='Python dev job',
            category='engineering', location=self.loc1, salary=80000, is_active=True
        )
        self.job2 = JobPosting.objects.create(
            employer=self.employer, title='Sales Manager', description='Lead sales team',
            category='tech', location=self.loc2, salary=60000, is_active=True
        )
        self.job3 = JobPosting.objects.create(
            employer=self.employer, title='Inactive Job', category='other',
            location=self.loc1, salary=50000, is_active=False
        )

    def test_filter_by_title(self):
        """Test filtering jobs by title (case-insensitive)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seeker_access_token}')
        response = self.client.get(f'{self.job_list_url}?title=software', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Software Engineer')

    def test_filter_by_category(self):
        """Test filtering jobs by category."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seeker_access_token}')
        response = self.client.get(f'{self.job_list_url}?category=tech', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['category'], 'tech')

    def test_filter_by_country(self):
        """Test filtering jobs by country."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seeker_access_token}')
        response = self.client.get(f'{self.job_list_url}?country=US', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['location']['country'], 'US')

    def test_filter_by_city(self):
        """Test filtering jobs by city."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seeker_access_token}')
        response = self.client.get(f'{self.job_list_url}?city=Toronto', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['location']['city'], 'Toronto')

    def test_filter_by_salary(self):
        """Test filtering jobs by salary (>=)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seeker_access_token}')
        response = self.client.get(f'{self.job_list_url}?salary=70000', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Software Engineer')
        self.assertTrue(float(response.data['results'][0]['salary']) >= 70000)


    def test_employer_sees_all_jobs(self):
        """Test employer sees all their jobs, including inactive."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.employer_access_token}')
        response = self.client.get(f'{self.job_list_url}?country=US', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        titles = [job['title'] for job in response.data['results']]
        self.assertIn('Software Engineer', titles)
        self.assertIn('Inactive Job', titles)

    def test_pagination(self):
        """Test pagination limits results."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.seeker_access_token}')
        response = self.client.get(f'{self.job_list_url}?page=1', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) <= 10)

    def test_unauthenticated_access(self):
        """Test unauthenticated requests are rejected."""
        self.client.credentials()
        response = self.client.get(self.job_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)