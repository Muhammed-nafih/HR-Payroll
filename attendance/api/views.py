from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from attendance.models import (Attendance,
AttendanceValidationCondition,  
AttendanceOverTime, 
AttendanceActivity, 
EmployeeShiftDay, 
Employee, 
AttendanceLateComeEarlyOut,
EmployeeShift,
WorkRecords,AttendanceRequestComment,
AttendanceRequestFile,
GraceTime,


)
from base.models import EmployeeShiftSchedule, Department
from .serializers import (
AttendanceSerializer, 
AttendanceListSerializer,
AttendanceViewSerializer, 
AttendanceUpdateSerializer, 
BulkDeleteSerializer, 
AttendanceMyviewSerializer, 
AttendanceFilterSerializer,
AttendanceOverTimeSerializer, 
AttendanceOverTimeViewSerializer,
AttendanceOverTimeSearchSerializer,
AttendanceOverTimeUpdateSerializer,
AttendanceActivitySerializer,
AttendanceActivitySearchSerializer,
ClockInSerializer,
ClockOutSerializer,
AttendanceLateComeEarlyOutSerializer,
AttendanceValidationConditionSerializer,
BulkAttendanceValidateSerializer,
BulkOvertimeApproveSerializer,
AttendanceRequestSerializer,
OnTimeAttendanceSerializer,
LateComeAttendanceSerializer,
ExpectedAttendanceSerializer,
EarlyOutAttendanceSerializer,
EmployeeShiftSerializer,
BulkApproveSerializer,
WorkRecordsSerializer,
AttendanceRequestCommentSerializer,EmployeeSerializer,AvailableLeaveSerializer,EmployeeShiftDaySerializer,
)
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator
from rest_framework.pagination import PageNumberPagination
from attendance.filters import (AttendanceFilters, 
AttendanceOverTimeFilter, 
AttendanceActivityFilter, 
LateComeEarlyOutFilter, 
LateComeEarlyOutReGroup,
AttendanceReGroup,
AttendanceOvertimeReGroup,
AttendanceActivityReGroup,
AttendanceFilters,
AttendanceRequestReGroup,
EmployeeFilter

)
from attendance.forms import AttendanceForm, AttendanceUpdateForm, AttendanceOverTimeForm, AttendanceValidationConditionForm,AttendanceRequestForm,NewRequestForm, BulkAttendanceRequestForm,AttendanceRequestCommentForm,GraceTimeForm,GraceTimeAssignForm,AttendanceActivityExportForm,LateComeEarlyOutExportForm,AttendanceOverTimeExportForm
from attendance.methods.utils import (
filtersubordinates, 
strtime_seconds, sortby, 
format_time, employee_exists, 
strtime_seconds, 
shift_schedule_today, 
clock_in_attendance_and_activity,
clock_out_attendance_and_activity,
early_out,
is_reportingmanger,
get_diff_dict,
get_employee_last_name,monthly_leave_days, get_pagination,
 get_week_start_end_dates, get_month_start_end_dates, strtime_seconds,pending_hour_data, worked_hour_data

)
import calendar
from django.shortcuts import get_object_or_404
from base.methods import choosesubordinates,closest_numbers,is_reportingmanager,filtersubordinates, get_key_instances,export_data
from django.utils.translation import gettext as _
from django.contrib import messages
from horilla.decorators import manager_can_enter
from horilla_api.api_views.attendance.permission_views import ManagerCanEnter, manager_permission_required
from rest_framework.decorators import action
from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from rest_framework.decorators import permission_classes
from django.db import IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta, date
from notifications.signals import notify
from django.urls import reverse
import contextlib
from django.db.models import Q
from attendance.views.dashboard import generate_data_set,find_on_time, find_late_come, find_early_out
import json
import copy
from django.http import JsonResponse,HttpResponse
from attendance.views.views import paginator_qry
from employee.models import EmployeeWorkInformation
from horilla import settings
from attendance.views.dashboard import total_attendance
from horilla.methods import get_horilla_model_class
from base.forms import PenaltyAccountForm
from base.models import PenaltyAccounts
from django.apps import apps
from django.db.models.query import QuerySet

from employee.authentication import JWTAuthentication

def paginator_qry(qryset, page_number):
    """
    This method is used to paginate queryset
    """
    paginator = Paginator(qryset, 50)
    qryset = paginator.get_page(page_number)
    return qryset



class AttendanceValidateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, attendance_id):
        attendance = get_object_or_404(Attendance, id=attendance_id)

        conditions = AttendanceValidationCondition.objects.all()
        # Set the default condition for 'at work' to 9:00 AM
        condition_for_at_work = strtime_seconds("09:00")
        if conditions.exists():
            condition_for_at_work = strtime_seconds(conditions[0].validation_at_work)
        at_work = strtime_seconds(attendance.attendance_worked_hour)
        
        is_valid = condition_for_at_work >= at_work

        return Response({"is_valid": is_valid}, status=status.HTTP_200_OK)





class AttendanceCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]  
    authentication_classes = [JWTAuthentication]
    def post(self, request, *args, **kwargs):
        serializer = AttendanceSerializer(data=request.data)
        if not request.user.has_perm("attendance.add_attendance"):
            return Response({"detail": "You do not have permission to add attendance."}, status=status.HTTP_403_FORBIDDEN)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class AttendancePagination(PageNumberPagination):
    page_size = 50 

class AttendanceListAPIView(APIView):
    permission_classes = [IsAuthenticated] 
    authentication_classes = [JWTAuthentication] 
    def get(self, request, *args, **kwargs):
        queryset = Attendance.objects.all()
        paginator = AttendancePagination()
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = AttendanceListSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)    
    



class AttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        previous_data = request.environ["QUERY_STRING"]
        form = AttendanceForm()
        condition = AttendanceValidationCondition.objects.first()
        minot = strtime_seconds("00:30")
        if condition is not None:
            minot = strtime_seconds(condition.minimum_overtime_to_approve)
        validate_attendances = Attendance.objects.filter(attendance_validated=False)
        attendances = Attendance.objects.filter(attendance_validated=True)
        ot_attendances = Attendance.objects.filter(
            attendance_overtime_approve=False,
            overtime_second__gte=minot,
            attendance_validated=True,
        )
        filter_obj = AttendanceFilters(queryset=Attendance.objects.all())
        attendances = filtersubordinates(request, attendances, "attendance.view_attendance")
        validate_attendances = filtersubordinates(
            request, validate_attendances, "attendance.view_attendance"
        )
        ot_attendances = filtersubordinates(
            request, ot_attendances, "attendance.view_attendance"
        )

        attendances_paginated = Paginator(attendances, 10).get_page(request.GET.get("page"))
        validate_attendances_paginated = Paginator(validate_attendances, 10).get_page(request.GET.get("vpage"))
        ot_attendances_paginated = Paginator(ot_attendances, 10).get_page(request.GET.get("opage"))

        data = {
            "form": form.as_p(),  
            "validate_attendances": AttendanceSerializer(validate_attendances_paginated, many=True).data,
            "attendances": AttendanceSerializer(attendances_paginated, many=True).data,
            "overtime_attendances": AttendanceSerializer(ot_attendances_paginated, many=True).data,
            "pd": previous_data,
            "gp_fields": AttendanceReGroup.fields, 
        }
        return Response(data, status=status.HTTP_200_OK)




class AttendanceSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        previous_data = request.query_params.urlencode()
        field = request.query_params.get("field")
        minot = strtime_seconds("00:30")
        condition = AttendanceValidationCondition.objects.first()
        if condition is not None:
            minot = strtime_seconds(condition.minimum_overtime_to_approve)

        validate_attendances = Attendance.objects.filter(attendance_validated=False)
        attendances = Attendance.objects.filter(attendance_validated=True)
        ot_attendances = Attendance.objects.filter(
            attendance_overtime_approve=False,
            overtime_second__gte=minot,
            attendance_validated=True,
        )
        validate_attendances = AttendanceFilters(request.query_params, validate_attendances).qs
        attendances = AttendanceFilters(request.query_params, attendances).qs
        ot_attendances = AttendanceFilters(request.query_params, ot_attendances).qs
        if field:
            field_copy = field.replace(".", "__")
            attendances = attendances.order_by(field_copy)
            validate_attendances = validate_attendances.order_by(field_copy)
            ot_attendances = ot_attendances.order_by(field_copy)
        attendances = filtersubordinates(request, attendances, "attendance.view_attendance")
        validate_attendances = filtersubordinates(request, validate_attendances, "attendance.view_attendance")
        ot_attendances = filtersubordinates(request, ot_attendances, "attendance.view_attendance")
        attendances = sortby(request, attendances, "sortby")
        validate_attendances = sortby(request, validate_attendances, "sortby")
        ot_attendances = sortby(request, ot_attendances, "sortby")
        response_data = {
            "validate_attendances": AttendanceViewSerializer(validate_attendances, many=True).data,
            "attendances": AttendanceViewSerializer(attendances, many=True).data,
            "ot_attendances": AttendanceViewSerializer(ot_attendances, many=True).data,
            "previous_data": previous_data,
            "field": field,
        }
        return Response(response_data, status=status.HTTP_200_OK)



class AttendanceUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id, format=None):
        attendance = get_object_or_404(Attendance, id=obj_id)
        form = AttendanceUpdateForm(request.data, instance=attendance)
        form = choosesubordinates(request, form, "attendance.change_attendance")
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance Updated."))
            return Response({"detail": _("Attendance Updated.")}, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class AttendanceDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, ManagerCanEnter]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, obj_id):
        attendance = get_object_or_404(Attendance, id=obj_id)
        month = attendance.attendance_date.strftime("%B").lower()
        overtime = attendance.employee_id.employee_overtime.filter(month=month).last()
        if overtime:
            if attendance.attendance_overtime_approve:
                total_overtime = strtime_seconds(overtime.overtime)
                attendance_overtime_seconds = strtime_seconds(attendance.attendance_overtime)
                if total_overtime > attendance_overtime_seconds:
                    total_overtime = total_overtime - attendance_overtime_seconds
                else:
                    total_overtime = attendance_overtime_seconds - total_overtime
                overtime.overtime = format_time(total_overtime)
                overtime.save()
        try:
            attendance.delete()
            return Response({"message": "Attendance deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class AttendanceBulkDeleteAPIView(APIView):
    authentication_classes = [JWTAuthentication]
   
    def post(self, request, format=None):
        serializer = BulkDeleteSerializer(data=request.data)
        if serializer.is_valid():
            ids = serializer.validated_data['ids']
            for attendance_id in ids:
                try:
                    attendance = Attendance.objects.get(id=attendance_id)
                    month = attendance.attendance_date.strftime("%B").lower()
                    overtime = attendance.employee_id.employee_overtime.filter(month=month).last()
                    if overtime is not None:
                        if attendance.attendance_overtime_approve:
                            total_overtime = strtime_seconds(overtime.overtime)
                            attendance_overtime_seconds = strtime_seconds(attendance.attendance_overtime)
                            if total_overtime > attendance_overtime_seconds:
                                total_overtime -= attendance_overtime_seconds
                            else:
                                total_overtime = attendance_overtime_seconds - total_overtime
                            overtime.overtime = format_time(total_overtime)
                            overtime.save()
                    attendance.delete()
                except Exception as error:
                    return Response({"error": str(error), "message": _("You cannot delete this attendance")}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Success"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ViewMyAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        user = request.user
        employee = user.employee_get
        employee_attendances = employee.employee_attendances.all()
        filter = AttendanceFilters(queryset=employee_attendances)
        
        attendances_paginated = paginator_qry(employee_attendances, request.GET.get("page"))

        data = {
            "attendances": AttendanceSerializer(attendances_paginated, many=True).data,
            "f": str(filter.form.as_p()),  # Serialize the filter form to HTML
        }
        return Response(data, status=status.HTTP_200_OK)



class FilterOwnAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        user = request.user
        employee = user.employee_get
        attendances = Attendance.objects.filter(employee_id=employee)
        attendances = AttendanceFilters(request.GET, queryset=attendances).qs
        
        attendances_paginated = paginator_qry(attendances, request.GET.get("page"))
        
        data = {
            "attendances": AttendanceSerializer(attendances_paginated, many=True).data,
        }
        return Response(data, status=status.HTTP_200_OK)





class AttendanceOvertimeCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, format=None):
        form = AttendanceOverTimeForm(request.data)
        form = choosesubordinates(request, form, "attendance.add_attendanceovertime")
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance account added."))
            return Response({"detail": _("Attendance account added.")}, status=status.HTTP_201_CREATED)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class AttendanceOvertimeViewAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        previous_data = request.environ["QUERY_STRING"]
        accounts = AttendanceOverTime.objects.all()
        accounts = filtersubordinates(request, accounts, "attendance.view_attendanceovertime")
        form = AttendanceOverTimeForm()
        form = choosesubordinates(request, form, "attendance.add_attendanceovertime")
        filter_obj = AttendanceOverTimeFilter()
        
        accounts_paginated = Paginator(accounts, 10).get_page(request.GET.get("page"))

        data = {
            "accounts": AttendanceOverTimeSerializer(accounts_paginated, many=True).data,
            "form": form.as_p(),  
            "pd": previous_data,
            "f": filter_obj.form.as_p(),  
            "gp_fields": AttendanceOvertimeReGroup.fields,  
        }
        return Response(data, status=status.HTTP_200_OK)



class AttendanceOvertimeSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        field = request.GET.get("field")
        previous_data = request.environ["QUERY_STRING"]

        accounts = AttendanceOverTimeFilter(request.GET).qs
        form = AttendanceOverTimeForm()
        template = "attendance/attendance_account/overtime_list.html"
        if field:
            field_copy = field.replace(".", "__")
            accounts = accounts.order_by(field_copy)
            template = "attendance/attendance_account/group_by.html"
        accounts = sortby(request, accounts, "sortby")
        accounts = filtersubordinates(
            request, accounts, "attendance.view_attendanceovertime"
        )
        
        accounts_paginated = Paginator(accounts, 10).get_page(request.GET.get("page"))

        data = {
            "accounts": AttendanceOverTimeSerializer(accounts_paginated, many=True).data,
            "form": form.as_p(), 
            "pd": previous_data,
            "field": field,
        }
        return Response(data, status=status.HTTP_200_OK)




class AttendanceOverTimeUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id, format=None):
        overtime = get_object_or_404(AttendanceOverTime, id=obj_id)
        form = AttendanceOverTimeForm(request.data, instance=overtime)
        form = choosesubordinates(request, form, "attendance.change_attendanceovertime")
        if form.is_valid():
            form.save()
            messages.success(request, _("Attendance account updated successfully."))
            return Response({"detail": _("Attendance account updated successfully.")}, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class AttendanceOverTimeDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, ManagerCanEnter]
    authentication_classes = [JWTAuthentication]

    
    def delete(self, request, obj_id, format=None):
        try:
            overtime = AttendanceOverTime.objects.get(id=obj_id)
            overtime.delete()
            return Response({"message": "Attendance overtime deleted successfully."},status=status.HTTP_200_OK,)
        except AttendanceOverTime.DoesNotExist:
            return Response({"error": "AttendanceOverTime record not found."},status=status.HTTP_404_NOT_FOUND,)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"},status=status.HTTP_400_BAD_REQUEST,)
            



class AttendanceActivityListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        previous_data = request.environ["QUERY_STRING"]
        attendance_activities = AttendanceActivity.objects.all()
        filter_obj = AttendanceActivityFilter()
        
        attendance_activities_paginated = Paginator(attendance_activities, 10).get_page(request.GET.get("page"))

        data = {
            "data": AttendanceActivitySerializer(attendance_activities_paginated, many=True).data,
            "pd": previous_data,
            "f": filter_obj.form.as_p(), 
            "gp_fields": AttendanceActivityReGroup.fields, 
        }
        return Response(data, status=status.HTTP_200_OK)

    

class AttendanceActivitySearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, format=None):
        previous_data = request.environ["QUERY_STRING"]
        field = request.GET.get("field")
        attendance_activities = AttendanceActivityFilter(request.GET).qs
        if field and field != "":
            field_copy = field.replace(".", "__")
            attendance_activities = attendance_activities.order_by(field_copy)
        
        attendance_activities = filtersubordinates(request, attendance_activities, "attendance.view_attendanceactivity")
        attendance_activities = sortby(request, attendance_activities, "orderby")
        paginator = Paginator(attendance_activities, 10)
        page = request.GET.get("page")
        attendance_activities_paginated = paginator.get_page(page)

        data = {
            "data": AttendanceActivitySerializer(attendance_activities_paginated, many=True).data,
            "pd": previous_data,
            "field": field,
        }
        return Response(data, status=status.HTTP_200_OK)


class AttendanceActivityDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, obj_id):
        try:
            attendance_activity = get_object_or_404(AttendanceActivity, id=obj_id)
            attendance_activity.delete()
            return Response({"detail": _("Attendance activity deleted")}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"detail": str(e), "error": _("You cannot delete this activity")},
                status=status.HTTP_400_BAD_REQUEST
            )





class ActivitySingleView(APIView):
    """
    API view to render a single attendance activity.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, obj_id):
        """
        Handles GET requests to render a single attendance activity.
        """
        try:
            request_copy = request.GET.copy()
            request_copy.pop("instances_ids", None)
            previous_data = request_copy.urlencode()
            activity = get_object_or_404(AttendanceActivity, id=obj_id)

            instance_ids_json = request.GET.get("instances_ids")
            instance_ids = json.loads(instance_ids_json) if instance_ids_json else []
            previous_instance, next_instance = closest_numbers(instance_ids, obj_id)
            context = {
                "pd": previous_data,
                "activity": {
                    "id": activity.id,
                    "title": activity.title,
                    "date": activity.attendance_date,
                    "description": activity.description,
                    # Add other necessary fields
                },
                "previous_instance": previous_instance,
                "next_instance": next_instance,
                "instance_ids_json": instance_ids_json,
            }

            if activity:
                attendance = Attendance.objects.filter(attendance_date=activity.attendance_date).first()
                if attendance:
                    context["attendance"] = {
                        "id": attendance.id,
                        "date": attendance.attendance_date,
                        "status": attendance.status,
                        # Add other necessary fields
                    }

            return Response(context, status=200)
        except AttendanceActivity.DoesNotExist:
            return Response({"error": "Attendance activity not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class AttendanceActivityBulkDeleteView(APIView):
    """
    API view to delete bulk of attendances.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request):
        """
        Handles DELETE requests to delete bulk of attendances.
        """
        try:
            ids = json.loads(request.POST.get("ids", "[]"))
            if not ids:
                return JsonResponse({"error": "No valid attendance IDs provided."}, status=400)

            activities_deleted = 0
            for attendance_id in ids:
                try:
                    activity = AttendanceActivity.objects.get(id=attendance_id)
                    activity.delete()
                    activities_deleted += 1
                    messages.success(
                        request,
                        _("{employee} activity deleted.").format(employee=activity.employee_id),
                    )
                except AttendanceActivity.DoesNotExist:
                    messages.error(request, _("Attendance activity not found."))
                except (OverflowError, ValueError):
                    messages.error(request, _("Invalid attendance ID."))

            if activities_deleted > 0:
                return JsonResponse({"message": "Success"}, status=200)
            else:
                return JsonResponse({"message": "No attendance activities were deleted."}, status=200)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)

class ClockInAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request, *args, **kwargs):
        serializer = ClockInSerializer(data=request.data)
        if serializer.is_valid():
         
            date_today = serializer.validated_data['date_today']
            day = serializer.validated_data['day']
            now = serializer.validated_data['now']

           
            employee, work_info = employee_exists(request)
            if employee and work_info is not None:
                shift = work_info.shift_id
                attendance_date = date_today
               
                day = EmployeeShiftDay.objects.get(day=day)
              
                now_sec = strtime_seconds(now)
                mid_day_sec = strtime_seconds("12:00")
                minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                    day=day, shift=shift
                )

                if start_time_sec > end_time_sec:
                  
                    if mid_day_sec > now_sec:
                       
                        date_yesterday = date_today - timedelta(days=1)
                        day_yesterday = date_yesterday.strftime("%A").lower()
                        day_yesterday = EmployeeShiftDay.objects.get(day=day_yesterday)
                        minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                            day=day_yesterday, shift=shift
                        )
                        attendance_date = date_yesterday
                        day = day_yesterday

                
                clock_in_attendance_and_activity(
                    employee=employee,
                    date_today=date_today,
                    attendance_date=attendance_date,
                    day=day,
                    now=now,
                    shift=shift,
                    minimum_hour=minimum_hour,
                    start_time=start_time_sec,
                    end_time=end_time_sec,
                )
                return Response({
                    "message": "Clock-in successful",
                    "check_out_button": """
                        <button class="oh-btn oh-btn--warning-outline"
                          hx-get="/attendance/clock-out"
                          hx-target='#attendance-activity-container'
                          hx-swap='innerHTML'>
                          <ion-icon class="oh-navbar__clock-icon mr-2 text-warning" name="exit-outline"></ion-icon>
                          <span class="hr-check-in-out-text">Check-Out</span>
                        </button>
                    """
                }, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Employee or work information not found."}, status=status.HTTP_400_BAD_REQUEST)

       
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClockOutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, format=None):
        employee = get_object_or_404(Employee, id=request.data.get('employee_id'))
        date_today = date.today()
        now = datetime.now().strftime("%H:%M")

        clock_out_attendance_and_activity(employee=employee, date_today=date_today, now=now)

        attendance = Attendance.objects.filter(employee_id=employee).order_by(
            "-attendance_date", "-id"
        ).first()
        serializer = AttendanceSerializer(attendance)
        
        check_in_html = """
              <button class="oh-btn oh-btn--success-outline "
              hx-get="/attendance/clock-in"
              hx-target='#attendance-activity-container'
              hx-swap='innerHTML'>
              <ion-icon class="oh-navbar__clock-icon mr-2 text-success"
              name="enter-outline"></ion-icon>
               <span class="hr-check-in-out-text">{check_in}</span>
              </button>
            """.format(
            check_in=_("Check-In")
        )

        response_data = {
            "attendance": serializer.data,
            "html": check_in_html
        }
        return Response(response_data, status=status.HTTP_200_OK)






class LateComeEarlyOutBulkDeleteView(APIView):
    """
    API view to delete bulk of 'late come/early out' attendances.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request):
        """
        Handles DELETE requests to delete bulk of 'late come/early out' attendances.
        """
        try:
            ids = json.loads(request.POST.get("ids", "[]"))
            if not ids:
                return JsonResponse({"error": "No valid attendance IDs provided."}, status=400)

            activities_deleted = 0
            for attendance_id in ids:
                try:
                    late_come = AttendanceLateComeEarlyOut.objects.get(id=attendance_id)
                    late_come.delete()
                    activities_deleted += 1
                    messages.success(
                        request,
                        _("{employee} Late-in early-out deleted.").format(
                            employee=late_come.employee_id
                        ),
                    )
                except AttendanceLateComeEarlyOut.DoesNotExist:
                    messages.error(request, _("Attendance not found."))
                except (OverflowError, ValueError):
                    messages.error(request, _("Invalid attendance ID."))

            if activities_deleted > 0:
                return JsonResponse({"message": "Success"}, status=200)
            else:
                return JsonResponse({"message": "No attendance activities were deleted."}, status=200)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)







class LateInEarlyOutSingleView(APIView):
    """
    API view to render a single 'late in/early out' attendance activity.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, obj_id):
        """
        Handles GET requests to render a single 'late in/early out' attendance activity.
        """
        try:
            request_copy = request.GET.copy()
            request_copy.pop("instances_ids", None)
            previous_data = request_copy.urlencode()

            late_in_early_out = get_object_or_404(AttendanceLateComeEarlyOut, id=obj_id)

            instance_ids_json = request.GET.get("instances_ids")
            instance_ids = json.loads(instance_ids_json) if instance_ids_json else []
            previous_instance, next_instance = closest_numbers(instance_ids, obj_id)

            context = {
                "late_in_early_out": {
                    "id": late_in_early_out.id,
                    "title": late_in_early_out.title,
                    "date": late_in_early_out.date,
                    "description": late_in_early_out.description,
                    # Add other necessary fields
                },
                "previous_instance": previous_instance,
                "next_instance": next_instance,
                "instance_ids_json": instance_ids_json,
                "pd": previous_data,
            }

            return Response(context, status=200)
        except AttendanceLateComeEarlyOut.DoesNotExist:
            return Response({"error": "Attendance activity not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)







class LateComeEarlyOutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
   
    def get(self, request, format=None):
        reports = AttendanceLateComeEarlyOut.objects.all()
        reports = filtersubordinates(
            request, reports, "attendance.view_attendancelatecomeearlyout"
        )
        filter_obj = LateComeEarlyOutFilter(request.GET, queryset=reports)
        
        paginator = Paginator(filter_obj.qs, 10)  
        page = request.GET.get('page')
        paginated_reports = paginator.get_page(page)

        serializer = AttendanceLateComeEarlyOutSerializer(paginated_reports, many=True)
        response_data = {
            "data": serializer.data,
            "filter": LateComeEarlyOutFilter().data,
            "gp_fields": LateComeEarlyOutReGroup.fields,
        }
        return Response(response_data, status=status.HTTP_200_OK)
    


class LateComeEarlyOutSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
   
    def get(self, request, format=None):
        field = request.GET.get("field")
        previous_data = request.environ["QUERY_STRING"]

        reports = LateComeEarlyOutFilter(request.GET).qs
        if field:
            field_copy = field.replace(".", "__")
            reports = reports.order_by(field_copy)

        reports = filtersubordinates(request, reports, "attendance.view_attendancelatecomeearlyout")
        reports = sortby(request, reports, "sortby")

        paginator = Paginator(reports, 10) 
        page = request.GET.get('page')
        paginated_reports = paginator.get_page(page)

        serializer = AttendanceLateComeEarlyOutSerializer(paginated_reports, many=True)
        response_data = {
            "data": serializer.data,
            "pd": previous_data,
            "field": field,
        }
        return Response(response_data, status=status.HTTP_200_OK)



class LateComeEarlyOutDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def delete(self, request, obj_id, format=None):
        try:
            late_come_early_out_instance = get_object_or_404(AttendanceLateComeEarlyOut, id=obj_id)
            late_come_early_out_instance.delete()
            return Response({"success": "Late-in early-out deleted"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ValidationConditionCreateAPIView(APIView):
   
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request, format=None):
        condition = AttendanceValidationCondition.objects.first()
        if condition:
            serializer = AttendanceValidationConditionSerializer(condition, data=request.data, partial=True)
        else:
            serializer = AttendanceValidationConditionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
  


class ValidationConditionUpdateAPIView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id, format=None):
        condition = get_object_or_404(AttendanceValidationCondition, id=obj_id)
        serializer = AttendanceValidationConditionSerializer(condition, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, obj_id, format=None):
        condition = get_object_or_404(AttendanceValidationCondition, id=obj_id)
        serializer = AttendanceValidationConditionSerializer(condition)
        return Response(serializer.data, status=status.HTTP_200_OK)



class ValidationConditionDeleteAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def delete(self, request, obj_id, format=None):
        try:
            condition = get_object_or_404(AttendanceValidationCondition, id=obj_id)
            condition.delete()
            return Response({"success": "Validation condition deleted."}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

  
class ValidateBulkAttendanceAPI(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = BulkAttendanceValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ids = serializer.validated_data['ids']
        validated_attendances = []
        for attendance_id in ids:
            attendance = get_object_or_404(Attendance, id=attendance_id)
            attendance.attendance_validated = True
            attendance.save()
            validated_attendances.append(attendance.employee_id.employee_user_id.username)  
            
            notify.send(
                request.user.employee_get,
                recipient=attendance.employee_id.employee_user_id,
                verb=f"Your attendance for the date {attendance.attendance_date} is validated",
                verb_ar=f"تم التحقق من حضورك في تاريخ {attendance.attendance_date}",
                verb_de=f"Ihre Anwesenheit für das Datum {attendance.attendance_date} wurde bestätigt",
                verb_es=f"Se ha validado su asistencia para la fecha {attendance.attendance_date}",
                verb_fr=f"Votre présence pour la date {attendance.attendance_date} est validée",
                redirect=reverse("view-my-attendance"),
                icon="checkmark",
            )
        return Response(
            {"message": "Attendance validated successfully.", "validated_attendances": validated_attendances},
            status=status.HTTP_200_OK
        )
    

class ValidateAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id):
        attendance = get_object_or_404(Attendance, id=obj_id)
 
        if is_reportingmanger(request, attendance) or request.user.has_perm("attendance.change_attendance"):
            attendance.attendance_validated = True
            attendance.save()
            messages.success(request, _("Attendance validated."))
            notify.send(
                request.user.employee_get,
                recipient=attendance.employee_id.employee_user_id,
                verb=f"Your attendance for the date {attendance.attendance_date} is validated",
                verb_ar=f"تم تحقيق حضورك في تاريخ {attendance.attendance_date}",
                verb_de=f"Deine Anwesenheit für das Datum {attendance.attendance_date} ist bestätigt.",
                verb_es=f"Se valida tu asistencia para la fecha {attendance.attendance_date}.",
                verb_fr=f"Votre présence pour la date {attendance.attendance_date} est validée.",
                redirect=reverse("view-my-attendance"),
                icon="checkmark",
            )
            return Response({"message": "Attendance validated successfully."}, status=200)
        return Response({"error": "You don't have permission to validate this attendance."}, status=403)
    

class RevalidateAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id):
  
        attendance = get_object_or_404(Attendance, id=obj_id)
        if is_reportingmanger(request, attendance) or request.user.has_perm("attendance.change_attendance"):
            attendance.attendance_validated = False
            attendance.save()
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb=f"{attendance.employee_id} requested revalidation for {attendance.attendance_date} attendance",
                    verb_ar=f"{attendance.employee_id} طلب إعادة التحقق من حضور تاريخ {attendance.attendance_date}",
                    verb_de=f"{attendance.employee_id} beantragte eine Neubewertung der Teilnahme am {attendance.attendance_date}",
                    verb_es=f"{attendance.employee_id} solicitó la validación nuevamente para la asistencia del {attendance.attendance_date}",
                    verb_fr=f"{attendance.employee_id} a demandé une revalidation pour la présence du {attendance.attendance_date}",
                    redirect=reverse("view-my-attendance"),
                    icon="refresh",
                )
            return Response(
                {"message": "Revalidation requested successfully."},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "You cannot request revalidation for others' attendance."},
            status=status.HTTP_403_FORBIDDEN
        )    
    

class ApproveOvertimeAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id):
       
        attendance = get_object_or_404(Attendance, id=obj_id)
        if request.user.has_perm("attendance.change_attendance"):
            attendance.attendance_overtime_approve = True
            attendance.save()

            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=attendance.employee_id.employee_user_id,
                    verb=f"Your {attendance.attendance_date}'s attendance overtime approved.",
                    verb_ar=f"تمت الموافقة على إضافة ساعات العمل الإضافية لتاريخ {attendance.attendance_date}.",
                    verb_de=f"Die Überstunden für den {attendance.attendance_date} wurden genehmigt.",
                    verb_es=f"Se ha aprobado el tiempo extra de asistencia para el {attendance.attendance_date}.",
                    verb_fr=f"Les heures supplémentaires pour la date {attendance.attendance_date} ont été approuvées.",
                    redirect=reverse("attendance-overtime-view"),
                    icon="checkmark",
                )

            return Response(
                {"message": "Overtime approved successfully."},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "You do not have permission to approve overtime."},
            status=status.HTTP_403_FORBIDDEN
        )
    


class ApproveBulkOvertimeAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        serializer = BulkOvertimeApproveSerializer(data=request.data)
        if serializer.is_valid():
            ids = serializer.validated_data["ids"]
            for attendance_id in ids:
                attendance = get_object_or_404(Attendance, id=attendance_id)
                attendance.attendance_overtime_approve = True
                attendance.save()
                notify.send(
                    request.user.employee_get,
                    recipient=attendance.employee_id.employee_user_id,
                    verb=f"Overtime approved for {attendance.attendance_date}'s attendance",
                    verb_ar=f"تمت الموافقة على العمل الإضافي لحضور تاريخ {attendance.attendance_date}",
                    verb_de=f"Überstunden für die Anwesenheit am {attendance.attendance_date} genehmigt",
                    verb_es=f"Horas extra aprobadas para la asistencia del {attendance.attendance_date}",
                    verb_fr=f"Heures supplémentaires approuvées pour la présence du {attendance.attendance_date}",
                    redirect=reverse("attendance-overtime-view"),
                    icon="checkmark",
                )
            return Response(
                {"message": "Overtime approved for all selected attendances."},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "Invalid data provided."},
            status=status.HTTP_400_BAD_REQUEST
        )


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication] 
    def get(self, request):
        
        employees = Employee.objects.filter(is_active=True).filter(~Q(employee_work_info__shift_id=None))
        total_employees = len(employees)
        today = datetime.today()
        week_day = today.strftime("%A").lower()
        on_time = self.find_on_time(request, today=today, week_day=week_day)
        late_come_obj = self.find_late_come(today=today)
        marked_attendances = late_come_obj + on_time
        expected_attendances = self.find_expected_attendances(week_day=week_day)
        on_time_ratio = 0
        late_come_ratio = 0
        marked_attendances_ratio = 0
        if expected_attendances != 0:
            on_time_ratio = f"{(on_time / expected_attendances) * 100:.1f}"
            late_come_ratio = f"{(late_come_obj / expected_attendances) * 100:.1f}"
            marked_attendances_ratio = f"{(marked_attendances / expected_attendances) * 100:.1f}"

        early_outs = AttendanceLateComeEarlyOut.objects.filter(
            type="early_out", attendance_id__attendance_date=today
        )
        on_break = len(early_outs)
        data = {
            "total_employees": total_employees,
            "on_time": on_time,
            "on_time_ratio": on_time_ratio,
            "late_come": late_come_obj,
            "late_come_ratio": late_come_ratio,
            "expected_attendances": expected_attendances,
            "marked_attendances": marked_attendances,
            "marked_attendances_ratio": marked_attendances_ratio,
            "on_break": on_break,
        }

        return Response(data)
    def find_on_time(self, request, today, week_day):
        on_time = 0
        attendances = Attendance.objects.filter(attendance_date=today)
        attendances = self.filtersubordinates(request, attendances, "attendance.view_attendance")
        schedules_today = attendances.first().shift_id.employeeshiftschedule_set.filter(day__day=week_day) if attendances.first() else None
        if schedules_today:
            for attendance in attendances:
                late_come_obj = attendance.late_come_early_out.filter(type="late_come").first()
                if late_come_obj is None:
                    on_time += 1
        return on_time

    def find_late_come(self, today):
        late_come_obj = AttendanceLateComeEarlyOut.objects.filter(
            type="late_come", attendance_id__attendance_date=today
        )
        return len(late_come_obj)

    def find_expected_attendances(self, week_day):
        schedules_today = EmployeeShiftSchedule.objects.filter(day__day=week_day)
        expected_attendances = 0
        for schedule in schedules_today:
            shift = schedule.shift_id
            expected_attendances += len(shift.employeeworkinformation_set.all())
        return expected_attendances

    def filtersubordinates(self, request, attendances, permission):
        if not request.user.has_perm(permission):
            return attendances.none()  
        return attendances

class DashboardAttendanceAPIView(APIView):
    authentication_classes = [JWTAuthentication]

    def generate_data_set(self, dept):
        today = datetime.today()
        week_day = today.strftime("%A").lower()

        start_date = today
        end_date = today

        on_time = find_on_time(self.request, today=today, week_day=week_day, department=dept)
        late_come_obj = find_late_come(start_date=start_date, end_date=end_date, department=dept)
        early_out_obj = find_early_out(start_date=start_date, end_date=end_date, department=dept)

        data = {
            "label": dept.department,
            "data": [on_time, len(late_come_obj), len(early_out_obj)],  
        }
        return data

    def get(self, request):
        labels = [
            "On Time",
            "Late Come",
            "On Break",
        ]
        data_set = []
        departments = Department.objects.all()  
        for dept in departments:
            data_set.append(self.generate_data_set(dept))
        return JsonResponse({"dataSet": data_set, "labels": labels}, status=status.HTTP_200_OK)





