from rest_framework import serializers
from .models import JobPosting, Location
# from authentication.serializers import EmployerProfileSerializer # For nested user data
from common.serializers import UserSerializer

class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model."""
    class Meta:
        model = Location
        fields = ['id', 'country', 'city', 'address', 'created_at']
        read_only_fields = ['id', 'created_at']


class JobPostingSerializer(serializers.ModelSerializer):
    """
    Serializer for JobPosting model, handling creation, retrieval, and updates.

    - For GET: Returns nested 'location' object with country, city, address.
    - For POST/PATCH: Accepts flat 'location_country', 'location_city', 'location_address' fields.
    """
    employer = UserSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    
    # Flat location fields for input (write-only)
    location_country = serializers.CharField(write_only=True, required=False)
    location_city = serializers.CharField(write_only=True, required=False)
    location_address = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = JobPosting
        fields = [
            'id', 'title', 'description', 'salary', 'category', 'location',
            'location_country', 'location_city', 'location_address',
            'job_type', 'employer', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'employer']

    def validate(self, data):
        """
        Validate that location fields are provided together during creation or update.
        """
        if self.instance is None:  # Creation
            if not all(k in data for k in ['location_country', 'location_city', 'location_address']):
                raise serializers.ValidationError("All location fields (country, city, address) are required for creating a job posting.")
        else:  # Update
            if any(k in data for k in ['location_country', 'location_city', 'location_address']):
                if not all(k in data for k in ['location_country', 'location_city', 'location_address']):
                    raise serializers.ValidationError("All location fields must be provided together for an update.")
        return data

    def create(self, validated_data):
        """
        Create a new job posting with a Location instance from flat fields.
        """
        country = validated_data.pop('location_country')
        city = validated_data.pop('location_city')
        address = validated_data.pop('location_address')

        # Create or get Location instance
        location, _ = Location.objects.get_or_create(
            country=country,
            city=city,
            address=address
        )
        validated_data['location'] = location
        validated_data['employer'] = self.context['request'].user  # Set employer from authenticated user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Update an existing job posting, handling location updates if provided.
        """
        country = validated_data.pop('location_country', None)
        city = validated_data.pop('location_city', None)
        address = validated_data.pop('location_address', None)

        if country and city and address:
            # Update or create new Location if all fields are provided
            location, _ = Location.objects.get_or_create(
                country=country,
                city=city,
                address=address
            )
            instance.location = location

        return super().update(instance, validated_data)