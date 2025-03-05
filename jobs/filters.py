# jobs/filters.py
from django_filters import rest_framework as filters
from .models import JobPosting

class JobPostingFilter(filters.FilterSet):
    title = filters.CharFilter(lookup_expr='icontains')  # Case-insensitive search
    description = filters.CharFilter(lookup_expr='icontains')
    # category = filters.ChoiceFilter(choices=JobPosting.category)
    category = filters.CharFilter(field_name='category', lookup_expr='exact')
    country = filters.CharFilter(field_name='location__country', lookup_expr='exact')
    city = filters.CharFilter(field_name='location__city', lookup_expr='exact')
    salary = filters.NumberFilter(field_name='salary', lookup_expr='gte')  # Greater than or equal
    

    class Meta:
        model = JobPosting
        fields = ['title', 'description', 'category', 'country', 'city', 'salary']