class ValidateAttendanceRequestAPI(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API to validate the requested attendance.
    """

    def get(self, request, attendance_id, *args, **kwargs):
        try:
            # Fetch the attendance record
            attendance = Attendance.objects.get(id=attendance_id)
            first_dict = attendance.serialize()
            
            # Define the empty data structure
            empty_data = {
                str(key): None for key in [
                    _("employee_id"),
                    _("attendance_date"),
                    _("attendance_clock_in_date"),
                    _("attendance_clock_in"),
                    _("attendance_clock_out"),
                    _("attendance_clock_out_date"),
                    _("shift_id"),
                    _("work_type_id"),
                    _("attendance_worked_hour"),
                    _("minimum_hour"),
                ]
            }
            
            # Determine the data to compare
            if attendance.request_type == "create_request":
                other_dict = first_dict
                first_dict = empty_data
            else:
                other_dict = json.loads(attendance.requested_data)
            
            # Handle navigation for requests
            requests_ids_json = request.query_params.get("requests_ids")
            previous_instance_id = next_instance_id = attendance.pk
            if requests_ids_json:
                requests_ids = json.loads(requests_ids_json)
                previous_instance_id, next_instance_id = closest_numbers(requests_ids, attendance_id)
            
            # Compute the difference and ensure keys are strings
            diff_data = {
                str(k): v for k, v in get_diff_dict(first_dict, other_dict, Attendance).items()
            }
            response_data = {
                "data": diff_data,
                "attendance": attendance.serialize(),  # Assuming `serialize` returns serialized data
                "previous": previous_instance_id,
                "next": next_instance_id,
                "requests_ids": requests_ids_json,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)

        except Attendance.DoesNotExist:
            return Response(
                {"error": "Attendance record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ApproveValidateAttendanceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, attendance_id):
        from attendance.views.clock_in_out import late_come,early_out
        try:
            attendance = get_object_or_404(Attendance, id=attendance_id)
            prev_attendance_date = attendance.attendance_date
            prev_attendance_clock_in_date = attendance.attendance_clock_in_date
            prev_attendance_clock_in = attendance.attendance_clock_in
            
            attendance.attendance_validated = True
            attendance.is_validate_request_approved = True
            attendance.is_validate_request = False
            attendance.request_description = None
            attendance.save()

            if attendance.requested_data is not None:
                requested_data = json.loads(attendance.requested_data)
                requested_data["attendance_clock_out"] = (
                    None if requested_data["attendance_clock_out"] == "None" else requested_data["attendance_clock_out"]
                )
                requested_data["attendance_clock_out_date"] = (
                    None if requested_data["attendance_clock_out_date"] == "None" else requested_data["attendance_clock_out_date"]
                )
                Attendance.objects.filter(id=attendance_id).update(**requested_data)

                # Save the instance once more to affect the overtime calculation
                attendance = Attendance.objects.get(id=attendance_id)
                attendance.save()

            if (
                attendance.attendance_clock_out is None
                or attendance.attendance_clock_out_date is None
            ):
                attendance.attendance_validated = True
                activity = AttendanceActivity.objects.filter(
                    employee_id=attendance.employee_id,
                    attendance_date=prev_attendance_date,
                    clock_in_date=prev_attendance_clock_in_date,
                    clock_in=prev_attendance_clock_in,
                )
                if activity:
                    activity.update(
                        employee_id=attendance.employee_id,
                        attendance_date=attendance.attendance_date,
                        clock_in_date=attendance.attendance_clock_in_date,
                        clock_in=attendance.attendance_clock_in,
                    )
                else:
                    AttendanceActivity.objects.create(
                        employee_id=attendance.employee_id,
                        attendance_date=attendance.attendance_date,
                        clock_in_date=attendance.attendance_clock_in_date,
                        clock_in=attendance.attendance_clock_in,
                    )

            # Create late come or early out objects
            shift = attendance.shift_id
            day = attendance.attendance_date.strftime("%A").lower()
            day = EmployeeShiftDay.objects.get(day=day)

            minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                day=day, shift=shift
            )
            if attendance.attendance_clock_in:
                late_come(
                    attendance, start_time=start_time_sec, end_time=end_time_sec, shift=shift
                )
            if attendance.attendance_clock_out:
                early_out(
                    attendance, start_time=start_time_sec, end_time=end_time_sec, shift=shift
                )

            messages.success(request, _("Attendance request has been approved"))
            employee = attendance.employee_id
            notify.send(
                request.user,
                recipient=employee.employee_user_id,
                verb=f"Your attendance request for {attendance.attendance_date} is validated",
                verb_ar=f"تم التحقق من طلب حضورك في تاريخ {attendance.attendance_date}",
                verb_de=f"Ihr Anwesenheitsantrag für das Datum {attendance.attendance_date} wurde bestätigt",
                verb_es=f"Se ha validado su solicitud de asistencia para la fecha {attendance.attendance_date}",
                verb_fr=f"Votre demande de présence pour la date {attendance.attendance_date} est validée",
                redirect=reverse("request-attendance-view") + f"?id={attendance.id}",
                icon="checkmark-circle-outline",
            )
            if attendance.employee_id.employee_work_info.reporting_manager_id:
                reporting_manager = (
                    attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                )
                user_last_name = get_employee_last_name(attendance)
                notify.send(
                    request.user,
                    recipient=reporting_manager,
                    verb=f"{employee.employee_first_name} {user_last_name}'s attendance request for {attendance.attendance_date} is validated",
                    verb_ar=f"تم التحقق من طلب الحضور لـ {employee.employee_first_name} {user_last_name} في {attendance.attendance_date}",
                    verb_de=f"Die Anwesenheitsanfrage von {employee.employee_first_name} {user_last_name} für den {attendance.attendance_date} wurde validiert",
                    verb_es=f"Se ha validado la solicitud de asistencia de {employee.employee_first_name} {user_last_name} para el {attendance.attendance_date}",
                    verb_fr=f"La demande de présence de {employee.employee_first_name} {user_last_name} pour le {attendance.attendance_date} a été validée",
                    redirect=reverse("request-attendance-view") + f"?id={attendance.id}",
                    icon="checkmark-circle-outline",
                )

            return Response({"message": "Attendance request has been approved"}, status=status.HTTP_200_OK)

        except Attendance.DoesNotExist:
            return Response({"detail": "Attendance not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CancelAttendanceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, attendance_id):
        try:
            attendance = get_object_or_404(Attendance, id=attendance_id)
            if (
                attendance.employee_id.employee_user_id == request.user
                or is_reportingmanager(request)
                or request.user.has_perm("attendance.change_attendance")
            ):
                attendance.is_validate_request_approved = False
                attendance.is_validate_request = False
                attendance.request_description = None
                attendance.requested_data = None
                attendance.request_type = None

                attendance.save()
                if attendance.request_type == "create_request":
                    attendance.delete()
                    messages.success(request, _("The requested attendance is removed."))
                else:
                    messages.success(request, _("Attendance request has been rejected"))
                
                employee = attendance.employee_id
                notify.send(
                    request.user,
                    recipient=employee.employee_user_id,
                    verb=f"Your attendance request for {attendance.attendance_date} is rejected",
                    verb_ar=f"تم رفض طلبك للحضور في تاريخ {attendance.attendance_date}",
                    verb_de=f"Ihre Anwesenheitsanfrage für {attendance.attendance_date} wurde abgelehnt",
                    verb_es=f"Tu solicitud de asistencia para el {attendance.attendance_date} ha sido rechazada",
                    verb_fr=f"Votre demande de présence pour le {attendance.attendance_date} est rejetée",
                    icon="close-circle-outline",
                )
            else:
                return Response({"detail": "You do not have permission to cancel this attendance request."}, status=status.HTTP_403_FORBIDDEN)
        
        except Attendance.DoesNotExist:
            return Response({"detail": "Attendance request not found"}, status=status.HTTP_404_NOT_FOUND)
        except OverflowError:
            return Response({"detail": "An overflow error occurred"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Attendance request has been canceled"}, status=status.HTTP_200_OK)

class BulkApproveAttendanceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    

    def post(self, request, format=None):
        from attendance.views.clock_in_out import late_come,early_out
        serializer = BulkApproveSerializer(data=request.data)
        
        if serializer.is_valid():
            ids = serializer.validated_data.get('ids', [])
            if not ids:
                return Response({"detail": "No attendance IDs provided or IDs list is empty"}, status=status.HTTP_400_BAD_REQUEST)
            
            for attendance_id in ids:
                try:
                    # Retrieve the attendance entry
                    attendance = Attendance.objects.get(id=attendance_id)
                    prev_attendance_date = attendance.attendance_date
                    prev_attendance_clock_in_date = attendance.attendance_clock_in_date
                    prev_attendance_clock_in = attendance.attendance_clock_in
                    
                    # Mark as validated and approved
                    attendance.attendance_validated = True
                    attendance.is_validate_request_approved = True
                    attendance.is_validate_request = False
                    attendance.request_description = None
                    attendance.save()

                    # If the attendance has requested data, update it
                    if attendance.requested_data is not None:
                        requested_data = json.loads(attendance.requested_data)
                        requested_data["attendance_clock_out"] = (
                            None if requested_data["attendance_clock_out"] == "None" else requested_data["attendance_clock_out"]
                        )
                        requested_data["attendance_clock_out_date"] = (
                            None if requested_data["attendance_clock_out_date"] == "None" else requested_data["attendance_clock_out_date"]
                        )
                        Attendance.objects.filter(id=attendance_id).update(**requested_data)

                        # Re-save the attendance instance to affect overtime calculation
                        attendance = Attendance.objects.get(id=attendance_id)
                        attendance.save()

                    # Update or create AttendanceActivity if clock out data is None
                    if (
                        attendance.attendance_clock_out is None
                        or attendance.attendance_clock_out_date is None
                    ):
                        attendance.attendance_validated = True
                        activity = AttendanceActivity.objects.filter(
                            employee_id=attendance.employee_id,
                            attendance_date=prev_attendance_date,
                            clock_in_date=prev_attendance_clock_in_date,
                            clock_in=prev_attendance_clock_in,
                        )
                        if activity:
                            activity.update(
                                employee_id=attendance.employee_id,
                                attendance_date=attendance.attendance_date,
                                clock_in_date=attendance.attendance_clock_in_date,
                                clock_in=attendance.attendance_clock_in,
                            )
                        else:
                            AttendanceActivity.objects.create(
                                employee_id=attendance.employee_id,
                                attendance_date=attendance.attendance_date,
                                clock_in_date=attendance.attendance_clock_in_date,
                                clock_in=attendance.attendance_clock_in,
                            )

                    # Handle late comes or early outs
                    shift = attendance.shift_id
                    day = attendance.attendance_date.strftime("%A").lower()
                    day = EmployeeShiftDay.objects.get(day=day)

                    minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                        day=day, shift=shift
                    )
                    if attendance.attendance_clock_in:
                        late_come(
                            attendance,
                            start_time=start_time_sec,
                            end_time=end_time_sec,
                            shift=shift,
                        )
                    if attendance.attendance_clock_out:
                        early_out(
                            attendance,
                            start_time=start_time_sec,
                            end_time=end_time_sec,
                            shift=shift,
                        )

                    # Send notifications to employee and reporting manager
                    employee = attendance.employee_id
                    notify.send(
                        request.user,
                        recipient=employee.employee_user_id,
                        verb=f"Your attendance request for {attendance.attendance_date} is validated",
                        verb_ar=f"تم التحقق من طلب حضورك في تاريخ {attendance.attendance_date}",
                        verb_de=f"Ihr Anwesenheitsantrag für das Datum {attendance.attendance_date} wurde bestätigt",
                        verb_es=f"Se ha validado su solicitud de asistencia para la fecha {attendance.attendance_date}",
                        verb_fr=f"Votre demande de présence pour la date {attendance.attendance_date} est validée",
                        redirect=reverse("request-attendance-view") + f"?id={attendance.id}",
                        icon="checkmark-circle-outline",
                    )
                    if attendance.employee_id.employee_work_info.reporting_manager_id:
                        reporting_manager = (
                            attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                        )
                        user_last_name = get_employee_last_name(attendance)
                        notify.send(
                            request.user,
                            recipient=reporting_manager,
                            verb=f"{employee.employee_first_name} {user_last_name}'s attendance request for {attendance.attendance_date} is validated",
                            verb_ar=f"تم التحقق من طلب الحضور لـ {employee.employee_first_name} {user_last_name} في {attendance.attendance_date}",
                            verb_de=f"Die Anwesenheitsanfrage von {employee.employee_first_name} {user_last_name} für den {attendance.attendance_date} wurde validiert",
                            verb_es=f"Se ha validado la solicitud de asistencia de {employee.employee_first_name} {user_last_name} para el {attendance.attendance_date}",
                            verb_fr=f"La demande de présence de {employee.employee_first_name} {user_last_name} pour le {attendance.attendance_date} a été validée",
                            redirect=reverse("request-attendance-view") + f"?id={attendance.id}",
                            icon="checkmark-circle-outline",
                        )

                except Attendance.DoesNotExist:
                    return Response({"detail": f"Attendance ID {attendance_id} not found"}, status=status.HTTP_404_NOT_FOUND)
                except Exception as e:
                    return Response({"detail": f"An error occurred while processing ID {attendance_id}: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": "Attendance requests have been approved successfully."}, status=status.HTTP_200_OK)

        # If serializer is not valid, return errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkRejectAttendanceRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            # Fetching the list of IDs
            ids = request.data.get("ids", [])
            
            # Validating the IDs
            if not ids or not isinstance(ids, list):
                return Response({"detail": "No attendance IDs provided or invalid format."}, status=status.HTTP_400_BAD_REQUEST)

            for attendance_id in ids:
                try:
                    # Fetching the attendance object by ID
                    attendance = get_object_or_404(Attendance, id=attendance_id)

                    # Checking permissions to reject the attendance request
                    if (
                        attendance.employee_id.employee_user_id == request.user
                        or is_reportingmanager(request)
                        or request.user.has_perm("attendance.change_attendance")
                    ):
                        # Mark attendance as rejected
                        attendance.is_validate_request_approved = False
                        attendance.is_validate_request = False
                        attendance.request_description = None
                        attendance.requested_data = None
                        attendance.request_type = None
                        attendance.save()

                        # Handling the deletion of create_request type attendance
                        if attendance.request_type == "create_request":
                            attendance.delete()
                            messages.success(request, _("The requested attendance is removed."))
                        else:
                            messages.success(request, _("The requested attendance is rejected."))

                        # Sending notifications about the rejection
                        employee = attendance.employee_id
                        notify.send(
                            request.user,
                            recipient=employee.employee_user_id,
                            verb=f"Your attendance request for {attendance.attendance_date} is rejected",
                            verb_ar=f"تم رفض طلبك للحضور في تاريخ {attendance.attendance_date}",
                            verb_de=f"Ihre Anwesenheitsanfrage für {attendance.attendance_date} wurde abgelehnt",
                            verb_es=f"Tu solicitud de asistencia para el {attendance.attendance_date} ha sido rechazada",
                            verb_fr=f"Votre demande de présence pour le {attendance.attendance_date} est rejetée",
                            icon="close-circle-outline",
                        )
                except Attendance.DoesNotExist:
                    messages.error(request, _("Attendance request not found"))
                except OverflowError:
                    messages.error(request, _("An overflow error occurred"))

            return Response({"message": "Attendance requests have been processed"}, status=status.HTTP_200_OK)
        
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON format"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EditValidateAttendanceAPI(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, attendance_id, format=None):
        try:
            attendance = Attendance.objects.get(id=attendance_id)
        except Attendance.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        initial = attendance.serialize()
        if attendance.request_type != "create_request":
            initial = json.loads(attendance.requested_data)
        initial["request_description"] = attendance.request_description
        form = AttendanceRequestForm(initial=initial)
        return Response(form.data)

    def post(self, request, attendance_id, format=None):
        try:
            attendance = Attendance.objects.get(id=attendance_id)
        except Attendance.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        form = AttendanceRequestForm(request.data, instance=copy.copy(attendance))
        if form.is_valid():
            instance = form.save()
            instance.employee_id = attendance.employee_id
            instance.id = attendance.id
            if attendance.request_type != "create_request":
                attendance.requested_data = json.dumps(instance.serialize())
                attendance.request_description = instance.request_description
                attendance.is_validate_request = True
                attendance.save()
            else:
                instance.is_validate_request_approved = False
                instance.is_validate_request = True
                instance.save()
            return Response({"message": "Attendance request updated."}, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class GetEmployeeShiftAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        employee_id = request.GET.get("employee_id")
        shift = None
        if employee_id:
            employee = get_object_or_404(Employee, id=employee_id)
            shift = employee.get_shift
        form = NewRequestForm()
        if request.GET.get("bulk") and eval(request.GET.get("bulk")):
            form = BulkAttendanceRequestForm()
        form.fields["shift_id"].queryset = EmployeeShift.objects.all()
        form.fields["shift_id"].widget.attrs["hx-trigger"] = "load,change"
        form.fields["shift_id"].initial = shift
        shift_data = EmployeeShiftSerializer(shift).data if shift else None
        return Response({
            "shift_data": shift_data,
            "form": form.initial
        }, status=status.HTTP_200_OK)



from django.http import Http404
class AttendanceRequestChangesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

class AttendanceRequestChangesAPIView(APIView):
    def get_attendance(self, attendance_id):
        try:
            return get_object_or_404(Attendance, id=attendance_id)
        except Attendance.DoesNotExist:
            raise Http404

    def post(self, request, attendance_id, *args, **kwargs):
        attendance = self.get_attendance(attendance_id)
        form = AttendanceRequestForm(request.POST, instance=copy.copy(attendance))
        form.fields["work_type_id"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "height:50px;border-radius:0;border:1px solid hsl(213deg,22%,84%)",
            }
        )
        form.fields["shift_id"].widget.attrs.update(
            {
                "class": "w-100",
                "style": "height:50px;border-radius:0;border:1px solid hsl(213deg,22%,84%)",
            }
        )
        work_type_id = form.data["work_type_id"]
        shift_id = form.data["shift_id"]
        if work_type_id is None or not len(work_type_id):
            form.add_error("work_type_id", "This field is required")
        if shift_id is None or not len(shift_id):
            form.add_error("shift_id", "This field is required")
        if form.is_valid():
            try:
                instance = form.save(commit=False)
                instance.employee_id = attendance.employee_id
                instance.id = attendance.id
                if attendance.request_type != "create_request":
                    attendance.requested_data = json.dumps(instance.serialize())
                    attendance.request_description = instance.request_description
                    attendance.is_validate_request = True
                    attendance.save()
                else:
                    instance.is_validate_request_approved = False
                    instance.is_validate_request = True
                    instance.save()
                messages.success(request, _("Attendance update request created."))
                employee = attendance.employee_id
                if attendance.employee_id.employee_work_info.reporting_manager_id:
                    reporting_manager = (
                        attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                    )
                    user_last_name = get_employee_last_name(attendance)
                    notify.send(
                        request.user,
                        recipient=reporting_manager,
                        verb=f"{employee.employee_first_name} {user_last_name}'s\
                              attendance update request for {attendance.attendance_date} is created",
                        verb_ar=f"تم إنشاء طلب تحديث الحضور لـ {employee.employee_first_name} \
                            {user_last_name }في {attendance.attendance_date}",
                        verb_de=f"Die Anfrage zur Aktualisierung der Anwesenheit von \
                            {employee.employee_first_name} {user_last_name} \
                                für den {attendance.attendance_date} wurde erstellt",
                        verb_es=f"Se ha creado la solicitud de actualización de asistencia para {employee.employee_first_name}\
                              {user_last_name} el {attendance.attendance_date}",
                        verb_fr=f"La demande de mise à jour de présence de {employee.employee_first_name}\
                              {user_last_name} pour le {attendance.attendance_date} a été créée",
                        redirect=reverse("request-attendance-view")
                        + f"?id={attendance.id}",
                        icon="checkmark-circle-outline",
                    )
                return Response({"message": _("Attendance update request created.")}, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                form.add_error(None, e.messages)
        return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)

# views.py



class RequestAttendanceAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            bulk_flag = request.GET.get("bulk")
            try:
                bulk = eval(bulk_flag) if bulk_flag else False
            except Exception:
                bulk = False

            if bulk:
                # BULK REQUEST HANDLING
                employee = request.user.employee_get
                form = BulkAttendanceRequestForm(data=request.data, initial={"employee_id": employee})
                
                if form.is_valid():
                    form.instance.attendance_clock_in_date = request.data.get("from_date")
                    form.instance.attendance_date = request.data.get("from_date")
                    instance = form.save(commit=False)
                    instance.save()
                    return Response(
                        {"message": _("Attendance request created")},
                        status=status.HTTP_201_CREATED
                    )
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # SINGLE (NON-BULK) REQUEST HANDLING
                form = NewRequestForm(data=request.data)
                form = choosesubordinates(request, form, "attendance.change_attendance")
                form.fields["employee_id"].queryset = (
                    form.fields["employee_id"].queryset | Employee.objects.filter(employee_user_id=request.user)
                )
                
                if form.is_valid():
                    if getattr(form, "new_instance", None) is not None:
                        form.new_instance.save()
                        return Response(
                            {"message": _("New attendance request created")},
                            status=status.HTTP_201_CREATED
                        )
                    else:
                        return Response(
                            {"message": _("Update request updated")},
                            status=status.HTTP_200_OK
                        )
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"error": _("An unexpected error occurred.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



from django.core.exceptions import ValidationError


import logging

logger = logging.getLogger(__name__)



from django.core.exceptions import ObjectDoesNotExist


class EditRequestAttendanceAPI(APIView):
    authentication_classes = [JWTAuthentication]
 
    def post(self, request, *args, **kwargs):
        try:
            serializer = AttendanceRequestSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            return Response({"error": "Related object not found: " + str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An unexpected error occurred: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from urllib.parse import parse_qs


class RequestAttendanceView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to view the attendances to request.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to view the attendances to request.
        """
        try:
            requests = Attendance.objects.filter(is_validate_request=True)
            requests = filtersubordinates(
                request=request,
                perm="attendance.view_attendance",
                queryset=requests,
            )
            requests = requests | Attendance.objects.filter(
                employee_id__employee_user_id=request.user,
                is_validate_request=True,
            )
            requests = AttendanceFilters(request.GET, requests).qs
            previous_data = request.GET.urlencode()
            data_dict = parse_qs(previous_data)
            get_key_instances(Attendance, data_dict)

            keys_to_remove = [key for key, value in data_dict.items() if value == ["unknown"]]
            for key in keys_to_remove:
                data_dict.pop(key)
            
            attendances = filtersubordinates(
                request=request,
                perm="attendance.view_attendance",
                queryset=Attendance.objects.all(),
            )
            attendances = attendances | Attendance.objects.filter(
                employee_id__employee_user_id=request.user
            )
            attendances = attendances.filter(employee_id__is_active=True)
            attendances = AttendanceFilters(request.GET, attendances).qs
            check_attendance = Attendance.objects.all()
            requests_ids = json.dumps(
                [instance.id for instance in paginator_qry(requests, None).object_list]
            )
            attendances_ids = json.dumps(
                [instance.id for instance in paginator_qry(attendances, None).object_list]
            )
            requests = requests.filter(employee_id__is_active=True)

            serialized_requests = AttendanceSerializer(paginator_qry(requests, None).object_list, many=True).data
            serialized_attendances = AttendanceSerializer(paginator_qry(attendances, None).object_list, many=True).data
            
            context = {
                "requests": serialized_requests,
                "attendances": serialized_attendances,
                "requests_ids": requests_ids,
                "attendances_ids": attendances_ids,
                "filter_dict": data_dict,
                "gp_fields": AttendanceRequestReGroup.fields,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class HourAttendanceSelectView(APIView):
    """
    API view to select hour attendance.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to select hour attendance.
        """
        try:
            page_number = request.GET.get("page")
            context = {}

            if page_number == "all":
                if request.user.has_perm("attendance.view_attendanceovertime"):
                    employees = AttendanceOverTime.objects.all()
                else:
                    employees = AttendanceOverTime.objects.filter(
                        employee_id__employee_user_id=request.user
                    ) | AttendanceOverTime.objects.filter(
                        employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                    )

                employee_ids = [str(emp.id) for emp in employees]
                total_count = employees.count()

                context = {"employee_ids": employee_ids, "total_count": total_count}

            return JsonResponse(context, safe=False)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)



class HourAttendanceSelectFilterView(APIView):
    """
    API view to select and filter hour attendance.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to select and filter hour attendance.
        """
        try:
            page_number = request.GET.get("page")
            filtered = request.GET.get("filter")
            filters = json.loads(filtered) if filtered else {}

            if page_number == "all":
                if request.user.has_perm("attendance.view_attendanceovertime"):
                    employee_filter = AttendanceOverTimeFilter(
                        filters, queryset=AttendanceOverTime.objects.all()
                    )
                else:
                    employee_filter = AttendanceOverTimeFilter(
                        filters,
                        queryset=AttendanceOverTime.objects.filter(
                            employee_id__employee_user_id=request.user
                        )
                        | AttendanceOverTime.objects.filter(
                            employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                        ),
                    )

                # Get the filtered queryset
                filtered_employees = employee_filter.qs

                employee_ids = [str(emp.id) for emp in filtered_employees]
                total_count = filtered_employees.count()

                context = {"employee_ids": employee_ids, "total_count": total_count}

                return JsonResponse(context, safe=False)
            else:
                return JsonResponse({"error": "Invalid page number."}, status=400)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)



