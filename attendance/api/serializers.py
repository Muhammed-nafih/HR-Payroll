from rest_framework import serializers
from attendance.models import Attendance, AttendanceValidationCondition, AttendanceOverTime, AttendanceActivity, AttendanceLateComeEarlyOut,EmployeeShift,WorkRecords,AttendanceRequestComment,Employee,EmployeeShiftDay
from leave.models import AvailableLeave
from attendance.forms import AttendanceRequestForm

class EmployeeShiftDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShiftDay
        fields = ['day']

class AttendanceSerializer(serializers.ModelSerializer):
    attendance_day = EmployeeShiftDaySerializer()

    class Meta:
        model = Attendance
        fields = [
            'id',
            'employee_id',
            'attendance_date',
            'shift_id',
            'work_type_id',
            'attendance_clock_in_date',
            'attendance_clock_in',
            'attendance_clock_out_date',
            'attendance_clock_out',
            'attendance_worked_hour',
            'minimum_hour',
            'attendance_validated',
            'attendance_day',  # Correct field name
        ]

    def validate_attendance_date(self, value):
        return value

class AttendanceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'  



class AttendanceViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'


class AttendanceValidationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceValidationCondition
        fields = '__all__'


class AttendanceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = [
            'employee_id',
            'attendance_date',
            'shift_id',
            'work_type_id',
            'attendance_clock_in_date',
            'attendance_clock_in',
            'attendance_clock_out_date',
            'attendance_clock_out',
            'attendance_worked_hour',
            'minimum_hour',
            'attendance_validated'
        ]


class BulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(), 
        allow_empty=False
    )

class AttendanceMyviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

class AttendanceFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

class AttendanceOverTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceOverTime
        fields = '__all__'
 
class AttendanceOverTimeViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceOverTime
        fields = "__all__"

class AttendanceOverTimeSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceOverTime
        fields = "__all__"

class AttendanceOverTimeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceOverTime
        fields = '__all__'

class AttendanceActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceActivity
        fields = '__all__'  


class AttendanceActivitySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceActivity
        fields = '__all__'        

class ClockInSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    shift_id = serializers.IntegerField()
    date_today = serializers.DateField(required=True)
    day = serializers.CharField(max_length=10, required=True)
    now = serializers.TimeField(required=True)

class ClockOutSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    
    date_today = serializers.DateField()
    now = serializers.CharField()  

class AttendanceLateComeEarlyOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceLateComeEarlyOut
        fields = '__all__'

class AttendanceValidationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceValidationCondition
        fields = '__all__'

class BulkAttendanceValidateSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text="List of attendance IDs to validate."
    )

class BulkOvertimeApproveSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField())

class OnTimeAttendanceSerializer(serializers.Serializer):
    today = serializers.DateField()
    week_day = serializers.CharField(max_length=10) 
    department = serializers.IntegerField(required=False)

class LateComeAttendanceSerializer(serializers.Serializer):
    today = serializers.DateField()  
    department = serializers.IntegerField(required=False)  

class ExpectedAttendanceSerializer(serializers.Serializer):
    week_day = serializers.IntegerField() 

class EarlyOutAttendanceSerializer(serializers.Serializer):
    today = serializers.DateField()  
    department = serializers.IntegerField(required=False) 







class EmployeeShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShift
        fields = '__all__'

class BulkApproveSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False,
        error_messages={'required': 'No attendance IDs provided or IDs list is empty'}
    )



class WorkRecordsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkRecords
        fields = '__all__'




class AttendanceRequestCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRequestComment
        fields = '__all__'  # Include all fields in the AttendanceRequestComment model





class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'  # Include all fields in the Employee model


class AvailableLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableLeave
        fields = '__all__'  # Include all fields in the AvailableLeave model



class AttendanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRequestForm.Meta.model
        fields = '__all__'
