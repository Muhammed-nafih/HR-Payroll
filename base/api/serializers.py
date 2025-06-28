from rest_framework import serializers
from base.models import (ShiftRequest,
Company,
Department,
JobPosition,
JobRole,
WorkType,
Announcement,
AnnouncementView,
AnnouncementComment,
ShiftRequestComment,
BaserequestFile,
WorkTypeRequestComment,
EmployeeShiftSchedule, 
EmployeeShift,
RotatingShift,
EmployeeType,
Tags,



)
from employee.models import Actiontype
from django import forms
from horilla_audit.models import AuditTag

class ShiftRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftRequest
        fields = '__all__'



class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'



class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'



class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = '__all__' 



class JobPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosition
        fields = '__all__'



class JobPositionMultiForm(forms.ModelForm):
    company_id = forms.ModelMultipleChoiceField(
        queryset=Company.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    
    class Meta:
        model = JobPosition
        fields = '__all__'


class JobRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRole
        fields = "__all__"  # Include all fields or specify the necessary ones



class WorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkType
        fields = '__all__'



class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = '__all__'



class AnnouncementViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementView
        fields = '__all__'



class AnnouncementCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementComment
        fields = '__all__'




class ActiontypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actiontype
        fields = '__all__'



class ShiftRequestCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftRequestComment
        fields = '__all__'



class BaserequestFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaserequestFile
        fields = '__all__'



class WorkTypeRequestCommentSerializer(serializers.ModelSerializer):
    files = BaserequestFileSerializer(many=True, read_only=True)

    class Meta:
        model = WorkTypeRequestComment
        fields = '__all__'


class EmployeeShiftScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShiftSchedule
        fields = '__all__'

class EmployeeShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShift
        fields = '__all__'


class RotatingShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotatingShift
        fields = '__all__'




class EmployeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeType
        fields = '__all__'



class AuditTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditTag
        fields = '__all__'



class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = '__all__'

