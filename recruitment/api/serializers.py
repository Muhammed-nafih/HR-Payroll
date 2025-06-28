from rest_framework import serializers
from recruitment.models import Recruitment,Candidate, Stage, Employee, JobPosition, StageNote, Recruitment, JobPosition,InterviewSchedule,RecruitmentSurvey,SurveyTemplate,SkillZone,SkillZoneCandidate
from django.utils.translation import gettext as _

class RecruitmentSerializer(serializers.ModelSerializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False)

    class Meta:
        model = Recruitment
        fields = '__all__'

    def validate(self, data):
        return data


class RecruitmentViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recruitment
        fields = '__all__' 

class RecruitmentSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recruitment
        fields = '__all__'


class StageSerializer(serializers.ModelSerializer):
   
    
    class Meta:
        model = Stage
        fields = '__all__'


class CandidateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Candidate
        fields = '__all__'



class StageNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StageNote
        fields = '__all__'


class CandidateHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate.history.model
        fields = '__all__'


class JobPositionSerializer(serializers.ModelSerializer):
 
    class Meta:
        model = JobPosition
        fields = "__all__"

class RecruitmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recruitment
        fields = "__all__"

from base.models import HorillaMailTemplate

class HorillaMailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorillaMailTemplate
        fields = '__all__'




class InterviewScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedule
        fields = '__all__'




class RecruitmentSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruitmentSurvey
        fields = '__all__'



class SurveyTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyTemplate
        fields = '__all__'


class SkillZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillZone
        fields = '__all__'





class SkillZoneCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillZoneCandidate
        fields = '__all__'
