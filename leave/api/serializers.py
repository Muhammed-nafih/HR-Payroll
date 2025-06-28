from rest_framework import serializers
from leave.models import (
LeaveRequest, 
LeaveType, 
LeaveRequestConditionApproval,
LeaveRequest, 
AvailableLeave, 
Employee,
JobPosition, 
RestrictLeave,
Holidays,
LeaveAllocationRequest,
LeaverequestComment,
LeaveallocationrequestComment,
LeaverequestFile,
CompensatoryLeaverequestComment,
CompensatoryLeaveRequest

)
from base.models import PenaltyAccounts
class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = '__all__' 


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'


class LeaveRequestConditionApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestConditionApproval
        fields = '__all__'


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = '__all__'


class LeaveRequestConditionApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestConditionApproval
        fields = '__all__'


class LeaveRequestFilterSerializer(serializers.Serializer):
    field = serializers.CharField(required=False, allow_blank=True)
    page = serializers.IntegerField(required=False)
    sortby = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)



class LeaveRequestUpdateFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = '__all__' 


class AvailableLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableLeave
        fields = '__all__'



class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'employee_user_id', 'employee_work_info']


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'

class AvailableLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableLeave
        fields = ['leave_type_id', 'employee_id', 'available_days']


class AssignLeaveFormSerializer(serializers.Serializer):
    leave_type_id = serializers.CharField(required=False)
    employee_id = serializers.CharField(required=False)


class AvailableLeaveUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableLeave
        fields = '__all__'



class JobPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosition
        fields = '__all__'


class RestrictLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestrictLeave
        fields = '__all__'


class HolidaysSerializer(serializers.ModelSerializer):
    class Meta:
        model = Holidays
        fields = '__all__'


class LeaveAllocationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAllocationRequest
        fields = '__all__'

from django import forms

class PenaltyAccountForm(forms.ModelForm):
    class Meta:
        model = PenaltyAccounts
        fields = '__all__'


class LeaverequestcommentForm(forms.ModelForm):
    class Meta:
        model = LeaverequestComment
        fields = ['comment', 'employee_id', 'request_id']

class LeaverequestFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaverequestFile
        fields = '__all__'


class LeaverequestCommentSerializer(serializers.ModelSerializer):
    files = LeaverequestFileSerializer(many=True, read_only=True)

    class Meta:
        model = LeaverequestComment
        fields = '__all__'



class LeaveallocationrequestCommentSerializer(serializers.ModelSerializer):
    files = LeaverequestFileSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveallocationrequestComment
        fields = '__all__'


class CompensatoryLeaverequestCommentSerializer(serializers.ModelSerializer):
    files = LeaverequestFileSerializer(many=True, read_only=True)

    class Meta:
        model = CompensatoryLeaverequestComment
        fields = ['id', 'request_id', 'employee_id', 'comment', 'files', 'created_at']


class CompensatoryLeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompensatoryLeaveRequest
        fields = '__all__'



class LeaveAssignSerializer(serializers.Serializer):
    leave_type_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    employee_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )

from rest_framework import serializers

from leave.methods import calculate_requested_days, leave_requested_dates, holiday_dates_list, company_leave_dates_list
from datetime import datetime

class UserLeaveRequestSerializer(serializers.ModelSerializer):
    start_date_breakdown = serializers.CharField(required=False, allow_blank=True)
    end_date_breakdown = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "start_date",
            "end_date",
            "start_date_breakdown",
            "end_date_breakdown",
            "leave_type_id",
        ]

    def validate(self, data):
        employee = self.context["employee"]
        leave_type = data["leave_type_id"]

        # Validate dates
        start_date = data["start_date"]
        end_date = data["end_date"]
        if start_date > end_date:
            raise serializers.ValidationError("Start date cannot be after end date.")

        # Check available leave
        available_leave = AvailableLeave.objects.get(
            employee_id=employee, leave_type_id=leave_type
        )
        available_total_leave = (
            available_leave.available_days + available_leave.carryforward_days
        )

        requested_days = calculate_requested_days(
            start_date,
            end_date,
            data.get("start_date_breakdown", None),
            data.get("end_date_breakdown", None),
        )
        requested_dates = leave_requested_dates(start_date, end_date)
        holidays = holiday_dates_list()
        company_leaves = company_leave_dates_list(start_date)

        if leave_type.exclude_company_leave == "yes" and leave_type.exclude_holiday == "yes":
            total_leaves = list(set(holidays + company_leaves))
            requested_days -= sum(date in total_leaves for date in requested_dates)
        else:
            if leave_type.exclude_holiday == "yes":
                requested_days -= sum(date in holidays for date in requested_dates)
            if leave_type.exclude_company_leave == "yes":
                requested_days -= sum(date in company_leaves for date in requested_dates)

        if requested_days > available_total_leave:
            raise serializers.ValidationError("Insufficient leave days available.")

        return data

    def create(self, validated_data):
        employee = self.context["employee"]
        leave_request = LeaveRequest(**validated_data)
        leave_request.employee_id = employee
        leave_request.created_by = employee
        leave_request.save()
        return leave_request


class LeaveAllocationRequestRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


