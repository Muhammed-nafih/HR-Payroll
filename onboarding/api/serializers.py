from rest_framework import serializers
from onboarding.models import OnboardingStage, Employee,Candidate,CandidateTask
from recruitment.models import JobPosition,Recruitment
class OnboardingViewStageSerializer(serializers.ModelSerializer):
    employee_id = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), many=True)

    class Meta:
        model = OnboardingStage
        fields = '__all__'




class CandidateSerializer(serializers.ModelSerializer):
    job_position_id = serializers.PrimaryKeyRelatedField(queryset=JobPosition.objects.all())  # Assuming JobPosition is the related model

    class Meta:
        model = Candidate
        fields = '__all__'



class RecruitmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recruitment
        fields = '__all__'

class OnboardingStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingStage
        fields = '__all__'

class CandidateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateTask
        fields = '__all__'
