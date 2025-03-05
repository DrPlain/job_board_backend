# applications/serializers.py
from rest_framework import serializers
from .models import JobApplication
from jobs.serializers import JobPostingSerializer
from common.serializers import UserSerializer
from jobs.models import JobPosting

class JobApplicationSerializer(serializers.ModelSerializer):
    job = JobPostingSerializer(read_only=True)
    job_seeker = UserSerializer(read_only=True)
    job_id = serializers.PrimaryKeyRelatedField(
        queryset=JobPosting.objects.all(),  # No status filter; all jobs are eligible
        source='job',
        write_only=True
    )

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'job_id', 'job_seeker', 'status', 'applied_at']
        read_only_fields = ['job_seeker', 'applied_at']

    def validate(self, data):
        # Ensure the job_seeker isn't the employer
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.method == 'POST':
                if data['job'].employer == request.user:
                    raise serializers.ValidationError("You cannot apply to your own job.")
        return data