from datetime import date

class WorkRecordsView(APIView):
    """
    API view to view work records.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to view work records.
        """
        try:
            today = date.today()
            previous_data = request.GET.urlencode()

            context = {
                "current_date": today,
                "pd": previous_data,
            }
            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)


from collections import defaultdict



class WorkRecordsChangeMonthView(APIView):
    """
    API view to change and view work records for a specific month.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to change and view work records for a specific month.
        """
        try:
            previous_data = request.GET.urlencode()
            employee_filter_form = EmployeeFilter()
            if request.GET.get("month"):
                date_obj = request.GET.get("month")
                month = int(date_obj.split("-")[1])
                year = int(date_obj.split("-")[0])
            else:
                month = date.today().month
                year = date.today().year

            schedules = list(EmployeeShiftSchedule.objects.all())
            employees = list(Employee.objects.filter(is_active=True))
            if request.method == "POST":
                employee_filter_form = EmployeeFilter(request.POST)
                employees = list(employee_filter_form.qs)
            data = []
            month_matrix = calendar.monthcalendar(year, month)

            days = [day for week in month_matrix for day in week if day != 0]
            current_month_date_list = [datetime(year, month, day).date() for day in days]

            all_work_records = WorkRecords.objects.filter(
                date__in=current_month_date_list
            ).select_related("employee_id")

            work_records_dict = defaultdict(lambda: defaultdict(lambda: None))
            for record in all_work_records:
                work_records_dict[record.employee_id.id][record.date] = record

            schedules_dict = defaultdict(dict)
            for schedule in schedules:
                schedules_dict[schedule.shift_id][schedule.day.day.lower()] = schedule

            for employee in employees:
                shift = getattr(getattr(employee, "employee_work_info", None), "shift_id", None)
                work_record_list = []

                for current_date in current_month_date_list:
                    day = current_date.strftime("%A").lower()
                    schedule = schedules_dict.get(shift, {}).get(day, None)
                    work_record = work_records_dict[employee.id].get(current_date, None)

                    if not work_record:
                        work_record = (
                            None
                            if not schedule or schedule.minimum_working_hour == "00:00"
                            else "EW"
                        )
                    work_record_list.append(work_record)

                data.append(
                    {
                        "employee": employee.id,
                        "work_record": WorkRecordsSerializer(work_record_list, many=True).data,
                    }
                )

            leave_dates = monthly_leave_days(month, year)
            page_number = request.GET.get("page")
            paginator = Paginator(data, get_pagination())
            data = paginator.get_page(page_number)

            context = {
                "current_month_dates_list": current_month_date_list,
                "leave_dates": leave_dates,
                "data": list(data),
                "pd": previous_data,
                "current_date": date.today(),
                "f": employee_filter_form.__dict__,  # Serialize form fields
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class AttendanceRequestCommentAPIView(APIView):
    """
    API view to create Attendance request comments.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request, attendance_id):
        """
        Handles POST requests to create attendance request comments.
        """
        try:
            attendance = get_object_or_404(Attendance, id=attendance_id)
            emp = getattr(request.user, 'employee_get', None)
            if not emp:
                return Response({"error": "Employee not found."}, status=404)

            form = AttendanceRequestCommentForm(request.POST)
            if form.is_valid():
                form.instance.employee_id = emp
                form.instance.request_id = attendance
                form.save()
                comments = AttendanceRequestComment.objects.filter(
                    request_id=attendance_id
                ).order_by("-created_at")
                no_comments = not comments.exists()
                form = AttendanceRequestCommentForm(
                    initial={"employee_id": emp.id, "request_id": attendance_id}
                )
                messages.success(request, _("Comment added successfully!"))
                work_info = EmployeeWorkInformation.objects.filter(
                    employee_id=attendance.employee_id
                )
                if work_info.exists():
                    if attendance.employee_id.employee_work_info.reporting_manager_id is not None:
                        if emp.id == attendance.employee_id.id:
                            rec = attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                            verb = f"{attendance.employee_id}'s attendance request has received a comment."
                        elif emp.id == attendance.employee_id.employee_work_info.reporting_manager_id.id:
                            rec = attendance.employee_id.employee_user_id
                            verb = "Your attendance request has received a comment."
                        else:
                            rec = [
                                attendance.employee_id.employee_user_id,
                                attendance.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            ]
                            verb = f"{attendance.employee_id}'s attendance request has received a comment."
                    else:
                        rec = attendance.employee_id.employee_user_id
                        verb = "Your attendance request has received a comment."
                    notify.send(
                        emp,
                        recipient=rec,
                        verb=verb,
                        redirect=reverse("request-attendance-view") + f"?id={attendance.id}",
                        icon="chatbox-ellipses",
                    )
                serialized_comments = AttendanceRequestCommentSerializer(comments, many=True).data
                return Response({
                    "comments": serialized_comments,
                    "no_comments": no_comments,
                    "request_id": attendance_id,
                }, status=200)
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)






class AttendanceRequestCommentView(APIView):
    """
    API view to show Attendance request comments.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, attendance_id):
        """
        Handles GET requests to show attendance request comments.
        """
        try:
            comments = AttendanceRequestComment.objects.filter(
                request_id=attendance_id
            ).order_by("-created_at")
            no_comments = not comments.exists()

            if request.FILES:
                files = request.FILES.getlist("files")
                comment_id = request.GET.get("comment_id")
                if comment_id:
                    comment = get_object_or_404(AttendanceRequestComment, id=comment_id)
                    attachments = []
                    for file in files:
                        file_instance = AttendanceRequestFile()
                        file_instance.file = file
                        file_instance.save()
                        attachments.append(file_instance)
                    comment.files.add(*attachments)

            serialized_comments = AttendanceRequestCommentSerializer(comments, many=True).data

            context = {
                "comments": serialized_comments,
                "no_comments": no_comments,
                "request_id": attendance_id,
            }
            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class DeleteAttendanceRequestCommentView(APIView):
    """
    API view to delete Attendance request comments.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, comment_id):
        """
        Handles DELETE requests to delete Attendance request comments.
        """
        try:
            comment = get_object_or_404(AttendanceRequestComment, id=comment_id)
            attendance_id = comment.request_id.id
            comment.delete()
            messages.success(request, _("Comment deleted successfully!"))
            return Response({"message": "Comment deleted successfully!", "attendance_id": attendance_id}, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class DepartmentOvertimeChartView(APIView):
    """
    API view to generate department overtime chart.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to generate department overtime chart.
        """
        try:
            start_date = request.GET.get("date") if request.GET.get("date") else date.today()
            chart_type = request.GET.get("type") if request.GET.get("type") else "day"
            end_date = request.GET.get("end_date") if request.GET.get("end_date") else start_date

            if chart_type == "day":
                start_date = start_date
                end_date = start_date
            elif chart_type == "weekly":
                start_date, end_date = get_week_start_end_dates(start_date)
            elif chart_type == "monthly":
                start_date, end_date = get_month_start_end_dates(start_date)
            elif chart_type == "date_range":
                start_date = start_date
                end_date = end_date

            attendance = total_attendance(start_date=start_date, department=None, end_date=end_date)

            condition = AttendanceValidationCondition.objects.first()
            min_ot = strtime_seconds("00:00")
            if condition is not None and condition.minimum_overtime_to_approve is not None:
                min_ot = strtime_seconds(condition.minimum_overtime_to_approve)
            attendances = attendance.filter(
                overtime_second__gte=min_ot,
                attendance_validated=True,
                employee_id__is_active=True,
                attendance_overtime_approve=True,
            )
            departments = []
            department_total = []

            for attendance in attendances:
                departments.append(attendance.employee_id.employee_work_info.department_id.department)
            departments = list(set(departments))

            for depart in departments:
                department_total.append({"department": depart, "ot_hours": 0})

            for attendance in attendances:
                if attendance.employee_id.employee_work_info.department_id:
                    department = attendance.employee_id.employee_work_info.department_id.department
                    ot = attendance.approved_overtime_second
                    ot_hrs = ot / 3600
                    for depart in department_total:
                        if depart["department"] == department:
                            depart["ot_hours"] += ot_hrs

            dataset = [
                {
                    "label": "",
                    "data": [],
                }
            ]

            for depart_total, depart in zip(department_total, departments):
                if depart == depart_total["department"]:
                    dataset[0]["data"].append(depart_total["ot_hours"])

            response = {
                "dataset": dataset,
                "labels": departments,
                "department_total": department_total,
                "message": _("No validated Overtimes were found"),
                "emptyImageSrc": f"/{settings.STATIC_URL}images/ui/overtime-icon.png",
            }

            return JsonResponse(response, status=200)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)






class ValidatedAttendancesTableView(APIView):
    """
    API view to render validated attendances table.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to render validated attendances table.
        """
        try:
            page_number = request.GET.get("page")
            previous_data = request.GET.urlencode()
            validate_attendances = Attendance.objects.filter(
                attendance_validated=False, employee_id__is_active=True
            )
            validate_attendances = filtersubordinates(
                request=request,
                perm="attendance.change_attendance",
                queryset=validate_attendances,
            )

            context = {
                "validate_attendances": paginator_qry(validate_attendances, page_number),
                "pd": previous_data,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class ValidatedAttendancesTableView(APIView):
    """
    API view to render validated attendances table.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to render validated attendances table.
        """
        try:
            page_number = request.GET.get("page")
            previous_data = request.GET.urlencode()
            validate_attendances = Attendance.objects.filter(
                attendance_validated=False, employee_id__is_active=True
            )
            validate_attendances = filtersubordinates(
                request=request,
                perm="attendance.change_attendance",
                queryset=validate_attendances,
            )

            paginated_attendances = paginator_qry(validate_attendances, page_number)
            serialized_attendances = AttendanceSerializer(paginated_attendances, many=True).data

            context = {
                "validate_attendances": serialized_attendances,
                "pd": previous_data,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



from base.methods import closest_numbers  # Corrected import statement

class UserRequestOneView(APIView):
    """
    API endpoint to view one user attendance request.
    """

    def get(self, request, id):
        try:
            attendance_request = Attendance.objects.get(id=id)

            at_work_seconds = attendance_request.at_work_second
            hours_at_work = at_work_seconds // 3600
            minutes_at_work = (at_work_seconds % 3600) // 60
            at_work = "{:02}:{:02}".format(hours_at_work, minutes_at_work)

            over_time_seconds = attendance_request.overtime_second
            hours_over_time = over_time_seconds // 3600
            minutes_over_time = (over_time_seconds % 3600) // 60
            over_time = "{:02}:{:02}".format(hours_over_time, minutes_over_time)

            instance_ids_json = request.query_params.get("instances_ids")
            instance_ids = json.loads(instance_ids_json) if instance_ids_json else []
            previous_instance, next_instance = closest_numbers(instance_ids, id)

            data = {
                "attendance_request": AttendanceSerializer(attendance_request).data,
                "at_work": at_work,
                "over_time": over_time,
                "previous_instance": previous_instance,
                "next_instance": next_instance,
                "instance_ids_json": instance_ids_json,
                "dashboard": request.query_params.get("dashboard"),
            }
            return Response(data, status=status.HTTP_200_OK)

        except Attendance.DoesNotExist:
            return Response({"error": "Attendance request not found"}, status=status.HTTP_404_NOT_FOUND)



class PendingHoursView(APIView):
    """
    API view to generate pending hours chart dashboard.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to generate pending hours chart dashboard.
        """
        try:
            records = AttendanceOverTimeFilter(request.GET).qs
            labels = list(Department.objects.values_list("department", flat=True))
            data = {
                "labels": labels,
                "datasets": [
                    pending_hour_data(labels, records),
                    worked_hour_data(labels, records),
                ],
            }

            return JsonResponse({"data": data}, status=200)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)




class GraceTimeCreateView(APIView):
    """
    API view to create grace time.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    
    def post(self, request):
        """
        Handles POST requests to create grace time.
        """
        try:
            form = GraceTimeForm(request.POST)
            if form.is_valid():
                cleaned_data = form.cleaned_data
                gracetime = form.save()
                shifts = cleaned_data.get("shifts")
                for shift in shifts:
                    shift.grace_time_id = gracetime
                    shift.save()
                messages.success(request, _("Grace time created successfully."))
                return HttpResponse("<script>window.location.reload()</script>")
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class GraceTimeUpdateView(APIView):
    """
    API view to update grace time.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, grace_id):
        """
        Handles POST requests to update grace time.
        """
        try:
            grace_time = get_object_or_404(GraceTime, id=grace_id)
            form = GraceTimeForm(request.POST, instance=grace_time)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.save()
                messages.success(request, _("Grace time updated successfully."))
                return HttpResponse("<script>window.location.reload()</script>")
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)


from django.db.models import ProtectedError

class GraceTimeDeleteView(APIView):
    """
    API view to delete grace time.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, grace_id):
        """
        Handles DELETE requests to delete grace time.
        """
        try:
            grace_time = get_object_or_404(GraceTime, id=grace_id)
            grace_time.delete()
            messages.success(request, _("Grace time deleted successfully."))
            context = {
                "condition": AttendanceValidationCondition.objects.first(),
                "default_grace_time": GraceTime.objects.filter(is_default=True).first(),
                "grace_times": GraceTime.objects.all().exclude(is_default=True),
            }
            return Response({"message": "Grace time deleted successfully.", "context": context}, status=200)
        except GraceTime.DoesNotExist:
            messages.error(request, _("Grace Time does not exist."))
            return Response({"error": "Grace Time does not exist."}, status=404)
        except ProtectedError:
            messages.error(request, _("Related data exists."))
            return Response({"error": "Related data exists."}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



class GraceTimeAssignView(APIView):
    """
    API view to assign grace time to shifts.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

  
    def post(self, request, grace_id):
        """
        Handles POST requests to assign grace time to shifts.
        """
        try:
            gracetime = get_object_or_404(GraceTime, id=grace_id)
            form = GraceTimeAssignForm(request.POST)
            if form.is_valid():
                cleaned_data = form.cleaned_data
                shifts = cleaned_data.get("shifts")
                for shift in shifts:
                    shift.grace_time_id = gracetime
                    shift.save()
                messages.success(request, _("Grace time added to shifts successfully."))
                return HttpResponse("<script>window.location.reload()</script>")
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class OwnAttendanceSortView(APIView):
    """
    API view to sort out attendances.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to sort out attendances.
        """
        try:
            attendances = Attendance.objects.filter(employee_id=request.user.employee_get)
            previous_data = request.GET.urlencode()
            attendances = sortby(request, attendances, "orderby")

            paginated_attendances = paginator_qry(attendances, request.GET.get("page"))
            serialized_attendances = AttendanceSerializer(paginated_attendances, many=True).data

            context = {
                "attendances": serialized_attendances,
                "pd": previous_data,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)






class AttendanceActivityExportView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handle GET request to export attendance activity data.
        """
        try:
            if request.headers.get("HX-Request") == "true":
                export_form = AttendanceActivityExportForm()
                context = {
                    "export_form": export_form,
                    "export": AttendanceActivityFilter(
                        queryset=AttendanceActivity.objects.all()
                    ),
                }
                return Response({
                    "template": render(
                        request,
                        "attendance/attendance_activity/export_filter.html",
                        context=context,
                    ).content.decode("utf-8")
                }, status=200)
            return export_data(
                request=request,
                model=AttendanceActivity,
                filter_class=AttendanceActivityFilter,
                form_class=AttendanceActivityExportForm,
                file_name="Attendance_activity",
            )
        except Exception as e:
            return JsonResponse({
                "error": "Failed to process request",
                "details": str(e)
            }, status=400)


from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.http import JsonResponse
import json


class LateComeEarlyOutExportView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handle GET request to export late come early out data.
        """
        try:
            if request.headers.get("HX-Request") == "true":
                filter_instance = LateComeEarlyOutFilter(
                    queryset=AttendanceLateComeEarlyOut.objects.all()
                )
                form = LateComeEarlyOutExportForm()
                context = {
                    "export": filter_instance,
                    "export_form": form,
                }
                return Response(context)
            return export_data(
                request=request,
                model=AttendanceLateComeEarlyOut,
                filter_class=LateComeEarlyOutFilter,
                form_class=LateComeEarlyOutExportForm,
                file_name="Late_come_",
            )
        except Exception as e:
            return JsonResponse({
                "error": "Invalid data provided",
                "details": str(e)
            }, status=400)




class AttendanceAccountExportView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handle GET request to export attendance account data.
        """
        try:
            if request.headers.get("HX-Request") == "true":
                context = {
                    "export_obj": AttendanceOverTimeFilter(),
                    "export_fields": AttendanceOverTimeExportForm(),
                }
                rendered_content = render(
                    request,
                    "attendance/attendance_account/attendance_account_export_filter.html",
                    context=context,
                ).content.decode("utf-8")
                return Response({
                    "template": rendered_content
                }, status=200)
            return export_data(
                request=request,
                model=AttendanceOverTime,
                filter_class=AttendanceOverTimeFilter,
                form_class=AttendanceOverTimeExportForm,
                file_name="Attendance_Account",
            )
        except Exception as e:
            return JsonResponse({
                "error": "Failed to process request",
                "details": str(e)
            }, status=400)




class CutAvailableLeaveView(APIView):
    """
    API view to create the penalties.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

  
    def post(self, request, instance_id):
        """
        Handles POST requests to create the penalties.
        """
        try:
            instance = get_object_or_404(AttendanceLateComeEarlyOut, id=instance_id)
            form = PenaltyAccountForm(request.POST)
            if form.is_valid():
                penalty_instance = form.instance
                penalty = PenaltyAccounts()
                penalty.employee_id = instance.employee_id
                penalty.late_early_id = instance
                penalty.penalty_amount = penalty_instance.penalty_amount

                if apps.is_installed("leave"):
                    penalty.leave_type_id = penalty_instance.leave_type_id
                    penalty.minus_leaves = penalty_instance.minus_leaves
                    penalty.deduct_from_carry_forward = penalty_instance.deduct_from_carry_forward

                penalty.save()
                return Response({"success": "Penalty/Fine added"}, status=201)
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)
