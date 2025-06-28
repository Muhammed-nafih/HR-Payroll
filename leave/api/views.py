from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from employee.authentication import JWTAuthentication
from rest_framework.decorators import permission_classes
from rest_framework import status
from leave.models import( 
LeaveRequest,
LeaveType,
LeaveGeneralSetting,
Employee,  
LeaveRequestConditionApproval,
LeaveRequest, 
AvailableLeave,
LeaverequestComment,
JobPosition,
RestrictLeave,
Holidays,
CompanyLeaves,
Department,
LeaveAllocationRequest,
EmployeeWorkInformation,
LeaverequestFile,
LeaveallocationrequestComment,
CompensatoryLeaverequestComment,
CompensatoryLeaveRequest




)
from attendance.models import Attendance
from leave.api.serializers import (LeaveRequestSerializer,
LeaveTypeSerializer, 
LeaveRequestConditionApprovalSerializer,
LeaveRequestSerializer, 
LeaveRequestConditionApprovalSerializer,
LeaveRequestUpdateFormSerializer,
AvailableLeaveSerializer,
AssignLeaveFormSerializer,
JobPositionSerializer,
RestrictLeaveSerializer,
HolidaysSerializer,
LeaveAllocationRequestSerializer,
LeaverequestCommentSerializer,
LeaveallocationrequestCommentSerializer,
CompensatoryLeaverequestCommentSerializer,
CompensatoryLeaveRequestSerializer,
LeaveAssignSerializer,
UserLeaveRequestSerializer,
LeaveAllocationRequestRejectSerializer


)
from rest_framework.pagination import PageNumberPagination
from leave.filters import LeaveTypeFilter 
from django.core.paginator import Paginator
from base.methods import get_pagination, choosesubordinates,filtersubordinates,export_data, sortby,get_key_instances,closest_numbers
from leave.methods import attendance_days
from urllib.parse import parse_qs
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from leave.views import multiple_approvals_check ,leave_request_view, leave_request_approve, leave_request_cancel, company_leave_dates_list,filter_compensatory_leave
from leave.threading import LeaveMailSendThread
from django.urls import reverse
from django.contrib import messages
from notifications.signals import notify
import contextlib

from leave.forms import (LeaveRequestCreationForm,
LeaveRequestExportForm,
LeaveRequestUpdationForm,
RejectForm,
AssignLeaveForm,
LeaveOneAssignForm,
AvailableLeaveUpdateForm,
AvailableLeaveColumnExportForm,
RestrictLeaveForm,
RestrictLeaveForm,
UpdateLeaveTypeForm,
UserLeaveRequestForm,
UserLeaveRequestCreationForm,
LeaveAllocationRequestForm,
LeaveAllocationRequestRejectForm,
LeaverequestcommentForm,
LeaveallocationrequestcommentForm,
CompensatoryLeaveForm,
 LeaveTypeForm,
 CompensatoryLeaveRequestRejectForm


)
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from leave.methods import filter_conditional_leave_request, get_horilla_model_class, leave_requested_dates,calculate_requested_days, holiday_dates_list,get_leave_day_attendance
from leave.filters import (LeaveRequestFilter,
AssignedLeaveFilter, 
LeaveAssignReGroup,
RestrictLeaveFilter,
AssignedLeaveFilter ,
UserLeaveRequestFilter,
MyLeaveRequestReGroup,
LeaveAllocationRequestFilter,
LeaveAllocationRequestReGroup,
CompensatoryLeaveRequestFilter

)
from horilla.decorators import manager_can_enter
from horilla.decorators import permission_required
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils.http import unquote

from django.apps import apps
from django.http import JsonResponse,HttpResponse,HttpResponseRedirect
from django.shortcuts import render,redirect
from horilla.group_by import group_by_queryset
from datetime import date ,datetime,timedelta
from django.template.loader import render_to_string
from collections import defaultdict
import calendar
import json
from base.models import PenaltyAccounts
from base.forms import PenaltyAccountForm
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist




class LeaveTypeCreation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        form = LeaveTypeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return Response({"detail": _("New leave type created successfully")}, status=status.HTTP_201_CREATED)
        else:
            errors = form.errors.as_json()
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)



@permission_classes([IsAuthenticated, ])

class LeaveRequestAPIView(APIView):
 
    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Leave request created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


import numpy as np
def sanitize_data(data):
    if isinstance(data, float):
        if np.isinf(data) or np.isnan(data):
            return 0.0
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_data(value) for key, value in data.items()}
    return data


class LeaveTypeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        try:
            queryset = LeaveType.objects.all().exclude(is_compensatory_leave=True)
            if (LeaveGeneralSetting.objects.first() and
                LeaveGeneralSetting.objects.first().compensatory_leave):
                queryset = LeaveType.objects.all()
            
            page_number = request.GET.get("page")
            page_obj = paginator_qry(queryset, page_number)
            previous_data = request.GET.urlencode()
            leave_type_filter = LeaveTypeFilter()
            requests_ids = list(queryset.values_list("id", flat=True))

            response_data = {
                "leave_types": list(page_obj.object_list.values()),  
                "form": leave_type_filter.form.as_p(),  
                "previous_data": previous_data,
                "requests_ids": requests_ids,
            }
            
            sanitized_data = sanitize_data(response_data)
            
            return Response(sanitized_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def paginator_qry(qryset, page_number):
    paginator = Paginator(qryset, get_pagination())
    qryset = paginator.get_page(page_number)
    return qryset


class LeaveTypeIndividualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        """
        API endpoint to view one leave type.
        """
        try:
            leave_type = LeaveType.find(id)
            leave_type_data = LeaveTypeSerializer(leave_type).data
            requests_ids_json = request.GET.get("instances_ids")
            compensatory = request.GET.get("compensatory")

            context = {
                "leave_type": leave_type_data,
                "compensatory": compensatory
            }

            if requests_ids_json:
                requests_ids = json.loads(requests_ids_json)
                previous_id, next_id = closest_numbers(requests_ids, id)
                context["previous"] = previous_id
                context["next"] = next_id
                context["requests_ids"] = requests_ids_json

            return Response(context, status=status.HTTP_200_OK)
        except LeaveType.DoesNotExist:
            return Response({"message": "Leave type not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class LeaveTypeFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            queryset = LeaveType.objects.all()
            page_number = request.GET.get("page")
            leave_type_filter = LeaveTypeFilter(request.GET, queryset).qs
            page_obj = paginator_qry(leave_type_filter, page_number)
            previous_data = request.GET.urlencode()
            requests_ids = list(leave_type_filter.values_list("id", flat=True))
            data_dict = parse_qs(previous_data)
            
            response_data = {
                "leave_types": LeaveTypeSerializer(page_obj, many=True).data, 
                "previous_data": previous_data,
                "filter_dict": data_dict,
                "requests_ids": requests_ids,
            }

            sanitized_data = sanitize_data(response_data) 
            
            return Response(sanitized_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class LeaveTypeUpdateView(APIView):
    """
    API endpoint to update a leave type.

    Args:
        request (HttpRequest): The HTTP request object.
        id (int): The ID of the leave type to update.

    Returns:
        JsonResponse: Success or error message with status code.
    """

    def post(self, request, id):
        try:
            leave_type = get_object_or_404(LeaveType, id=id)
            form = UpdateLeaveTypeForm(request.POST, request.FILES, instance=leave_type)

            if form.is_valid():
                form.save()
                messages.success(request, _("Leave type is updated successfully.."))
                return Response({
                    "message": "Leave type is updated successfully.."
                }, status=status.HTTP_200_OK)
            return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Failed to update leave type", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LeaveTypeDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, obj_id, *args, **kwargs):
        try:
            leave_type = LeaveType.objects.get(id=obj_id)
            leave_type.delete()
            return Response({"message": "Leave type deleted successfully."}, status=status.HTTP_200_OK)
        except LeaveType.DoesNotExist:
            return Response({"message": "Leave type not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError as e:
            models_verbose_name_sets = set()
            for obj in e.protected_objects:
                models_verbose_name_sets.add(obj._meta.verbose_name)
            models_verbose_name_str = ", ".join(models_verbose_name_sets)
            return Response(
                {"message": f"This leave type is already in use for {models_verbose_name_str}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class GetEmployeeLeaveTypesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            employee_id = request.GET.get("employee_id")
            form_class = LeaveRequestUpdationForm if request.GET.get("form") == "LeaveRequestUpdationForm" else LeaveRequestCreationForm
            form = form_class()

            if employee_id:
                employee = get_object_or_404(Employee, id=employee_id)
                assigned_leave_types = LeaveType.objects.filter(
                    id__in=employee.available_leave.values_list("leave_type_id", flat=True)
                )
                form.fields["leave_type_id"].queryset = assigned_leave_types
            else:
                form.fields["leave_type_id"].queryset = LeaveType.objects.none()

            leave_types = form.fields["leave_type_id"].queryset
            leave_types_data = LeaveTypeSerializer(leave_types, many=True).data

            return Response({
                "status": "success",
                "leave_types": leave_types_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MultipleApprovalsCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):

        try:
            approvals = LeaveRequestConditionApproval.objects.filter(leave_request_id=id)
            requested_query = approvals.filter(is_approved=False).order_by("sequence")
            approved_query = approvals.filter(is_approved=True).order_by("sequence")
            managers = [manager.manager_id for manager in approvals]

            if approvals.exists():
                result = {
                    "managers": managers,
                    "approved": LeaveRequestConditionApprovalSerializer(approved_query, many=True).data,
                    "requested": LeaveRequestConditionApprovalSerializer(requested_query, many=True).data,
                    "approvals": LeaveRequestConditionApprovalSerializer(approvals, many=True).data,
                }
            else:
                result = False

            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class LeaveRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        queryset = LeaveRequestFilter(request.GET).qs.order_by("-id").distinct()
        multiple_approvals = filter_conditional_leave_request(request).distinct()
        normal_requests = filtersubordinates(request, queryset, "leave.view_leaverequest")

        if not request.user.is_superuser:
            multi_approve_requests = LeaveRequestConditionApproval.objects.filter(
                is_approved=False, is_rejected=False
            )

            multi_ids = [req.leave_request_id.id for req in multi_approve_requests]

            normal_requests = [
                leave.id for leave in normal_requests if leave.id not in multi_ids
            ]

            normal_requests = LeaveRequest.objects.filter(id__in=normal_requests).distinct()

        queryset = normal_requests | multiple_approvals
        page_number = request.GET.get("page")
        paginator = Paginator(queryset, 10)
        page_obj = paginator.get_page(page_number)

        leave_requests = queryset

        leave_requests_with_interview = []
        if apps.is_installed("recruitment"):
            InterviewSchedule = get_horilla_model_class(
                app_label="recruitment", model="interviewschedule"
            )
            for leave_request in leave_requests:
                interviews = InterviewSchedule.objects.filter(
                    employee_id=leave_request.employee_id,
                    interview_date__range=[
                        leave_request.start_date,
                        leave_request.end_date,
                    ],
                )
                if interviews:
                    leave_requests_with_interview.append(leave_request)

        requests = queryset.filter(status="requested").count()
        requests_ids = list(page_obj.object_list.values_list("id", flat=True))
        approved_requests = queryset.filter(status="approved").count()
        rejected_requests = queryset.filter(status="cancelled").count()
        previous_data = request.GET.urlencode()

        data = {
            "leave_requests": LeaveRequestSerializer(page_obj, many=True).data,
            "pd": previous_data,
            "requests": requests,
            "approved_requests": approved_requests,
            "rejected_requests": rejected_requests,
            "requests_ids": requests_ids,
            "current_date": date.today(),
            "leave_requests_with_interview": LeaveRequestSerializer(leave_requests_with_interview, many=True).data,
        }
        return Response(data, status=status.HTTP_200_OK)


class LeaveRequestWithInterviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        """
        API view to get leave requests with interviews
        """
        leave_requests_with_interview = []
        if apps.is_installed("recruitment"):
            leave_requests = LeaveRequest.objects.all()
            for leave_request in leave_requests:
                InterviewSchedule = get_horilla_model_class(
                    app_label="recruitment", model="interviewschedule"
                )
                interviews = InterviewSchedule.objects.filter(
                    employee_id=leave_request.employee_id,
                    interview_date__range=[
                        leave_request.start_date,
                        leave_request.end_date,
                    ],
                )
                if interviews:
                    leave_requests_with_interview.append(leave_request)

        serializer = LeaveRequestSerializer(leave_requests_with_interview, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)






class LeaveRequestFilterView(APIView):
    permission_classes = [IsAuthenticated]
    

    def get(self, request, format=None):
        try:
            previous_data = request.GET.urlencode()
            queryset = LeaveRequestFilter(request.GET).qs.order_by("-id")

            leave_requests = queryset

            leave_requests_with_interview = []
            if apps.is_installed("recruitment"):
                for leave_request in leave_requests:
                    InterviewSchedule = get_horilla_model_class(
                        app_label="recruitment", model="interviewschedule"
                    )
                    interviews = InterviewSchedule.objects.filter(
                        employee_id=leave_request.employee_id,
                        interview_date__range=[
                            leave_request.start_date,
                            leave_request.end_date,
                        ],
                    )
                    if interviews:
                        leave_requests_with_interview.append(leave_request)

            field = request.GET.get("field")
            multiple_approvals = filter_conditional_leave_request(request)

            queryset = filtersubordinates(request, queryset, "leave.view_leaverequest")

            if not request.user.is_superuser:
                multi_approve_requests = LeaveRequestConditionApproval.objects.filter(
                    is_approved=False, is_rejected=False
                )

                multi_ids = [req.leave_request_id.id for req in multi_approve_requests]

                queryset = [leave.id for leave in queryset if leave.id not in multi_ids]
                queryset = LeaveRequest.objects.filter(id__in=queryset)

            queryset = queryset | multiple_approvals
            leave_request_filter = LeaveRequestFilter(request.GET, queryset).qs
            page_number = request.GET.get("page")
            if request.GET.get("sortby"):
                leave_request_filter = sortby(request, leave_request_filter, "sortby")

            if field:
                leave_request_filter = group_by_queryset(
                    leave_request_filter, field, request.GET.get("page"), "page"
                )
                list_values = [entry["list"] for entry in leave_request_filter]
                id_list = []
                for value in list_values:
                    for instance in value.object_list:
                        id_list.append(instance.id)
                requests_ids = json.dumps(list(id_list))
            else:
                leave_request_filter = paginator_qry(
                    leave_request_filter, request.GET.get("page")
                )
                requests_ids = json.dumps(
                    [instance.id for instance in leave_request_filter.object_list]
                )

            data_dict = []
            if not request.GET.get("dashboard"):
                data_dict = parse_qs(previous_data)
                get_key_instances(LeaveRequest, data_dict)

            if "status" in data_dict:
                status_list = data_dict["status"]
                if len(status_list) > 1:
                    data_dict["status"] = [status_list[-1]]

            return JsonResponse({
                "status": "success",
                "leave_requests": LeaveRequestSerializer(leave_request_filter, many=True).data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "field": field,
                "dashboard": request.GET.get("dashboard"),
                "requests_ids": requests_ids,
                "current_date": date.today(),
                "leave_requests_with_interview": LeaveRequestSerializer(leave_requests_with_interview, many=True).data,
            }, status=status.HTTP_200_OK)

        except LeaveRequest.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "Leave request not found."
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": "An unexpected error occurred: " + str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class LeaveRequestUpdateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id, format=None):
        leave_request = get_object_or_404(LeaveRequest, id=id)
        leave_type_id = leave_request.leave_type_id
        employee = leave_request.employee_id
        form = LeaveRequestUpdationForm(instance=leave_request)

        if employee is not None:
            available_leaves = employee.available_leave.all()
            assigned_leave_types = LeaveType.objects.filter(
                id__in=available_leaves.values_list("leave_type_id", flat=True)
            )
            
            # Check if leave_type_id is not None
            if leave_type_id is not None:
                if leave_type_id.id not in assigned_leave_types.values_list("id", flat=True):
                    assigned_leave_types = assigned_leave_types | LeaveType.objects.filter(id=leave_type_id.id)
                form.fields["leave_type_id"].queryset = assigned_leave_types

        form = choosesubordinates(request, form, "leave.add_leaverequest")
        if request.method == "POST":
            form = LeaveRequestUpdationForm(request.POST, request.FILES, instance=leave_request)
            form = choosesubordinates(request, form, "leave.add_leaverequest")
            if form.is_valid():
                leave_request = form.save(commit=False)
                save = True

                if save:
                    leave_request.save()
                    messages.success(request, ("Leave request is updated successfully."))
                    with contextlib.suppress(Exception):
                        notify.send(
                            request.user.employee_get,
                            recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            verb=f"Leave request updated for {leave_request.employee_id}.",
                            verb_ar=f"تم تحديث طلب الإجازة لـ {leave_request.employee_id}.",
                            verb_de=f"Urlaubsantrag aktualisiert für {leave_request.employee_id}.",
                            verb_es=f"Solicitud de permiso actualizada para {leave_request.employee_id}.",
                            verb_fr=f"Demande de congé mise à jour pour {leave_request.employee_id}.",
                            icon="people-circle",
                            redirect=reverse("request-view") + f"?id={leave_request.id}",
                        )

                    return Response(
                        {"detail": ("Leave request is updated successfully.")},
                        status=status.HTTP_200_OK
                    )
        
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

class LeaveRequestDeleteView(APIView):
    permission_classes = [IsAuthenticated, ]

    def delete(self, request, id, format=None):
        previous_data = request.GET.urlencode()
        try:
            leave_request = get_object_or_404(LeaveRequest, id=id)
            leave_request.delete()
            message = {"message": "Leave request deleted successfully."}
            return Response(message, status=status.HTTP_200_OK)
        except LeaveRequest.DoesNotExist:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError:
            return Response({"error": "Cannot delete leave request due to related entries."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class LeaveRequestApproveAPI(APIView):

    def post(self, request, id, emp_id=None):
        """
        API to approve a leave request.
        
        Args:
            id (int): Leave request id
            emp_id (int, optional): Employee id if the approval operation comes from 
                                    "/employee/employee-view/{employee_id}/" template. Defaults to None.
        """
        try:
            leave_request = get_object_or_404(LeaveRequest, id=id)
            employee_id = leave_request.employee_id
            leave_type_id = leave_request.leave_type_id
            available_leave = get_object_or_404(AvailableLeave, leave_type_id=leave_type_id, employee_id=employee_id)
            total_available_leave = available_leave.available_days + available_leave.carryforward_days
            
            if leave_request.status != "approved":
                if total_available_leave >= leave_request.requested_days:
                    if leave_request.requested_days > available_leave.available_days:
                        leave = leave_request.requested_days - available_leave.available_days
                        leave_request.approved_available_days = available_leave.available_days
                        available_leave.available_days = 0
                        available_leave.carryforward_days -= leave
                        leave_request.approved_carryforward_days = leave
                    else:
                        available_leave.available_days -= leave_request.requested_days
                        leave_request.approved_available_days = leave_request.requested_days
                    leave_request.status = "approved"
                    
                    if not leave_request.multiple_approvals():
                        available_leave.save()
                        leave_request.save()
                    else:
                        if request.user.is_superuser:
                            LeaveRequestConditionApproval.objects.filter(leave_request_id=leave_request).update(is_approved=True)
                            available_leave.save()
                            leave_request.save()
                        else:
                            conditional_requests = leave_request.multiple_approvals()
                            approver = [
                                manager for manager in conditional_requests["managers"]
                                if manager.employee_user_id == request.user
                            ]
                            condition_approval = LeaveRequestConditionApproval.objects.filter(manager_id=approver[0], leave_request_id=leave_request).first()
                            condition_approval.is_approved = True
                            managers = [manager.employee_user_id for manager in conditional_requests["managers"]]
                            if len(managers) > condition_approval.sequence:
                                with contextlib.suppress(Exception):
                                    notify.send(
                                        request.user.employee_get,
                                        recipient=managers[condition_approval.sequence],
                                        verb="You have a new leave request to validate.",
                                        verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                                        verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                                        verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                                        verb_fr="Vous avez une nouvelle demande de congé à valider.",
                                        icon="people-circle",
                                        redirect=f"/leave/request-view?id={leave_request.id}",
                                    )

                            condition_approval.save()
                            if approver[0] == conditional_requests["managers"][-1]:
                                available_leave.save()
                                leave_request.save()
                    
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_request.employee_id.employee_user_id,
                        verb="Your Leave request has been approved",
                        verb_ar="تمت الموافقة على طلب الإجازة الخاص بك",
                        verb_de="Ihr Urlaubsantrag wurde genehmigt",
                        verb_es="Se ha aprobado su solicitud de permiso",
                        verb_fr="Votre demande de congé a été approuvée",
                        icon="people-circle",
                        redirect=reverse("user-request-view") + f"?id={leave_request.id}",
                    )
                    
                    mail_thread = LeaveMailSendThread(request, leave_request, type="approve")
                    mail_thread.start()

                    return Response({"message": "Leave request approved successfully."}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": f"{employee_id} doesn't have enough leave days to approve the request."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "Leave request already approved."}, status=status.HTTP_400_BAD_REQUEST)
        
        except LeaveRequest.DoesNotExist:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        except AvailableLeave.DoesNotExist:
            return Response({"error": "Available leave record not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from .views import leave_request_approve  # Import the leave_request_approve function


class LeaveRequestBulkApproveView(APIView):
    permission_classes = [IsAuthenticated,]

    def post(self, request, format=None):
        request_ids = request.data.get("ids", [])
        for request_id in request_ids:
            try:
                leave_request = get_object_or_404(LeaveRequest, id=int(request_id))
                if leave_request.status == "requested" and (
                    leave_request.start_date >= datetime.today().date()
                    or request.user.has_perm("leave.change_leaverequest")
                ):
                    leave_request_approve(request, leave_request.id)
                else:
                    if leave_request.status == "approved":
                        message = (
                            "{} {} request already approved"
                        ).format(leave_request.employee_id, leave_request.leave_type_id)
                    elif leave_request.start_date < datetime.today().date():
                        message = (
                            "{} {} request date exceeded"
                        ).format(leave_request.employee_id, leave_request.leave_type_id)
                    else:
                        message = (
                            "{} {} can't approve."
                        ).format(leave_request.employee_id, leave_request.leave_type_id)
    
                    return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, OverflowError, LeaveRequest.DoesNotExist):
                return Response({"error": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({"message": "Bulk leave requests approved successfully"}, status=status.HTTP_200_OK)



class LeaveRequestBulkRejectView(APIView):
    permission_classes = [IsAuthenticated, ]

    def post(self, request, format=None):
        request_ids = request.data.get("request_ids", [])
        for request_id in request_ids:
            leave_request = (
                get_object_or_404(LeaveRequest, id=int(request_id)) if request_id else None
            )
            leave_request_cancel(request, leave_request.id)
        
        return Response({"message": "Bulk leave requests rejected successfully"}, status=status.HTTP_200_OK)


from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


class LeaveRequestCancelView(APIView):
    permission_classes = [IsAuthenticated,]

    def post(self, request, id, format=None):
        form = RejectForm(request.data)
        if form.is_valid():
            leave_request = get_object_or_404(LeaveRequest, id=id)
            employee_id = leave_request.employee_id
            leave_type_id = leave_request.leave_type_id
            available_leave = get_object_or_404(AvailableLeave, leave_type_id=leave_type_id, employee_id=employee_id)
            if leave_request.status != "rejected":
                available_leave.available_days += leave_request.approved_available_days
                available_leave.carryforward_days += leave_request.approved_carryforward_days
                leave_request.approved_available_days = 0
                leave_request.approved_carryforward_days = 0
                leave_request.status = "rejected"
                leave_request.leave_clashes_count = 0

                if leave_request.multiple_approvals() and not request.user.is_superuser:
                    conditional_requests = leave_request.multiple_approvals()
                    approver = [
                        manager for manager in conditional_requests["managers"]
                        if manager.employee_user_id == request.user
                    ]
                    condition_approval = get_object_or_404(
                        LeaveRequestConditionApproval, 
                        manager_id=approver[0], 
                        leave_request_id=leave_request
                    )
                    condition_approval.is_approved = False
                    condition_approval.is_rejected = True
                    condition_approval.save()

                leave_request.reject_reason = form.cleaned_data["reason"]
                leave_request.save()
                available_leave.save()
                
                comment = LeaverequestComment()
                comment.request_id = leave_request
                comment.employee_id = request.user.employee_get
                comment.comment = leave_request.reject_reason
                comment.save()

                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_request.employee_id.employee_user_id,
                        verb="Your leave request has been rejected.",
                        verb_ar="تم رفض طلب الإجازة الخاص بك",
                        verb_de="Ihr Urlaubsantrag wurde abgelehnt",
                        verb_es="Tu solicitud de permiso ha sido rechazada",
                        verb_fr="Votre demande de congé a été rejetée",
                        icon="people-circle",
                        redirect=reverse("user-request-view") + f"?id={leave_request.id}",
                    )

                mail_thread = LeaveMailSendThread(request, leave_request, type="reject")
                mail_thread.start()

                return Response({"message": "Leave request rejected successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Leave request already rejected."}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)





class UserLeaveCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, format=None):
        leave_request = get_object_or_404(LeaveRequest, id=id)
        employee_id = leave_request.employee_id

        if employee_id.employee_user_id.id == request.user.id:
            current_date = date.today()
            if leave_request.status == "approved" and leave_request.end_date >= current_date:
                form = RejectForm()
                return Response({"form": form}, status=status.HTTP_200_OK)
            return Response({"error": "You can't cancel this leave request."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "You don't have the permission."}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request, id, format=None):
        leave_request = get_object_or_404(LeaveRequest, id=id)
        employee_id = leave_request.employee_id

        if employee_id.employee_user_id.id == request.user.id:
            current_date = date.today()
            if leave_request.status == "approved" and leave_request.end_date >= current_date:
                form = RejectForm(request.data)
                if form.is_valid():
                    leave_request.reject_reason = form.cleaned_data["reason"]
                    leave_request.status = "cancelled"
                    leave_request.save()
                    messages.success(request, ("Leave request cancelled successfully."))

                    mail_thread = LeaveMailSendThread(request, leave_request, type="cancel")
                    mail_thread.start()
                    return Response({"message": "Leave request cancelled successfully."}, status=status.HTTP_200_OK)
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "You can't cancel this leave request."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "You don't have the permission."}, status=status.HTTP_403_FORBIDDEN)


#########################################################################################################################################################
import logging

class OneRequestView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def get(self, request, id, format=None):
        try:
            leave_request = get_object_or_404(LeaveRequest, id=id)
            dashboard = request.GET.get("dashboard")
            current_date = date.today()

            context = {
                "leave_request": LeaveRequestSerializer(leave_request).data,
                "current_date": current_date,
                "dashboard": dashboard,
            }

            requests_ids_json = request.GET.get("instances_ids")
            if requests_ids_json:
                try:
                    requests_ids = json.loads(requests_ids_json)
                    previous_id, next_id = self.closest_numbers(requests_ids, id)
                    context["previous"] = previous_id
                    context["next"] = next_id
                    context["requests_ids"] = requests_ids_json
                except json.JSONDecodeError:
                    logging.error("Failed to decode JSON from instances_ids.")
                    return Response({"error": "Invalid JSON format for instances_ids."}, status=status.HTTP_400_BAD_REQUEST)

            return Response(context, status=status.HTTP_200_OK)
        
        except LeaveRequest.DoesNotExist:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(f"An unexpected error occurred: {str(e)}")
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    def closest_numbers(self, ids, current_id):
        ids.sort()
        previous_id = None
        next_id = None
        for index, id in enumerate(ids):
            if id == current_id:
                if index > 0:
                    previous_id = ids[index - 1]
                if index < len(ids) - 1:
                    next_id = ids[index + 1]
                break
        return previous_id, next_id




class UpdateCompensatoryLeaveView(APIView):
    """
    API view for updating a compensatory leave request.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id):
        """
        Handles POST requests to update a compensatory leave request.
        """
        instance = get_object_or_404(CompensatoryLeaveRequest, id=comp_id)
        form = CompensatoryLeaveForm(request.POST, instance=instance)
        if form.is_valid():
            comp_req = form.save()
            comp_req.requested_days = attendance_days(comp_req.employee_id, comp_req.attendance_id.all())
            comp_req.save()
            messages.success(request, _("Compensatory Leave updated."))
            return Response({"message": _("Compensatory Leave updated.")}, status=200)
        return Response({"errors": form.errors}, status=400)







class LeaveAssignOneAPI(APIView):
    def post(self, request, id, format=None):
        try:
            leave_type_id = id
            employee_ids = request.data.get("employee_ids", [])
            leave_type = LeaveType.objects.get(id=leave_type_id)
            form = LeaveOneAssignForm()
            form = choosesubordinates(request, form, "leave.add_availableleave")

            if not leave_type.is_compensatory_leave:
                for employee_id in employee_ids:
                    try:
                        employee = Employee.objects.get(id=employee_id)
                    except Employee.DoesNotExist:
                        messages.error(request, _("Employee with ID {} does not exist.").format(employee_id))
                        continue

                    if not AvailableLeave.objects.filter(
                        leave_type_id=leave_type, employee_id=employee
                    ).exists():
                        AvailableLeave(
                            leave_type_id=leave_type,
                            employee_id=employee,
                            available_days=leave_type.total_days,
                        ).save()
                        messages.success(request, _("Leave type assign is successful.."))
                        with contextlib.suppress(Exception):
                            notify.send(
                                request.user.employee_get,
                                recipient=employee.employee_user_id,
                                verb="New leave type is assigned to you",
                                verb_ar="تم تعيين نوع إجازة جديد لك",
                                verb_de="Ihnen wurde ein neuer Urlaubstyp zugewiesen",
                                verb_es="Se le ha asignado un nuevo tipo de permiso",
                                verb_fr="Un nouveau type de congé vous a été attribué",
                                icon="people-circle",
                                redirect=reverse("user-request-view"),
                            )
                    else:
                        messages.info(
                            request, _("Leave type is already assigned to the employee..")
                        )
            else:
                messages.info(
                    request, _("Compensatory leave type can't be assigned manually..")
                )

            return Response({
                "message": "Leave type assigned successfully."
            }, status=status.HTTP_200_OK)

        except LeaveType.DoesNotExist:
            return Response({
                "error": "LeaveType with ID {} does not exist.".format(leave_type_id)
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class LeaveAssignView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = filtersubordinates(
            request, AvailableLeave.objects.all(), "leave.view_availableleave"
        )
        previous_data = request.GET.urlencode() or "field=leave_type_id"
        field = request.GET.get("field", "leave_type_id")
        page_number = request.GET.get("page")

        # Paginate and group queryset by field
        page_obj = group_by_queryset(queryset.order_by("-id"), field, page_number)
        available_leave_ids = json.dumps(
            [instance.id for entry in page_obj for instance in entry["list"].object_list]
        )

        data = {
            "available_leaves": [AvailableLeaveSerializer(entry["list"].object_list, many=True).data for entry in page_obj],
            "previous_data": previous_data,
            "filter_dict": parse_qs(previous_data),
            "gp_fields": LeaveAssignReGroup.fields,
            "available_leave_ids": available_leave_ids,
        }

        return Response(data, status=status.HTTP_200_OK)


class AvailableLeaveSingleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, obj_id, format=None):
        try:
            get_data = request.GET.copy()
            get_data.pop("instances_ids", None)
            previous_data = get_data.urlencode()

            available_leave = get_object_or_404(AvailableLeave, id=obj_id)
            instance_ids = json.loads(request.GET.get("instances_ids", "[]"))
            previous_instance, next_instance = (
                self.closest_numbers(instance_ids, obj_id) if instance_ids else (None, None)
            )

            content = {
                "available_leave": AvailableLeaveSerializer(available_leave).data,
                "previous_instance": previous_instance,
                "next_instance": next_instance,
                "instance_ids_json": json.dumps(instance_ids),
                "pd": previous_data,
            }

            return Response(content, status=status.HTTP_200_OK)
        
        except AvailableLeave.DoesNotExist:
            return Response({
                "error": "AvailableLeave with ID {} does not exist.".format(obj_id)
            }, status=status.HTTP_404_NOT_FOUND)
        
        except json.JSONDecodeError:
            return Response({
                "error": "Invalid JSON in instances_ids parameter."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                "error": "An unexpected error occurred: {}".format(str(e))
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def closest_numbers(self, ids, current_id):
        ids.sort()
        previous_id = None
        next_id = None
        for index, id in enumerate(ids):
            if id == current_id:
                if index > 0:
                    previous_id = ids[index - 1]
                if index < len(ids) - 1:
                    next_id = ids[index + 1]
                break
        return previous_id, next_id


class LeaveAssignFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            queryset = AvailableLeave.objects.all()
            assign_form = AssignLeaveForm()
            queryset = filtersubordinates(request, queryset, "leave.view_availableleave")
            assigned_leave_filter = AssignedLeaveFilter(request.GET, queryset).qs
            previous_data = request.GET.urlencode()
            field = request.GET.get("field")
            page_number = request.GET.get("page")
            available_leaves = assigned_leave_filter.order_by("-id")

            if request.GET.get("sortby"):
                available_leaves = sortby(request, available_leaves, "sortby")
                available_leave_ids = [instance.id for instance in paginator_qry(available_leaves, None)]

            if field:
                page_obj = group_by_queryset(available_leaves, field, page_number)
                list_values = [entry["list"] for entry in page_obj]
                id_list = [instance.id for value in list_values for instance in value.object_list]
                available_leave_ids = id_list
            else:
                available_leave_ids = [instance.id for instance in paginator_qry(available_leaves, None)]
                page_obj = paginator_qry(available_leaves, page_number)

            data_dict = parse_qs(previous_data)
            get_key_instances(AvailableLeave, data_dict)

            context = {
                "available_leaves": AvailableLeaveSerializer(page_obj, many=True).data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "field": field,
                "assign_form": assign_form.data,
                "available_leave_ids": json.dumps(available_leave_ids),
            }

            return Response(context, status=status.HTTP_200_OK)

        except AvailableLeave.DoesNotExist:
            return Response({
                "error": "No available leaves found."
            }, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            return Response({
                "error": f"ValueError: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        except json.JSONDecodeError:
            return Response({
                "error": "Invalid JSON format in request parameters."
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "error": f"An unexpected error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




from django.db import transaction

class LeaveAssignAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = LeaveAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        leave_type_ids = serializer.validated_data["leave_type_ids"]
        employee_ids = serializer.validated_data["employee_ids"]

        if not leave_type_ids or not employee_ids:
            return Response(
                {"error": "Both leave_type_ids and employee_ids are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Fetch leave types and employees
            leave_types = LeaveType.objects.filter(id__in=leave_type_ids)
            employees = Employee.objects.filter(id__in=employee_ids)

            # Identify existing assignments
            existing_assignments = set(
                AvailableLeave.objects.filter(
                    leave_type_id__in=leave_type_ids, employee_id__in=employee_ids
                ).values_list("leave_type_id", "employee_id")
            )

            new_assignments = []
            success_messages = set()
            info_messages = set()

            for employee in employees:
                for leave_type in leave_types:
                    assignment_key = (leave_type.id, employee.id)
                    if assignment_key not in existing_assignments:
                        new_assignments.append(
                            AvailableLeave(
                                leave_type_id=leave_type,
                                employee_id=employee,
                                available_days=leave_type.total_days,
                            )
                        )
                        success_messages.add(employee.employee_user_id)
                    else:
                        info_messages.add(employee.employee_user_id)

            # Bulk create new assignments
            if new_assignments:
                with transaction.atomic():
                    AvailableLeave.objects.bulk_create(new_assignments)
                    for user_id in success_messages:
                        with contextlib.suppress(Exception):
                            notify.send(
                                request.user.employee_get,
                                recipient=user_id,
                                verb="New leave type is assigned to you",
                                verb_ar="تم تعيين نوع إجازة جديد لك",
                                verb_de="Dir wurde ein neuer Urlaubstyp zugewiesen",
                                verb_es="Se te ha asignado un nuevo tipo de permiso",
                                verb_fr="Un nouveau type de congé vous a été attribué",
                                icon="people-circle",
                                redirect=reverse("user-request-view"),
                            )

            # Create response
            return Response(
                {
                    "message": "Leave types assigned successfully.",
                    "success_count": len(success_messages),
                    "info_count": len(info_messages),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class AvailableLeaveUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id, format=None):
        try:
            leave_assign = get_object_or_404(AvailableLeave, id=id)
            form = AvailableLeaveUpdateForm(request.data, instance=leave_assign)
            if form.is_valid():
                available_leave = form.save()
                messages.success(request, ("Available leaves updated successfully..."))
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=available_leave.employee_id.employee_user_id,
                        verb=f"Your {available_leave.leave_type_id} leave type updated.",
                        verb_ar=f"تم تحديث نوع الإجازة {available_leave.leave_type_id} الخاص بك.",
                        verb_de=f"Ihr Urlaubstyp {available_leave.leave_type_id} wurde aktualisiert.",
                        verb_es=f"Se ha actualizado su tipo de permiso {available_leave.leave_type_id}.",
                        verb_fr=f"Votre type de congé {available_leave.leave_type_id} a été mis à jour.",
                        icon="people-circle",
                        redirect=reverse("user-request-view"),
                    )
                return Response({"message": "Available leaves updated successfully."}, status=status.HTTP_200_OK)
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except AvailableLeave.DoesNotExist:
            return Response({"error": "AvailableLeave not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ValueError as e:
            return Response({"error": f"Value error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class LeaveAssignDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, obj_id, format=None):
        try:
            available_leave = get_object_or_404(AvailableLeave, id=obj_id)
            available_leave.delete()
            messages.success(request, "Assigned leave successfully deleted.")
            response_message = {"message": "Assigned leave successfully deleted."}

        except AvailableLeave.DoesNotExist:
            return Response({"error": "Assigned leave not found."}, status=status.HTTP_404_NOT_FOUND)

        except ProtectedError:
            return Response({"error": "Related entries exist."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response_message, status=status.HTTP_200_OK)






class LeaveAssignBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, format=None):
        try:
            ids = request.data.get("ids", [])
            if not isinstance(ids, list):
                ids = json.loads(ids)

            count = 0
            for assigned_leave_id in ids:
                try:
                    assigned_leave = AvailableLeave.objects.get(id=assigned_leave_id)
                    assigned_leave.delete()
                    count += 1
                except AvailableLeave.DoesNotExist:
                    messages.error(request, "Assigned leave with ID {} not found.".format(assigned_leave_id))

            messages.success(request, "{} assigned leaves deleted successfully.".format(count))
            return JsonResponse({"message": "{} assigned leaves deleted successfully.".format(count)}, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import pandas as pd


class AssignLeaveTypeExcelView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request, format=None):
        try:
            columns = [
                "Employee Badge ID",
                "Leave Type",
            ]
            data_frame = pd.DataFrame(columns=columns)
            response = HttpResponse(content_type="application/ms-excel")
            response["Content-Disposition"] = (
                'attachment; filename="assign_leave_type_excel.xlsx"'
            )
            data_frame.to_excel(response, index=False)
            return response
        except Exception as exception:
            return Response({"error": str(exception)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


###############################################################################################################################################################

class AssignLeaveTypeImportView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, format=None):
        error_data = {
            "Employee Badge ID": [],
            "Leave Type": [],
            "Badge ID Error": [],
            "Leave Type Error": [],
            "Assigned Error": [],
            "Other Errors": [],
        }

        file = request.FILES.get("assign_leave_type_import")
        if not file:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        data_frame = pd.read_excel(file)
        assign_leave_dicts = data_frame.to_dict("records")

        employees = {emp.badge_id.lower(): emp for emp in Employee.objects.all() if emp.badge_id}
        leave_types = {lt.name.lower(): lt for lt in LeaveType.objects.all() if lt.name}
        available_leaves = {
            (al.leave_type_id.id, al.employee_id.id): al
            for al in AvailableLeave.objects.all()
        }

        assign_leave_list = []
        error_list = []

        for assign_leave in assign_leave_dicts:
            badge_id = assign_leave.get("Employee Badge ID", "").strip().lower()
            assign_leave_type = assign_leave.get("Leave Type", "").strip().lower()

            if not badge_id:
                assign_leave["Badge ID Error"] = "Employee Badge ID is missing."
                error_list.append(assign_leave)
                continue

            if not assign_leave_type:
                assign_leave["Leave Type Error"] = "Leave Type is missing."
                error_list.append(assign_leave)
                continue

            employee = employees.get(badge_id)
            leave_type = leave_types.get(assign_leave_type)

            errors = []
            if employee is None:
                errors.append("This badge id does not exist.")
            if leave_type is None:
                errors.append("This leave type does not exist.")
            if errors:
                assign_leave["Other Errors"] = " ".join(errors)
                error_list.append(assign_leave)
                continue

            if (leave_type.id, employee.id) in available_leaves:
                assign_leave["Assigned Error"] = "Leave type has already been assigned to the employee."
                error_list.append(assign_leave)
                continue

            assign_leave_list.append(
                AvailableLeave(
                    leave_type_id=leave_type,
                    employee_id=employee,
                    available_days=leave_type.total_days,
                )
            )

        if assign_leave_list:
            AvailableLeave.objects.bulk_create(assign_leave_list)

        if error_list:
            error_df = pd.DataFrame(error_list)
            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = 'attachment; filename="AssignLeaveError.xlsx"'
            error_df.to_excel(response, index=False)
            return response

        context = {
            "created_count": len(assign_leave_dicts) - len(error_list),
            "error_count": len(error_list),
            "model": "Assigned Leaves",
        }
        html = render_to_string("import_popup.html", context)
        return HttpResponse(html)



####################################



class AssignedLeavesExportView(APIView):
    """
    API view for exporting assigned leaves data.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    

    def post(self, request):
        """
        Handles POST requests to export assigned leaves data and return a JSON response.
        """
        try:
            # Extract selected fields from the request data
            selected_fields = request.data.get('selected_fields', [])

            # Filter and prepare the data for export
            export_filter = AssignedLeaveFilter(request.data, queryset=AvailableLeave.objects.all())
            data = export_filter.qs.values(*selected_fields)

            # Export the data to a file
            file_response = export_data(
                request=request,
                model=AvailableLeave,
                filter_class=AssignedLeaveFilter,
                form_class=AvailableLeaveColumnExportForm,
                file_name="Assign_Leave",  # Set your desired file name here
            )

            # Return JSON response containing the exported data
            return Response({
                "message": "Export successful",
                "data": list(data),
            }, headers=file_response.headers, status=200)  # Include file response headers
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class GetJobPositionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            department_id = request.GET.get("department")
            
            if not department_id:
                return Response({"error": "Department ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            form = RestrictLeaveForm()
            form.fields["job_position"].queryset = JobPosition.objects.filter(department_id=department_id)

            job_positions = form.fields["job_position"].queryset.values('id', 'job_position')
            return Response({"job_positions": list(job_positions)}, status=status.HTTP_200_OK)
        
        except JobPosition.DoesNotExist:
            return Response({"error": "No job positions found for the given department."}, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            return Response({"error": f"Value error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.template.loader import render_to_string
from django.utils.http import unquote



from django.db import DatabaseError

class RestrictCreationView(APIView):
    """
    API View to handle the creation of restricted days.
    """

    def post(self, request, format=None):
        try:
            # Create a new form or use the posted data to create a new restricted day
            form = RestrictLeaveForm(request.data)

            if form.is_valid():
                # Save the form and create a new restricted day
                form.save()
                # Return a success response with the created restricted day
                return Response({"message": "Restricted day created successfully."}, status=status.HTTP_201_CREATED)
            else:
                # If form is not valid, return the errors
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except DatabaseError as e:
            # Handle database errors
            return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            # Handle any unexpected exceptions
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, format=None):
        try:
            # Return the restricted days as a list
            restricted_days = RestrictLeave.objects.all()
            serializer = RestrictLeaveSerializer(restricted_days, many=True)
            return Response({"restricted_days": serializer.data}, status=status.HTTP_200_OK)
        
        except DatabaseError as e:
            # Handle database errors
            return Response({"error": f"Database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            # Handle any unexpected exceptions
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RestrictView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            queryset = RestrictLeave.objects.all().order_by('-id')
            previous_data = request.GET.urlencode()
            page_number = request.GET.get("page")
            page_obj = paginator_qry(queryset, page_number)
            restrictday_filter = RestrictLeaveFilter()
            serialized_restrictdays = RestrictLeaveSerializer(page_obj, many=True)
            context = {
                "restrictday": serialized_restrictdays.data,
                "form": restrictday_filter.form.data,
                "pd": previous_data,
            }
            return Response(context, status=status.HTTP_200_OK)
        
        except RestrictLeave.DoesNotExist:
            return Response({"error": "No restrict leaves found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ValueError as e:
            return Response({"error": f"Value error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class RestrictFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            queryset = RestrictLeave.objects.all()
            previous_data = request.GET.urlencode()
            restrictday_filter = RestrictLeaveFilter(request.GET, queryset).qs
            
            if request.GET.get("sortby"):
                restrictday_filter = sortby(request, restrictday_filter, "sortby")
            
            page_number = request.GET.get("page")
            page_obj = paginator_qry(restrictday_filter[::-1], page_number)
            data_dict = parse_qs(previous_data)
            get_key_instances(RestrictLeave, data_dict)
            
            serialized_restrictdays = RestrictLeaveSerializer(page_obj, many=True)

            context = {
                "restrictday": serialized_restrictdays.data,
                "pd": previous_data,
                "filter_dict": data_dict,
            }
            return Response(context, status=status.HTTP_200_OK)
        
        except RestrictLeave.DoesNotExist:
            return Response({"error": "No restrict leaves found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ValueError as e:
            return Response({"error": f"Value error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class RestrictUpdateView(APIView):
    """
    API View to update a restricted day.
    """

    permission_classes = [IsAuthenticated, ]

    def post(self, request, id, format=None):
        try:
            # Retrieve the RestrictLeave object based on the given ID
            restrictday = RestrictLeave.objects.get(id=id)

            # Initialize the form with the posted data and the existing instance
            form = RestrictLeaveForm(request.data, instance=restrictday)

            if form.is_valid():
                # Save the form and update the restricted day
                form.save()
                # Return a success response
                return Response(
                    {"message": "Restricted day updated successfully."},
                    status=status.HTTP_200_OK
                )
            else:
                # If the form is not valid, return the form errors
                return Response(
                    {"errors": form.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except ObjectDoesNotExist:
            # Handle the case where the restricted day with the provided ID does not exist
            return Response(
                {"error": "Restricted day not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            # Handle any unexpected errors
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class RestrictDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id, format=None):
        try:
            restrictday = get_object_or_404(RestrictLeave, id=id)
            restrictday.delete()
            response_message = {"message": "Restricted day deleted successfully."}
            return Response(response_message, status=status.HTTP_200_OK)
        
        except RestrictLeave.DoesNotExist:
            return Response({"error": "Restricted day not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ProtectedError:
            return Response({"error": "Related entries exist."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class RestrictDaysBulkDelete(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, format=None):
        restrict_day_ids = request.data.get("ids", [])
        if not restrict_day_ids:
            return Response(
                {"detail": ("No IDs provided.")},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            restrict_days = RestrictLeave.objects.filter(id__in=restrict_day_ids)
            count = restrict_days.count()
            restrict_days.delete()
            return Response(
                {"detail": ("{count} Leave restricted days deleted successfully.").format(count=count)},
                status=status.HTTP_200_OK
            )
        except (OverflowError, ValueError):
            return Response(
                {"detail": ("Restricted Days not found.")},
                status=status.HTTP_404_NOT_FOUND
            )
        except:
            return Response(
                {"detail": ("Something went wrong.")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RestrictDaySelect(APIView):
    """
    API View to handle retrieving restricted day IDs and the total count.
    Supports pagination for the list of restricted days.
    """

    def get(self, request, format=None):
        page_number = request.GET.get("page")

        # Handle the case when "all" is passed in the page_number parameter
        if page_number == "all":
            restrict_days = RestrictLeave.objects.all()
        else:
            # Pagination logic if you do not request all entries
            paginator = PageNumberPagination()
            paginator.page_size = 10  # Adjust the number of items per page as needed
            restrict_days = paginator.paginate_queryset(RestrictLeave.objects.all(), request)
            return paginator.get_paginated_response(self.get_restrict_day_ids(restrict_days))

        # If "all" is selected, return all restricted day IDs and the total count
        return Response(
            {"restrict_day_ids": self.get_restrict_day_ids(restrict_days), "total_count": len(restrict_days)},
            status=status.HTTP_200_OK
        )

    def get_restrict_day_ids(self, restrict_days):
        """
        Helper function to extract the IDs from the list of restrict days.
        """
        return [str(day.id) for day in restrict_days]

#######################################################################################################################################






from django.utils.translation import gettext as _




class UserLeaveRequest(APIView):
    """
    API view for creating user leave requests.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        """
        Handles POST requests to create a user leave request.
        """
        try:
            employee = request.user.employee_get
            leave_type = LeaveType.objects.filter(id=id).first()
            if not leave_type:
                return Response({"error": "Leave type not found."}, status=404)

            form = UserLeaveRequestForm(request.POST, request.FILES, employee=employee)
            
            # Validate start_date and end_date
            start_date_str = request.POST.get("start_date")
            end_date_str = request.POST.get("end_date")
            if not start_date_str or not end_date_str:
                return Response({"error": "Start date and end date are required."}, status=400)
            
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError as ve:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            start_date_breakdown = request.POST.get("start_date_breakdown")
            end_date_breakdown = request.POST.get("end_date_breakdown")

            available_leave = get_object_or_404(AvailableLeave, employee_id=employee, leave_type_id=leave_type)
            available_total_leave = available_leave.available_days + available_leave.carryforward_days
            requested_days = calculate_requested_days(start_date, end_date, start_date_breakdown, end_date_breakdown)
            requested_dates = leave_requested_dates(start_date, end_date)
            requested_dates = [date.date() for date in requested_dates]
            holidays = Holidays.objects.all()
            holiday_dates = holiday_dates_list(holidays)
            company_leaves = CompanyLeaves.objects.all()
            company_leave_dates = company_leave_dates_list(company_leaves, start_date)

            if leave_type.exclude_company_leave == "yes" and leave_type.exclude_holiday == "yes":
                total_leaves = list(set(holiday_dates + company_leave_dates))
                total_leave_count = sum(requested_date in total_leaves for requested_date in requested_dates)
                requested_days -= total_leave_count
            else:
                holiday_count = 0
                if leave_type.exclude_holiday == "yes":
                    for requested_date in requested_dates:
                        if requested_date in holiday_dates:
                            holiday_count += 1
                    requested_days -= holiday_count
                if leave_type.exclude_company_leave == "yes":
                    company_leave_count = sum(requested_date in company_leave_dates for requested_date in requested_dates)
                    requested_days -= company_leave_count

            overlapping_requests = LeaveRequest.objects.filter(
                employee_id=employee, start_date__lte=end_date, end_date__gte=start_date
            ).exclude(status__in=["cancelled", "rejected"])
            
            if overlapping_requests.exists():
                form.add_error(None, _("There is already a leave request for this date range."))
                return Response({"errors": form.errors}, status=400)
            
            if not leave_type.limit_leave or requested_days <= available_total_leave:
                if form.is_valid():
                    leave_request = form.save(commit=False)
                    leave_request.leave_type_id = leave_type
                    leave_request.employee_id = employee

                    if leave_request.leave_type_id.require_approval == "no":
                        if leave_request.requested_days > available_leave.available_days:
                            leave = leave_request.requested_days - available_leave.available_days
                            leave_request.approved_available_days = available_leave.available_days
                            available_leave.available_days = 0
                            available_leave.carryforward_days -= leave
                            leave_request.approved_carryforward_days = leave
                        else:
                            available_leave.available_days -= leave_request.requested_days
                            leave_request.approved_available_days = leave_request.requested_days
                        leave_request.status = "approved"
                        available_leave.save()
                    leave_request.created_by = employee
                    leave_request.save()

                    # Notify managers if multiple approvals required
                    if multiple_approvals_check(leave_request.id):
                        conditional_requests = multiple_approvals_check(leave_request.id)
                        managers = [manager.employee_user_id for manager in conditional_requests["managers"]]
                        notify.send(
                            request.user.employee_get,
                            recipient=managers[0],
                            verb="You have a new leave request to validate.",
                            verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                            verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                            verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                            verb_fr="Vous avez une nouvelle demande de congé à valider.",
                            icon="people-circle",
                            redirect=f"/leave/request-view?id={leave_request.id}",
                        )
                    mail_thread = LeaveMailSendThread(request, leave_request, type="request")
                    mail_thread.start()
                    messages.success(request, _("Leave request created successfully."))
                    
                    # Check if employee_work_info exists before accessing
                    if leave_request.employee_id.employee_work_info:
                        reporting_manager = leave_request.employee_id.employee_work_info.reporting_manager_id
                        if reporting_manager:
                            notify.send(
                                request.user.employee_get,
                                recipient=reporting_manager.employee_user_id,
                                verb="You have a new leave request to validate.",
                                verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                                verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                                verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                                verb_fr="Vous avez une nouvelle demande de congé à valider.",
                                icon="people-circle",
                                redirect=reverse("request-view") + f"?id={leave_request.id}",
                            )
                    return Response({"message": _("Leave request created successfully.")}, status=201)
                return Response({"errors": form.errors}, status=400)

            form.add_error(None, _("Employee doesn't have enough leave days."))
            return Response({"errors": form.errors}, status=400)
        except LeaveType.DoesNotExist:
            return Response({"error": "Leave type not found."}, status=404)
        except AvailableLeave.DoesNotExist:
            return Response({"error": "Available leave not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class UserLeaveRequestUpdate(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, format=None):
        leave_request = get_object_or_404(LeaveRequest, id=id)
        if request.user.employee_get != leave_request.employee_id or leave_request.status == "approved":
            return Response(
                {"detail": _("You can't update this leave request...")},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = LeaveRequestSerializer(leave_request)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, id, format=None):
        leave_request = get_object_or_404(LeaveRequest, id=id)
        if request.user.employee_get != leave_request.employee_id or leave_request.status == "approved":
            return Response(
                {"detail": _("You can't update this leave request...")},
                status=status.HTTP_403_FORBIDDEN
            )

        form = UserLeaveRequestForm(
            request.data, request.FILES, instance=leave_request, employee=leave_request.employee_id
        )

        if form.is_valid():
            leave_request = form.save(commit=False)
            start_date = leave_request.start_date
            end_date = leave_request.end_date
            start_date_breakdown = leave_request.start_date_breakdown
            end_date_breakdown = leave_request.end_date_breakdown
            leave_type = leave_request.leave_type_id
            employee = request.user.employee_get
            available_leave = get_object_or_404(AvailableLeave, employee_id=employee, leave_type_id=leave_type)
            available_total_leave = available_leave.available_days + available_leave.carryforward_days

            requested_days = calculate_requested_days(
                start_date, end_date, start_date_breakdown, end_date_breakdown
            )
            requested_dates = leave_requested_dates(start_date, end_date)
            holidays = Holidays.objects.all()
            holiday_dates = holiday_dates_list(holidays)
            company_leaves = CompanyLeaves.objects.all()
            company_leave_dates = company_leave_dates_list(company_leaves, start_date)

            if leave_type.exclude_company_leave == "yes" and leave_type.exclude_holiday == "yes":
                total_leaves = list(set(holiday_dates + company_leave_dates))
                total_leave_count = sum(
                    requested_date in total_leaves for requested_date in requested_dates
                )
                requested_days -= total_leave_count
            else:
                holiday_count = sum(
                    requested_date in holiday_dates for requested_date in requested_dates
                ) if leave_type.exclude_holiday == "yes" else 0
                requested_days -= holiday_count

                company_leave_count = sum(
                    requested_date in company_leave_dates for requested_date in requested_dates
                ) if leave_type.exclude_company_leave == "yes" else 0
                requested_days -= company_leave_count

            if requested_days <= available_total_leave:
                leave_request.save()
                messages.success(request, _("Leave request updated successfully."))
                return Response(
                    {"detail": _("Leave request updated successfully.")},
                    status=status.HTTP_200_OK
                )
            else:
                form.add_error(
                    None,
                    _("You don't have enough leave days to make the request."),
                )
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)






class UserLeaveRequestDelete(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id, format=None):
        previous_data = request.GET.urlencode()
        try:
            leave_request = get_object_or_404(LeaveRequest, id=id)
            if request.user.employee_get == leave_request.employee_id:
                leave_request.delete()
                return Response(
                    {"detail": _("Leave request deleted successfully.")},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": _("You can't delete this leave request...")},
                    status=status.HTTP_403_FORBIDDEN
                )
        except LeaveRequest.DoesNotExist:
            return Response(
                {"detail": _("User has no leave request.")},
                status=status.HTTP_404_NOT_FOUND
            )
        except ProtectedError:
            return Response(
                {"detail": _("Related entries exist.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not LeaveRequest.objects.filter(employee_id=request.user.employee_get).exists():
            return Response(
                {"detail": "<script>window.location.reload();</script>"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"redirect": f"/leave/user-request-filter?{previous_data}"},
                status=status.HTTP_200_OK
            )


class UserLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            employee = request.user.employee_get
            queryset = employee.available_leave.all()
            previous_data = request.GET.urlencode()
            page_number = request.GET.get("page")

            paginator = Paginator(queryset, 10)
            page_obj = paginator.get_page(page_number)

            if not queryset.exists():
                return Response(
                    {"detail": _("No leave types assigned.")},
                    status=status.HTTP_200_OK
                )

            data = {
                "user_leaves": AvailableLeaveSerializer(page_obj, many=True).data,
                "pd": previous_data,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": _("User is not an employee.")},
                status=status.HTTP_400_BAD_REQUEST
            )



class UserLeaveFilter(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            employee = request.user.employee_get
            queryset = employee.available_leave.all()
            previous_data = request.GET.urlencode()
            page_number = request.GET.get("page")
            assigned_leave_filter = AssignedLeaveFilter(request.GET, queryset).qs
            data_dict = parse_qs(previous_data)

            paginator = Paginator(assigned_leave_filter, 10)
            page_obj = paginator.get_page(page_number)

            data = {
                "user_leaves": AvailableLeaveSerializer(page_obj, many=True).data,
                "filter_dict": data_dict,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": _("User is not an employee or an error occurred.")},
                status=status.HTTP_400_BAD_REQUEST
            )



class UserLeaveRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            user = request.user.employee_get
            queryset = user.leaverequest_set.all()
            previous_data = request.GET.urlencode()
            page_number = request.GET.get("page")

            # Fetching leave requests
            leave_requests = queryset

            leave_requests_with_interview = []
            if apps.is_installed("recruitment"):
                for leave_request in leave_requests:
                    # Fetch interviews for the employee within the requested leave period
                    InterviewSchedule = get_horilla_model_class(
                        app_label="recruitment", model="interviewschedule"
                    )
                    interviews = InterviewSchedule.objects.filter(
                        employee_id=leave_request.employee_id,
                        interview_date__range=[
                            leave_request.start_date,
                            leave_request.end_date,
                        ],
                    )
                    if interviews:
                        # If interview exists then adding the leave request to the list
                        leave_requests_with_interview.append(leave_request)

            user_request_filter = UserLeaveRequestFilter(request.GET, queryset=queryset)
            page_obj = Paginator(user_request_filter.qs.order_by("-id"), 10).get_page(page_number)
            request_ids = json.dumps(
                list(page_obj.object_list.values_list("id", flat=True))
            )
            user_leave = AvailableLeave.objects.filter(employee_id=user.id).exclude(
                leave_type_id__is_compensatory_leave=True
            )
            if (
                LeaveGeneralSetting.objects.first()
                and LeaveGeneralSetting.objects.first().compensatory_leave
            ):
                user_leave = AvailableLeave.objects.filter(employee_id=user.id)
            current_date = date.today()

            data = {
                "leave_requests": LeaveRequestSerializer(page_obj, many=True).data,
                "form": user_request_filter.form.as_p(),  # Converting form to HTML
                "pd": previous_data,
                "current_date": current_date,
                "gp_fields": MyLeaveRequestReGroup.fields,  # Assuming this is defined somewhere
                "request_ids": request_ids,
                "user_leaves": AvailableLeaveSerializer(user_leave, many=True).data,
                "leave_requests_with_interview": LeaveRequestSerializer(leave_requests_with_interview, many=True).data,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            messages.error(request, _("User is not an employee."))
            return Response(
                {"detail": _("User is not an employee.")},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserLeaveRequestFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            user = request.user.employee_get
            queryset = user.leaverequest_set.all().order_by("-id")
            previous_data = request.GET.urlencode()
            page_number = request.GET.get("page")
            field = request.GET.get("field")

            # Fetching leave requests
            leave_requests = queryset

            leave_requests_with_interview = []
            if apps.is_installed("recruitment"):
                for leave_request in leave_requests:
                    # Fetch interviews for the employee within the requested leave period
                    InterviewSchedule = get_horilla_model_class(
                        app_label="recruitment", model="interviewschedule"
                    )
                    interviews = InterviewSchedule.objects.filter(
                        employee_id=leave_request.employee_id,
                        interview_date__range=[
                            leave_request.start_date,
                            leave_request.end_date,
                        ],
                    )
                    if interviews:
                        # If interview exists then adding the leave request to the list
                        leave_requests_with_interview.append(leave_request)

            queryset = sortby(request, queryset, "sortby")
            user_request_filter = UserLeaveRequestFilter(request.GET, queryset).qs
            template = "leave/user_leave/user_requests.html"

            if field != "" and field is not None:
                user_request_filter = group_by_queryset(
                    user_request_filter, field, request.GET.get("page"), "page"
                )
                list_values = [entry["list"] for entry in user_request_filter]
                id_list = []
                for value in list_values:
                    for instance in value.object_list:
                        id_list.append(instance.id)
                requests_ids = json.dumps(list(id_list))
                template = "leave/user_leave/group_by.html"
            else:
                user_request_filter = Paginator(user_request_filter, 10).get_page(request.GET.get("page"))
                requests_ids = json.dumps(
                    [instance.id for instance in user_request_filter.object_list]
                )

            data_dict = parse_qs(previous_data)
            get_key_instances(LeaveRequest, data_dict)
            if "status" in data_dict:
                status_list = data_dict["status"]
                if len(status_list) > 1:
                    data_dict["status"] = [status_list[-1]]

            user_leave = AvailableLeave.objects.filter(employee_id=user.id)

            context = {
                "leave_requests": LeaveRequestSerializer(user_request_filter, many=True).data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "field": field,
                "current_date": date.today(),
                "request_ids": requests_ids,
                "user_leaves": AvailableLeaveSerializer(user_leave, many=True).data,
                "leave_requests_with_interview": LeaveRequestSerializer(leave_requests_with_interview, many=True).data,
            }
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            messages.error(request, _("User is not an employee."))
            return Response(
                {"detail": _("User is not an employee.")},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserLeaveRequestOne(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, format=None):
        leave_request = get_object_or_404(LeaveRequest, id=id)
        try:
            requests_ids_json = request.GET.get("instances_ids")
            previous_id, next_id = None, None
            if requests_ids_json:
                requests_ids = json.loads(requests_ids_json)
                previous_id, next_id = closest_numbers(requests_ids, id)
            
            data = {
                "leave_request": LeaveRequestSerializer(leave_request).data,
                "instances_ids": requests_ids_json,
                "previous": previous_id,
                "next": next_id,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": _("User has no leave request.")},
                status=status.HTTP_400_BAD_REQUEST
            )


class EmployeeLeaveToday(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        today = date.today()
        leaves = []
        requests_ids = []

        leave_requests = LeaveRequest.objects.filter(status="approved")

        for leave_request in leave_requests:
            if today in leave_request.requested_dates():
                leaves.append(leave_request)
                requests_ids.append(leave_request.employee_id.id)

        data = {
            "leaves": LeaveRequestSerializer(leaves, many=True).data,
            "requests_ids": requests_ids,
        }
        return Response(data, status=status.HTTP_200_OK)



class OverallLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        labels = []
        data = []
        departments = Department.objects.all()
        leave_requests = LeaveRequestFilter(request.GET, LeaveRequest.objects.all()).qs

        for department in departments:
            count = leave_requests.filter(
                employee_id__employee_work_info__department_id=department.id
            ).count()
            if count:
                labels.append(department.department)
                data.append(count)

        response_data = {
            "labels": labels,
            "data": data
        }
        return Response(response_data, status=status.HTTP_200_OK)





class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            requests_ids = []
            today = date.today()

            leave_requests = LeaveRequest.objects.filter(start_date__month=today.month)
            requested = LeaveRequest.objects.filter(start_date__gte=today, status="requested")
            approved = LeaveRequest.objects.filter(status="approved", start_date__month=today.month)
            rejected = LeaveRequest.objects.filter(status="rejected", start_date__month=today.month)
            holidays = Holidays.objects.filter(start_date__gte=today)
            next_holiday = holidays.order_by("start_date").first() if holidays.exists() else None
            holidays_this_month = holidays.filter(
                start_date__month=today.month,
                start_date__year=today.year,
            ).order_by("start_date")[1:]

            leave_today = LeaveRequest.objects.filter(
                employee_id__is_active=True,
                status="approved",
                start_date__lte=today,
                end_date__gte=today,
            )

            for item in leave_today:
                requests_ids.append(item.id)

            data = {
                "leave_requests": LeaveRequestSerializer(leave_requests, many=True).data,
                "requested": LeaveRequestSerializer(requested, many=True).data,
                "approved": LeaveRequestSerializer(approved, many=True).data,
                "rejected": LeaveRequestSerializer(rejected, many=True).data,
                "next_holiday": HolidaysSerializer(next_holiday).data if next_holiday else None,
                "holidays": HolidaysSerializer(holidays_this_month, many=True).data,
                "leave_today_employees": LeaveRequestSerializer(leave_today, many=True).data,
                "dashboard": "dashboard",
                "today": today.strftime("%Y-%m-%d"),
                "first_day": today.replace(day=1).strftime("%Y-%m-%d"),
                "last_day": date(today.year, today.month, calendar.monthrange(today.year, today.month)[1]).strftime("%Y-%m-%d"),
                "requests_ids": requests_ids,
            }
            return Response(data, status=status.HTTP_200_OK)
        
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "LeaveRequest data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Holidays.DoesNotExist:
            return Response({"detail": "Holidays data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class EmployeeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            today = date.today()
            user = get_object_or_404(Employee, employee_user_id=request.user)

            leave_requests = LeaveRequest.objects.filter(employee_id=user)
            requested = leave_requests.filter(status="requested")
            approved = leave_requests.filter(status="approved")
            rejected = leave_requests.filter(status="rejected")

            holidays = Holidays.objects.filter(start_date__gte=today)
            next_holiday = holidays.order_by("start_date").first() if holidays.exists() else None
            holidays_this_month = holidays.filter(
                start_date__gte=today,
                start_date__month=today.month,
                start_date__year=today.year,
            ).order_by("start_date")[1:]
            leave_requests = leave_requests.filter(
                start_date__month=today.month, start_date__year=today.year
            )
            requests_ids = [request.id for request in leave_requests]

            data = {
                "leave_requests": LeaveRequestSerializer(leave_requests, many=True).data,
                "requested": LeaveRequestSerializer(requested, many=True).data,
                "approved": LeaveRequestSerializer(approved, many=True).data,
                "rejected": LeaveRequestSerializer(rejected, many=True).data,
                "next_holiday": HolidaysSerializer(next_holiday).data if next_holiday else None,
                "holidays": HolidaysSerializer(holidays_this_month, many=True).data,
                "dashboard": "dashboard",
                "requests_ids": requests_ids,
            }
            return Response(data, status=status.HTTP_200_OK)

        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "LeaveRequest data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Holidays.DoesNotExist:
            return Response({"detail": "Holidays data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class DashboardLeaveRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            user = get_object_or_404(Employee, employee_user_id=request.user)
            day = request.GET.get("date")
            if day:
                day = datetime.strptime(day, "%Y-%m")
                leave_requests = LeaveRequest.objects.filter(
                    employee_id=user, start_date__month=day.month, start_date__year=day.year
                )
                requests_ids = [req.id for req in leave_requests]
            else:
                leave_requests = []
                requests_ids = []

            data = {
                "leave_requests": LeaveRequestSerializer(leave_requests, many=True).data,
                "dashboard": "dashboard",
                "requests_ids": requests_ids,
            }
            return Response(data, status=status.HTTP_200_OK)
        
        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "LeaveRequest data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ValueError:
            return Response({"detail": "Invalid date format. Expected format is YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AvailableLeaveChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            user = get_object_or_404(Employee, employee_user_id=request.user)
            available_leaves = AvailableLeave.objects.filter(employee_id=user).exclude(available_days=0)

            leave_count = []
            labels = []

            for leave in available_leaves:
                leave_count.append(leave.available_days + leave.carryforward_days)
                labels.append(leave.leave_type_id.name)

            dataset = [
                {
                    "label": _("Total leaves available"),
                    "data": leave_count,
                },
            ]

            response = {
                "labels": labels,
                "dataset": dataset,
                "message": _("Oops!! No leaves available for you this month..."),
            }
            return Response(response, status=status.HTTP_200_OK)
        
        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except AvailableLeave.DoesNotExist:
            return Response({"detail": "Available leave data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class EmployeeLeaveChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            day = date.today()
            if request.GET.get("date"):
                day = request.GET.get("date")
                day = datetime.strptime(day, "%Y-%m")

            leave_requests = LeaveRequest.objects.filter(employee_id__is_active=True, status="approved")
            leave_requests = leave_requests.filter(start_date__month=day.month, start_date__year=day.year)
            leave_types = leave_requests.values_list("leave_type_id__name", flat=True)
            labels = []
            dataset = []
            for employee in leave_requests.filter(start_date__month=day.month, start_date__year=day.year):
                labels.append(employee.employee_id)

            for leave_type in list(set(leave_types)):
                dataset.append(
                    {
                        "label": leave_type,
                        "data": [],
                    }
                )

            labels = list(set(labels))
            total_leave_with_type = defaultdict(lambda: defaultdict(float))

            for label in labels:
                leaves = leave_requests.filter(employee_id=label, start_date__month=day.month, start_date__year=day.year)
                for leave in leaves:
                    total_leave_with_type[leave.leave_type_id.name][label] += round(leave.requested_days, 2)

            for data in dataset:
                dataset_label = data["label"]
                data["data"] = [total_leave_with_type[dataset_label][label] for label in labels]

            employee_label = [f"{employee.employee_first_name} {employee.employee_last_name}" for employee in list(set(labels))]
            
            response = {
                "labels": employee_label,
                "dataset": dataset,
                "message": _("No leave request this month"),
            }
            return Response(response, status=status.HTTP_200_OK)
        
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "LeaveRequest data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ValueError:
            return Response({"detail": "Invalid date format. Expected format is YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class DepartmentLeaveChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            day = date.today()
            if request.GET.get("date"):
                day = request.GET.get("date")
                day = datetime.strptime(day, "%Y-%m")

            departments = Department.objects.all()
            department_counts = {dep.department: 0 for dep in departments}
            leave_request = LeaveRequest.objects.filter(status="approved")
            leave_request = leave_request.filter(
                start_date__month=day.month, start_date__year=day.year
            )
            leave_dates = []
            labels = []
            for leave in leave_request:
                for leave_date in leave.requested_dates():
                    leave_dates.append(leave_date.strftime("%Y-%m-%d"))

                for dep in departments:
                    if dep == leave.employee_id.employee_work_info.department_id:
                        department_counts[dep.department] += leave.requested_days

            for department, count in department_counts.items():
                if count != 0:
                    labels.append(department)
            values = list(department_counts.values())
            values = [value for value in values if value != 0]
            dataset = [
                {
                    "label": "",
                    "data": values,
                },
            ]
            response = {
                "labels": labels,
                "dataset": dataset,
                "message": _("No leave requests for this month."),
            }
            return Response(response, status=status.HTTP_200_OK)
        
        except Department.DoesNotExist:
            return Response({"detail": "Department data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "LeaveRequest data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ValueError:
            return Response({"detail": "Invalid date format. Expected format is YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class LeaveTypeChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            day = date.today()
            if request.GET.get("date"):
                day = request.GET.get("date")
                day = datetime.strptime(day, "%Y-%m")

            leave_types = LeaveType.objects.all()
            leave_type_count = {types.name: 0 for types in leave_types}
            leave_request = LeaveRequest.objects.filter(status="approved")
            leave_request = leave_request.filter(start_date__month=day.month, start_date__year=day.year)

            for leave in leave_request:
                for lev in leave_types:
                    if lev == leave.leave_type_id:
                        leave_type_count[lev.name] += leave.requested_days

            labels = [leave_type for leave_type, count in leave_type_count.items() if count != 0]
            values = [count for count in leave_type_count.values() if count != 0]

            response = {
                "labels": labels,
                "dataset": [
                    {
                        "data": values,
                    },
                ],
                "message": _("No leave requests for any leave type this month."),
            }
            return Response(response, status=status.HTTP_200_OK)
        
        except LeaveType.DoesNotExist:
            return Response({"detail": "LeaveType data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except LeaveRequest.DoesNotExist:
            return Response({"detail": "LeaveRequest data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except ValueError:
            return Response({"detail": "Invalid date format. Expected format is YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class LeaveOverPeriodView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        week_dates = [start_of_week + timedelta(days=i) for i in range(6)]

        leave_in_week = []

        leave_request = LeaveRequest.objects.filter(status="approved")
        leave_dates = []
        for leave in leave_request:
            for leave_date in leave.requested_dates():
                leave_dates.append(leave_date)

        filtered_dates = [
            day
            for day in leave_dates
            if day.month == today.month and day.year == today.year
        ]
        for week_date in week_dates:
            days = []
            for filtered_date in filtered_dates:
                if filtered_date == week_date:
                    days.append(filtered_date)
            leave_in_week.append(len(days))

        dataset = [
            {
                "label": _("Leave Trends"),
                "data": leave_in_week,
            },
        ]

        labels = [week_date.strftime("%d-%m-%Y") for week_date in week_dates]

        response = {
            "labels": labels,
            "dataset": dataset,
        }
        return Response(response, status=status.HTTP_200_OK)



class LeaveRequestCreationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, type_id=None, emp_id=None):
        """
        Handles GET requests to return the leave request form template.
        """
        referer = request.META.get("HTTP_REFERER", "")
        referer_parts = [
            part for part in referer.split("/") if part != ""
        ] if referer else []
        
        if request.GET.urlencode().startswith("pd="):
            previous_data = unquote(request.GET.urlencode())[len("pd=") :]
        else:
            request_copy = request.GET.copy()
            if "confirm" in request_copy:
                request_copy.pop("confirm")
            previous_data = request_copy.urlencode()
        
        form = LeaveRequestCreationForm()
        if request:
            employee = request.user.employee_get
            if employee:
                available_leaves = employee.available_leave.all()
                assigned_leave_types = LeaveType.objects.filter(
                    id__in=available_leaves.values_list("leave_type_id", flat=True)
                )
                form.fields["leave_type_id"].queryset = assigned_leave_types
        if type_id and emp_id:
            initial_data = {
                "leave_type_id": type_id,
                "employee_id": emp_id,
            }
            form = LeaveRequestCreationForm(initial=initial_data)
        form = choosesubordinates(request, form, "leave.add_leaverequest")

        context = {
            "form": form,
            "pd": previous_data,
        }
        return render(request, "leave/leave_request/leave_request_form.html", context)

    def post(self, request, type_id=None, emp_id=None):
        """
        Handles POST requests to create a leave request.
        """
        referer = request.META.get("HTTP_REFERER", "")
        referer_parts = [
            part for part in referer.split("/") if part != ""
        ] if referer else []

        form = LeaveRequestCreationForm(request.POST, request.FILES)
        form = choosesubordinates(request, form, "leave.add_leaverequest")
        if form.is_valid():
            leave_request = form.save(commit=False)
            save = True

            # Check if the leave is being created for a back date
            if leave_request.start_date < datetime.now().date():
                user = request.user
                # Check if the user has permission to create backdated leave
                if not (user.is_admin or user.is_manager or user == leave_request.employee_id.employee_work_info.reporting_manager_id):
                    return Response({"error": _("You do not have permission to create a backdated leave request.")}, status=403)

            if leave_request.leave_type_id.require_approval == "no":
                employee_id = leave_request.employee_id
                leave_type_id = leave_request.leave_type_id
                available_leave = AvailableLeave.objects.filter(
                    leave_type_id=leave_type_id, employee_id=employee_id
                ).first()  # Use filter and first to handle multiple objects
                if not available_leave:
                    return Response({"error": _("No available leave found for the specified type and employee.")}, status=404)
                
                leave_request.created_by = request.user.employee_get
                leave_request.save()
                if leave_request.requested_days > available_leave.available_days:
                    leave = (
                        leave_request.requested_days - available_leave.available_days
                    )
                    leave_request.approved_available_days = (
                        available_leave.available_days
                    )
                    available_leave.available_days = 0
                    available_leave.carryforward_days = (
                        available_leave.carryforward_days - leave
                    )
                    leave_request.approved_carryforward_days = leave
                else:
                    available_leave.available_days = (
                        available_leave.available_days - leave_request.requested_days
                    )
                    leave_request.approved_available_days = leave_request.requested_days
                leave_request.status = "approved"
                available_leave.save()
            if save:
                leave_request.created_by = request.user.employee_get
                leave_request.save()

                if multiple_approvals_check(leave_request.id):
                    conditional_requests = multiple_approvals_check(leave_request.id)
                    managers = []
                    for manager in conditional_requests["managers"]:
                        managers.append(manager.employee_user_id)
                    with contextlib.suppress(Exception):
                        notify.send(
                            request.user.employee_get,
                            recipient=managers[0],
                            verb="You have a new leave request to validate.",
                            verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                            verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                            verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                            verb_fr="Vous avez une nouvelle demande de congé à valider.",
                            icon="people-circle",
                            redirect=f"/leave/request-view?id={leave_request.id}",
                        )

                mail_thread = LeaveMailSendThread(
                    request, leave_request, type="request"
                )
                mail_thread.start()
                messages.success(request, _("Leave request created successfully.."))
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        verb=f"New leave request created for {leave_request.employee_id}.",
                        verb_ar=f"تم إنشاء طلب إجازة جديد لـ {leave_request.employee_id}.",
                        verb_de=f"Neuer Urlaubsantrag erstellt für {leave_request.employee_id}.",
                        verb_es=f"Nueva solicitud de permiso creada para {leave_request.employee_id}.",
                        verb_fr=f"Nouvelle demande de congé créée pour {leave_request.employee_id}.",
                        icon="people-circle",
                        redirect=reverse("request-view") + f"?id={leave_request.id}",
                    )
                form = LeaveRequestCreationForm()
                if referer_parts and referer_parts[-2] == "employee-view":
                    return Response({"success": True, "script": "<script>window.location.reload();</script>"})

            leave_requests = LeaveRequest.objects.all()
            if len(leave_requests) == 1:
                return Response({"success": True, "script": "<script>window.location.reload()</script>"})

        context = {
            "form": form,
            "pd": request.GET.urlencode() if request.GET.urlencode().startswith("pd=") else "",
        }
        return render(request, "leave/leave_request/leave_request_form.html", context)

class LeaveAllocationRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            employee = request.user.employee_get
            queryset = LeaveAllocationRequest.objects.all().order_by("-id")
            queryset = LeaveAllocationRequestFilter(request.GET, queryset).qs
            queryset = filtersubordinates(request, queryset, "leave.view_leaveallocationrequest")
            page_number = request.GET.get("page")
            paginator = Paginator(queryset, 10)
            leave_allocation_requests = paginator.get_page(page_number)
            requests_ids = json.dumps(
                list(leave_allocation_requests.object_list.values_list("id", flat=True))
            )

            my_leave_allocation_requests = LeaveAllocationRequest.objects.filter(
                employee_id=employee.id
            ).order_by("-id")
            my_leave_allocation_requests = LeaveAllocationRequestFilter(
                request.GET, my_leave_allocation_requests
            ).qs
            my_page_number = request.GET.get("m_page")
            my_paginator = Paginator(my_leave_allocation_requests, 10)
            my_leave_allocation_requests = my_paginator.get_page(my_page_number)
            my_requests_ids = json.dumps(
                list(my_leave_allocation_requests.object_list.values_list("id", flat=True))
            )
            leave_allocation_request_filter = LeaveAllocationRequestFilter()
            previous_data = request.GET.urlencode()
            data_dict = parse_qs(previous_data)
            data_dict = get_key_instances(LeaveAllocationRequest, data_dict)

            data = {
                "leave_allocation_requests": LeaveAllocationRequestSerializer(leave_allocation_requests, many=True).data,
                "my_leave_allocation_requests": LeaveAllocationRequestSerializer(my_leave_allocation_requests, many=True).data,
                "pd": previous_data,
                "form": leave_allocation_request_filter.form.as_p(),
                "filter_dict": data_dict,
                "gp_fields": LeaveAllocationRequestReGroup.fields,
                "requests_ids": requests_ids,
                "my_requests_ids": my_requests_ids,
            }
            return Response(data, status=status.HTTP_200_OK)
        
        except LeaveAllocationRequest.DoesNotExist:
            return Response({"detail": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except KeyError as e:
            return Response({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON format for instances_ids."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class LeaveAllocationRequestSingleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, req_id, format=None):
        try:
            my_request = False
            if request.GET.get("my_request") == "True":
                my_request = True
            requests_ids_json = request.GET.get("instances_ids")
            previous_id, next_id = None, None
            if requests_ids_json:
                requests_ids = json.loads(requests_ids_json)
                previous_id, next_id = closest_numbers(requests_ids, req_id)
            
            leave_allocation_request = get_object_or_404(LeaveAllocationRequest, id=req_id)
            
            data = {
                "leave_allocation_request": LeaveAllocationRequestSerializer(leave_allocation_request).data,
                "my_request": my_request,
                "instances_ids": requests_ids_json,
                "previous": previous_id,
                "next": next_id,
                "dashboard": request.GET.get("dashboard"),
            }
            return Response(data, status=status.HTTP_200_OK)
        
        except LeaveAllocationRequest.DoesNotExist:
            return Response({"detail": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except KeyError as e:
            return Response({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON format for instances_ids."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class LeaveAllocationRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            employee = request.user.employee_get
            form = LeaveAllocationRequestForm(initial={"employee_id": employee})
            form = choosesubordinates(request, form, "leave.add_leaveallocationrequest")
            form.fields["employee_id"].queryset = form.fields[
                "employee_id"
            ].queryset | Employee.objects.filter(employee_user_id=request.user)
            data = {
                "form": form.as_p(), 
            }
            return Response(data, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        except KeyError as e:
            return Response({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, format=None):
        try:
            employee = request.user.employee_get
            form = LeaveAllocationRequestForm(request.data, request.FILES)
            if form.is_valid():
                leave_allocation_request = form.save(commit=False)
                leave_allocation_request.skip_history = False
                leave_allocation_request.save()
                messages.success(request, _("New Leave allocation request is created"))
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_allocation_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        verb=f"New leave allocation request created for {leave_allocation_request.employee_id}.",
                        verb_ar=f"تم إنشاء طلب تخصيص إجازة جديد لـ {leave_allocation_request.employee_id}.",
                        verb_de=f"Neue Anfrage zur Urlaubszuweisung erstellt für {leave_allocation_request.employee_id}.",
                        verb_es=f"Nueva solicitud de asignación de permisos creada para {leave_allocation_request.employee_id}.",
                        verb_fr=f"Nouvelle demande d'allocation de congé créée pour {leave_allocation_request.employee_id}.",
                        icon="people-circle",
                        redirect=reverse("leave-allocation-request-view") + f"?id={leave_allocation_request.id}",
                    )
                return Response({"detail": _("New Leave allocation request is created")}, status=status.HTTP_201_CREATED)
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        except KeyError as e:
            return Response({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class LeaveAllocationRequestFilterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            field = request.GET.get("field")
            employee = request.user.employee_get
            page_number = request.GET.get("page")
            my_page_number = request.GET.get("m_page")
            previous_data = request.GET.urlencode()
            
            leave_allocation_requests_filtered = LeaveAllocationRequestFilter(request.GET).qs.order_by("-id")
            my_leave_allocation_requests_filtered = LeaveAllocationRequest.objects.filter(employee_id=employee.id).order_by("-id")
            my_leave_allocation_requests_filtered = LeaveAllocationRequestFilter(request.GET, my_leave_allocation_requests_filtered).qs
            leave_allocation_requests_filtered = filtersubordinates(request, leave_allocation_requests_filtered, "leave.view_leaveallocationrequest")

            if request.GET.get("sortby"):
                leave_allocation_requests_filtered = sortby(request, leave_allocation_requests_filtered, "sortby")

            if field:
                leave_allocation_requests = group_by_queryset(leave_allocation_requests_filtered, field, page_number, "page")
                my_leave_allocation_requests = group_by_queryset(my_leave_allocation_requests_filtered, field, my_page_number, "m_page")

                list_values = [entry["list"] for entry in leave_allocation_requests]
                id_list = [instance.id for value in list_values for instance in value.object_list]
                requests_ids = json.dumps(list(id_list))

                list_values = [entry["list"] for entry in my_leave_allocation_requests]
                id_list = [instance.id for value in list_values for instance in value.object_list]
                my_requests_ids = json.dumps(list(id_list))
            else:
                leave_allocation_requests = Paginator(leave_allocation_requests_filtered, 10).get_page(page_number)
                my_leave_allocation_requests = Paginator(my_leave_allocation_requests_filtered, 10).get_page(my_page_number)
                requests_ids = json.dumps(list(leave_allocation_requests.object_list.values_list("id", flat=True)))
                my_requests_ids = json.dumps(list(my_leave_allocation_requests.object_list.values_list("id", flat=True)))

            data_dict = parse_qs(previous_data)
            data_dict = get_key_instances(LeaveAllocationRequest, data_dict)
            data_dict.pop("m_page", None)

            data = {
                "leave_allocation_requests": LeaveAllocationRequestSerializer(leave_allocation_requests, many=True).data,
                "my_leave_allocation_requests": LeaveAllocationRequestSerializer(my_leave_allocation_requests, many=True).data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "field": field,
                "requests_ids": requests_ids,
                "my_requests_ids": my_requests_ids,
            }
            return Response(data, status=status.HTTP_200_OK)
        
        except LeaveAllocationRequest.DoesNotExist:
            return Response({"detail": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except KeyError as e:
            return Response({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except json.JSONDecodeError:
            return Response({"detail": "Invalid JSON format for instances_ids."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class LeaveAllocationRequestUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, req_id, format=None):
        try:
            leave_allocation_request = get_object_or_404(LeaveAllocationRequest, id=req_id)
            if leave_allocation_request.status != "approved":
                form = LeaveAllocationRequestForm(request.data, request.FILES, instance=leave_allocation_request)
                if form.is_valid():
                    leave_allocation_request = form.save(commit=False)
                    leave_allocation_request.skip_history = False
                    leave_allocation_request.save()
                    messages.success(request, _("Leave allocation request is updated successfully."))
                    with contextlib.suppress(Exception):
                        notify.send(
                            request.user.employee_get,
                            recipient=leave_allocation_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            verb=f"Leave allocation request updated for {leave_allocation_request.employee_id}.",
                            verb_ar=f"تم تحديث طلب تخصيص الإجازة لـ {leave_allocation_request.employee_id}.",
                            verb_de=f"Urlaubszuteilungsanforderung aktualisiert für {leave_allocation_request.employee_id}.",
                            verb_es=f"Solicitud de asignación de licencia actualizada para {leave_allocation_request.employee_id}.",
                            verb_fr=f"Demande d'allocation de congé mise à jour pour {leave_allocation_request.employee_id}.",
                            icon="people-circle",
                            redirect=reverse("leave-allocation-request-view") + f"?id={leave_allocation_request.id}",
                        )
                    return Response({"detail": _("Leave allocation request is updated successfully.")}, status=status.HTTP_200_OK)
                else:
                    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                messages.error(request, _("You can't update this request..."))
                return Response({"detail": _("You can't update this request...")}, status=status.HTTP_400_BAD_REQUEST)
        
        except LeaveAllocationRequest.DoesNotExist:
            return Response({"detail": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except KeyError as e:
            return Response({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

############################################################################################################################################################################
import logging


logger = logging.getLogger(__name__)

class LeaveAllocationRequestApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, req_id):
        try:
            leave_allocation_request = get_object_or_404(LeaveAllocationRequest, id=req_id)
            logger.info(f"Leave allocation request found with id: {req_id}")
            if leave_allocation_request.status == "requested":
                employee = leave_allocation_request.employee_id
                available_leave = employee.available_leave.filter(
                    leave_type_id=leave_allocation_request.leave_type_id
                ).first()
                if available_leave:
                    logger.info(f"Found available leave for employee: {employee.id}")
                    available_leave.available_days += leave_allocation_request.requested_days
                else:
                    logger.info(f"No available leave found, creating new available leave entry for employee: {employee.id}")
                    available_leave = AvailableLeave(
                        leave_type_id=leave_allocation_request.leave_type_id,
                        employee_id=employee,
                        available_days=leave_allocation_request.requested_days
                    )
                available_leave.save()
                leave_allocation_request.status = "approved"
                leave_allocation_request.save()
                logger.info(f"Leave allocation request approved for employee: {employee.id}")
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=leave_allocation_request.employee_id.employee_user_id,
                        verb="Your leave allocation request has been approved",
                        verb_ar="تمت الموافقة على طلب تخصيص إجازتك",
                        verb_de="Ihr Antrag auf Urlaubszuweisung wurde genehmigt",
                        verb_es="Se ha aprobado su solicitud de asignación de vacaciones",
                        verb_fr="Votre demande d'allocation de congé a été approuvée",
                        icon="people-circle",
                        redirect=reverse("leave-allocation-request-view") + f"?id={leave_allocation_request.id}",
                    )
                return Response({"detail": _("Leave allocation request approved successfully")}, status=status.HTTP_200_OK)
            else:
                logger.error(f"Leave allocation request with id: {req_id} cannot be approved because its status is: {leave_allocation_request.status}")
                return Response({"detail": _("The leave allocation request can't be approved")}, status=status.HTTP_400_BAD_REQUEST)
        
        except LeaveAllocationRequest.DoesNotExist:
            logger.error(f"Leave allocation request with id: {req_id} not found")
            return Response({"detail": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except AvailableLeave.DoesNotExist:
            logger.error(f"Available leave data for leave type id: {leave_allocation_request.leave_type_id} not found")
            return Response({"detail": "Available leave data not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except KeyError as e:
            logger.error(f"Missing key: {str(e)}")
            return Response({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        



class LeaveAllocationRequestRejectAPIView(APIView):
    """
    API view to reject a leave allocation request.
    """

    def post(self, request, req_id):
        """
        Reject the leave allocation request.

        Parameters:
        request (HttpRequest): The HTTP request object.
        req_id (int): The leave allocation request ID.
        """
        leave_allocation_request = get_object_or_404(LeaveAllocationRequest, id=req_id)

        if leave_allocation_request.status in ["requested", "approved"]:
            # Deserialize the request data
            serializer = LeaveAllocationRequestRejectSerializer(data=request.data)

            if serializer.is_valid():
                leave_allocation_request.reject_reason = serializer.validated_data["reason"]

                if leave_allocation_request.status == "approved":
                    leave_type = leave_allocation_request.leave_type_id
                    requested_days = leave_allocation_request.requested_days
                    available_leave = AvailableLeave.objects.filter(
                        leave_type_id=leave_type,
                        employee_id=leave_allocation_request.employee_id,
                    ).first()

                    if available_leave:
                        available_leave.available_days = max(
                            0, available_leave.available_days - requested_days
                        )
                        available_leave.save()

                leave_allocation_request.status = "rejected"
                leave_allocation_request.save()

                # Return success response
                return Response(
                    {"message": _("Leave allocation request rejected successfully")},
                    status=status.HTTP_200_OK,
                )

            # If serializer is invalid, return error response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        else:
            # Handle case where the leave allocation request cannot be rejected
            return Response(
                {"message": _("The leave allocation request can't be rejected")},
                status=status.HTTP_400_BAD_REQUEST,
            )




class LeaveAllocationRequestDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, req_id):
        """
        Function used to delete a leave allocation request.
        Args:
            req_id: leave allocation request id
        """
        try:
            leave_allocation_request = get_object_or_404(LeaveAllocationRequest, id=req_id)

            if leave_allocation_request.status != "approved":
                leave_allocation_request.delete()
                return Response({"detail": _("Leave allocation request deleted successfully.")}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": _("Approved request can't be deleted.")}, status=status.HTTP_400_BAD_REQUEST)
        
        except LeaveAllocationRequest.DoesNotExist:
            return Response({"detail": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except OverflowError:
            return Response({"detail": "Overflow error occurred while processing the request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except ProtectedError:
            return Response({"detail": _("Related entries exist, unable to delete.")}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.core.exceptions import PermissionDenied

class AssignedLeaveSelectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page_number = request.GET.get("page")

            if page_number == "all":
                if request.user.has_perm("leave.view_availableleave"):
                    employees = AvailableLeave.objects.all()
                else:
                    employees = AvailableLeave.objects.filter(
                        employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                    )
            else:
                employees = AvailableLeave.objects.none()

            employee_ids = [str(emp.id) for emp in employees]
            total_count = employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}

            return JsonResponse(context, safe=False)

        except AvailableLeave.DoesNotExist:
            return JsonResponse({"detail": "Available leave data not found."}, status=status.HTTP_404_NOT_FOUND)

        except PermissionDenied:
            return JsonResponse({"detail": "You do not have permission to view this data."}, status=status.HTTP_403_FORBIDDEN)

        except KeyError as e:
            return JsonResponse({"detail": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AssignedLeaveSelectFilterAPI(APIView):
    """
    API view to filter and select assigned leave data based on user permissions.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles the GET request to filter assigned leave data.
        """

        page_number = request.GET.get("page")
        filtered = request.GET.get("filter")
        filters = json.loads(filtered) if filtered else {}

        employee_name = filters.get("employee_name")  # New filter for employee name

        if page_number == "all":
            # Check user permissions and apply filtering logic
            if request.user.has_perm("leave.view_availableleave"):
                # Apply the filter to the queryset if employee_name is provided
                employee_filter = AssignedLeaveFilter(
                    filters, queryset=AvailableLeave.objects.all()
                )
            else:
                employee_filter = AssignedLeaveFilter(
                    filters,
                    queryset=AvailableLeave.objects.filter(
                        employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                    ),
                )

            # Apply additional filter for employee_name if provided
            if employee_name:
                filtered_employees = employee_filter.qs.filter(
                    employee_id__employee_first_name__icontains=employee_name
                )
            else:
                filtered_employees = employee_filter.qs

            employee_ids = [str(emp.id) for emp in filtered_employees]
            total_count = filtered_employees.count()

            # Return the filtered data as a JSON response
            context = {"employee_ids": employee_ids, "total_count": total_count}
            return Response(context, status=200)

        # In case of an invalid page_number or other conditions, return an error
        return Response(
            {"message": "Invalid page number or filter parameters."},
            status=400,
        )



###############################################################################################################################################################
class LeaveRequestBulkDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        This method is used to delete bulk of leave requests.
        """
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"message": "No valid IDs provided."}, status=400)

        failed_deletions = []

        for leave_request_id in ids:
            try:
                leave_request = LeaveRequest.objects.get(id=leave_request_id)
                employee = leave_request.employee_id
                if leave_request.status == "requested":
                    leave_request.delete()
                    messages.success(
                        request,
                        _("{}'s leave request deleted.".format(employee)),
                    )
                else:
                    failed_deletions.append(str(employee))
                    messages.error(
                        request,
                        _("{}'s leave request cannot be deleted.".format(employee)),
                    )
            except LeaveRequest.DoesNotExist:
                failed_deletions.append(str(leave_request_id))
                messages.error(request, _("Leave request not found."))

        if failed_deletions:
            return Response({
                "message": "Some leave requests could not be deleted.",
                "failed_ids": failed_deletions
            }, status=400)

        return Response({"message": " leave requests deleted successfully."}, status=200)



class LeaveRequestSelectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page_number = request.GET.get("page")

        if page_number == "all":
            if request.user.has_perm("leave.view_leaverequest"):
                employees = LeaveRequest.objects.all()
            else:
                employees = LeaveRequest.objects.filter(
                    employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                )

            employee_ids = [str(emp.id) for emp in employees]
            total_count = employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}

            return JsonResponse(context, safe=False)

        return Response({"detail": "Invalid page number or missing filters."}, status=status.HTTP_400_BAD_REQUEST)




class LeaveRequestSelectFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page_number = request.GET.get("page")
        filtered = request.GET.get("filter")
        filters = json.loads(filtered) if filtered else {}

        if page_number == "all":
            if request.user.has_perm("leave.view_leaverequest"):
                employee_filter = LeaveRequestFilter(
                    filters, queryset=LeaveRequest.objects.all()
                )
            else:
                employee_filter = LeaveRequestFilter(
                    filters,
                    queryset=LeaveRequest.objects.filter(
                        employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                    ),
                )

            # Get the filtered queryset
            filtered_employees = employee_filter.qs

            employee_ids = [str(emp.id) for emp in filtered_employees]
            total_count = filtered_employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}

            return JsonResponse(context, safe=False)

        return Response({"detail": "Invalid page number or missing filters."}, status=status.HTTP_400_BAD_REQUEST)




class UserRequestBulkDeleteAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        This method is used to delete bulk of leaves requests
        """
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            return JsonResponse({"message": "Invalid data format. 'ids' should be a non-empty list."}, status=400)
        
        for leave_request_id in ids:
            try:
                leave_request = LeaveRequest.objects.get(id=leave_request_id)
                status = leave_request.status
                if leave_request.status == "requested":
                    leave_request.delete()
                    messages.success(
                        request,
                        _("Leave request deleted."),
                    )
                else:
                    messages.error(
                        request,
                        _("You cannot delete leave request with status {}.".format(status)),
                    )
            except LeaveRequest.DoesNotExist:
                messages.error(request, _("Leave request not found."))
            except Exception as e:
                messages.error(request, _("An error occurred: {}".format(str(e))))

        return JsonResponse({"message": "Success"})


class UserRequestSelectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page_number = request.GET.get("page")
        user = request.user.employee_get

        if page_number == "all":
            employees = LeaveRequest.objects.filter(employee_id=user)
            employee_ids = [str(emp.id) for emp in employees]
            total_count = employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}

            return JsonResponse(context, safe=False)

        return Response({"detail": "Invalid page number or missing filters."}, status=status.HTTP_400_BAD_REQUEST)





class UserRequestSelectFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page_number = request.GET.get("page")
        filtered = request.GET.get("filter")
        filters = json.loads(filtered) if filtered else {}
        user = request.user.employee_get

        if page_number == "all":
            employee_filter = UserLeaveRequestFilter(
                filters, queryset=LeaveRequest.objects.filter(employee_id=user)
            )

            # Get the filtered queryset
            filtered_employees = employee_filter.qs

            employee_ids = [str(emp.id) for emp in filtered_employees]
            total_count = filtered_employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}

            return JsonResponse(context)

        return Response({"detail": "Invalid page number or missing filters."}, status=status.HTTP_400_BAD_REQUEST)




class EmployeeAvailableLeaveCountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leave_type_id = request.GET.get("leave_type_id")
        start_date = request.GET.get("start_date")
        
        try:
            start_date_format = datetime.strptime(start_date, "%Y-%m-%d").date()
        except:
            leave_type_id = None
            
        hx_target = request.META.get("HTTP_HX_TARGET", None)
        employee_id = (
            request.GET.getlist("employee_id")[0]
            if request.GET.getlist("employee_id")
            else None
        )
        
        available_leave = (
            AvailableLeave.objects.filter(
                leave_type_id=leave_type_id, employee_id=employee_id
            ).first()
            if leave_type_id and employee_id
            else None
        )
        
        total_leave_days = available_leave.total_leave_days if available_leave else 0
        forcated_days = 0

        if (
            available_leave
            and available_leave.leave_type_id.leave_type_next_reset_date()
            and available_leave
            and start_date_format
            >= available_leave.leave_type_id.leave_type_next_reset_date()
        ):
            forcated_days = available_leave.forcasted_leaves(start_date)
            total_leave_days = (
                available_leave.leave_type_id.carryforward_max
                if available_leave.leave_type_id.carryforward_type
                in ["carryforward", "carryforward expire"]
                and available_leave.leave_type_id.carryforward_max < total_leave_days
                else total_leave_days
            )
            if available_leave.leave_type_id.carryforward_type == "no carryforward":
                total_leave_days = 0
            total_leave_days += forcated_days

        context = {
            "hx_target": hx_target,
            "leave_type_id": leave_type_id,
            "available_leave": available_leave,
            "total_leave_days": total_leave_days,
            "forcated_days": forcated_days,
        }
        
        return Response(context, status=status.HTTP_200_OK)




class CutAvailableLeaveAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, instance_id):
        """
        This method is used to create the penalties
        """
        try:
            instance = get_object_or_404(LeaveRequest, id=instance_id)
            data = {
                "deduct_from_carry_forward": request.data.get("deduct_from_carry_forward"),
                "leave_type_id": request.data.get("leave_type_id"),
                "minus_leaves": request.data.get("minus_leaves"),
                "penalty_amount": request.data.get("penalty_amount")
            }
            form = PenaltyAccountForm(data)

            if form.is_valid():
                penalty_instance = form.save(commit=False)
                penalty_instance.leave_request_id = instance
                penalty_instance.employee_id = instance.employee_id
                penalty_instance.save()
                messages.success(request, "Penalty/Fine added")
                return JsonResponse({"message": "Penalty/Fine added successfully."})
            else:
                return JsonResponse({"errors": form.errors}, status=400)
        except LeaveRequest.DoesNotExist:
            return JsonResponse({"error": "Leave request not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)




class CreateLeaveRequestCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, leave_id):
        try:
            leave = get_object_or_404(LeaveRequest, id=leave_id)
            emp = request.user.employee_get
            data = request.data.copy()  # Copy the request data to ensure it's mutable
            data['employee_id'] = emp.id
            data['request_id'] = leave.id

            form = LeaverequestcommentForm(data)

            if form.is_valid():
                form.instance.employee_id = emp
                form.instance.request_id = leave
                form.save()

                # Fetch the comments to return them in the response
                comments = LeaverequestComment.objects.filter(request_id=leave_id).order_by("-created_at")
                no_comments = not comments.exists()
                messages.success(request, _("Comment added successfully!"))

                # Notification logic
                work_info = EmployeeWorkInformation.objects.filter(employee_id=leave.employee_id)
                if work_info.exists():
                    if leave.employee_id.employee_work_info.reporting_manager_id:
                        if request.user.employee_get.id == leave.employee_id.id:
                            rec = leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                            notify.send(
                                request.user.employee_get,
                                recipient=rec,
                                verb=f"{leave.employee_id}'s leave request has received a comment.",
                                redirect=reverse("request-view") + f"?id={leave.id}",
                                icon="chatbox-ellipses"
                            )
                        elif request.user.employee_get.id == leave.employee_id.employee_work_info.reporting_manager_id.id:
                            rec = leave.employee_id.employee_user_id
                            notify.send(
                                request.user.employee_get,
                                recipient=rec,
                                verb="Your leave request has received a comment.",
                                redirect=reverse("user-request-view") + f"?id={leave.id}",
                                icon="chatbox-ellipses"
                            )
                        else:
                            rec = [
                                leave.employee_id.employee_user_id,
                                leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            ]
                            notify.send(
                                request.user.employee_get,
                                recipient=rec,
                                verb=f"{leave.employee_id}'s leave request has received a comment.",
                                redirect=reverse("request-view") + f"?id={leave.id}",
                                icon="chatbox-ellipses"
                            )
                    else:
                        rec = leave.employee_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb="Your leave request has received a comment.",
                            redirect=reverse("user-request-view") + f"?id={leave.id}",
                            icon="chatbox-ellipses"
                        )

                return Response({"detail": "Comment added successfully!"}, status=status.HTTP_201_CREATED)

            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except LeaveRequest.DoesNotExist:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ViewLeaveRequestCommentAPI(APIView):
    permission_classes = [IsAuthenticated]
   

    def get(self, request, leave_id):
        """
        Retrieve and display comments for a leave request
        """
        try:
            comments = LeaverequestComment.objects.filter(request_id=leave_id).order_by("-created_at")
            no_comments = not comments.exists()
            serialized_comments = LeaverequestCommentSerializer(comments, many=True)

            return Response({
                "comments": serialized_comments.data,
                "no_comments": no_comments,
                "request_id": leave_id,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, leave_id):
        """
        Upload files associated with comments
        """
        try:
            comment_id = request.data.get("comment_id")
            files = request.FILES.getlist("files")
            comment = get_object_or_404(LeaverequestComment, id=comment_id)
            attachments = []
            for file in files:
                file_instance = LeaverequestFile(file=file)
                file_instance.save()
                attachments.append(file_instance)
            comment.files.add(*attachments)

            return Response({"message": "Files uploaded successfully."}, status=status.HTTP_201_CREATED)
        except LeaverequestComment.DoesNotExist:
            return Response({"error": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class CreateAllocationRequestCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, leave_id):
        try:
            leave = get_object_or_404(LeaveAllocationRequest, id=leave_id)
            emp = request.user.employee_get
            data = request.data.copy()
            data['employee_id'] = emp.id
            data['request_id'] = leave.id

            form = LeaveallocationrequestcommentForm(data)

            if form.is_valid():
                form.instance.employee_id = emp
                form.instance.request_id = leave
                form.save()
                
                comments = LeaveallocationrequestComment.objects.filter(request_id=leave_id).order_by("-created_at")
                no_comments = not comments.exists()
                messages.success(request, _("Comment added successfully!"))

                work_info = EmployeeWorkInformation.objects.filter(employee_id=leave.employee_id)
                if work_info.exists():
                    if leave.employee_id.employee_work_info.reporting_manager_id:
                        if request.user.employee_get.id == leave.employee_id.id:
                            rec = leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                            notify.send(
                                request.user.employee_get,
                                recipient=rec,
                                verb=f"{leave.employee_id}'s leave allocation request has received a comment.",
                                redirect=reverse("leave-allocation-request-view") + f"?id={leave.id}",
                                icon="chatbox-ellipses"
                            )
                        elif request.user.employee_get.id == leave.employee_id.employee_work_info.reporting_manager_id.id:
                            rec = leave.employee_id.employee_user_id
                            notify.send(
                                request.user.employee_get,
                                recipient=rec,
                                verb="Your leave allocation request has received a comment.",
                                redirect=reverse("leave-allocation-request-view") + f"?id={leave.id}",
                                icon="chatbox-ellipses"
                            )
                        else:
                            rec = [
                                leave.employee_id.employee_user_id,
                                leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            ]
                            notify.send(
                                request.user.employee_get,
                                recipient=rec,
                                verb=f"{leave.employee_id}'s leave allocation request has received a comment.",
                                redirect=reverse("leave-allocation-request-view") + f"?id={leave.id}",
                                icon="chatbox-ellipses"
                            )
                    else:
                        rec = leave.employee_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb="Your leave allocation request has received a comment.",
                            redirect=reverse("leave-allocation-request-view") + f"?id={leave.id}",
                            icon="chatbox-ellipses"
                        )
                return Response({"detail": "Comment added successfully!"}, status=status.HTTP_201_CREATED)
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except LeaveAllocationRequest.DoesNotExist:
            return Response({"error": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ViewAllocationRequestCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, leave_id):
        try:
            comments = LeaveallocationrequestComment.objects.filter(request_id=leave_id).order_by("-created_at")
            no_comments = not comments.exists()

            return Response({
                "comments": LeaveallocationrequestCommentSerializer(comments, many=True).data,
                "no_comments": no_comments,
                "request_id": leave_id,
            }, status=status.HTTP_200_OK)
        except LeaveallocationrequestComment.DoesNotExist:
            return Response({"error": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class DeleteAllocationRequestCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, comment_id):
        try:
            # Get the comment or return a 404 error if not found
            comment = LeaveallocationrequestComment.objects.filter(id=comment_id)
            
            # Check if the user has permission to delete the comment
            if not request.user.has_perm("leave.delete_leaveallocationrequestcomment"):
                comment = comment.filter(employee_id__employee_user_id=request.user)
            
            # Get the request ID for redirection
            if comment.exists():
                request_id = comment.first().request_id.id
            else:
                return Response({"detail": "Comment not found or you do not have permission to delete it."}, status=status.HTTP_404_NOT_FOUND)
            
            # Delete the comment
            comment.delete()
            messages.success(request, _("Comment deleted successfully!"))

            return Response({"detail": "Comment deleted successfully!", "request_id": request_id}, status=status.HTTP_204_NO_CONTENT)

        except LeaveallocationrequestComment.DoesNotExist:
            return Response({"error": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class DeleteAllocationCommentFileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            ids = request.GET.getlist("ids")
            if request.user.has_perm("leave.delete_leaverequestfile"):
                LeaverequestFile.objects.filter(id__in=ids).delete()
            else:
                LeaverequestFile.objects.filter(
                    id__in=ids, employee_id__employee_user_id=request.user
                ).delete()

            leave_id = request.GET.get("leave_id")
            comments = LeaveallocationrequestComment.objects.filter(
                request_id=leave_id
            ).order_by("-created_at")

            return Response({
                "comments": LeaveallocationrequestCommentSerializer(comments, many=True).data,
                "request_id": leave_id
            }, status=status.HTTP_204_NO_CONTENT)

        except LeaverequestFile.DoesNotExist:
            return Response({"error": "File(s) not found."}, status=status.HTTP_404_NOT_FOUND)
        except LeaveallocationrequestComment.DoesNotExist:
            return Response({"error": "Leave allocation request not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ViewClashesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, leave_request_id):
        record = get_object_or_404(LeaveRequest, id=leave_request_id)

        if record.status in ["rejected", "cancelled"]:
            overlapping_requests = LeaveRequest.objects.none()
            clashed_due_to_department = LeaveRequest.objects.none()
            clashed_due_to_job_position = LeaveRequest.objects.none()
        else:
            overlapping_requests = (
                LeaveRequest.objects.filter(
                    Q(
                        employee_id__employee_work_info__department_id=record.employee_id.employee_work_info.department_id
                    )
                    | Q(
                        employee_id__employee_work_info__job_position_id=record.employee_id.employee_work_info.job_position_id
                    ),
                    start_date__lte=record.end_date,
                    end_date__gte=record.start_date,
                )
                .exclude(id=leave_request_id)
                .exclude(Q(status="cancelled") | Q(status="rejected"))
            )

            clashed_due_to_department = overlapping_requests.filter(
                employee_id__employee_work_info__department_id=record.employee_id.employee_work_info.department_id
            )

            clashed_due_to_job_position = overlapping_requests.filter(
                employee_id__employee_work_info__job_position_id=record.employee_id.employee_work_info.job_position_id
            )

        leave_request_filter = LeaveRequestFilter(request.GET, overlapping_requests).qs
        leave_request_filter = paginator_qry(leave_request_filter, request.GET.get("page"))

        requests_ids = [instance.id for instance in leave_request_filter.object_list]

        return Response({
            "leave_request": LeaveRequestSerializer(record).data,
            "records": LeaveRequestSerializer(overlapping_requests, many=True).data,
            "current_date": date.today(),
            "requests_ids": requests_ids,
            "clashed_due_to_department": LeaveRequestSerializer(clashed_due_to_department, many=True).data,
            "clashed_due_to_job_position": LeaveRequestSerializer(clashed_due_to_job_position, many=True).data,
        }, status=status.HTTP_200_OK)





class CompensatoryLeaveSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled_compensatory = (
            LeaveGeneralSetting.objects.exists()
            and LeaveGeneralSetting.objects.first().compensatory_leave
        )
        leave_type, created = LeaveType.objects.get_or_create(
            is_compensatory_leave=True,
            defaults={"name": "Compensatory Leave Type", "payment": "paid"},
        )
        context = {
            "enabled_compensatory": enabled_compensatory,
            "leave_type": LeaveTypeSerializer(leave_type).data,
        }
        return Response(context, status=status.HTTP_200_OK)



class CompensatoryLeaveSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled_compensatory = (
            LeaveGeneralSetting.objects.exists()
            and LeaveGeneralSetting.objects.first().compensatory_leave
        )
        leave_type, created = LeaveType.objects.get_or_create(
            is_compensatory_leave=True,
            defaults={"name": "Compensatory Leave Type", "payment": "paid"},
        )
        context = {
            "enabled_compensatory": enabled_compensatory,
            "leave_type": LeaveTypeSerializer(leave_type).data,
        }
        return Response(context, status=status.HTTP_200_OK)





class EnableCompensatoryLeaveAPIView(APIView):
    """
    API view to enable/disable the compensatory leave feature.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to enable/disable the compensatory leave feature.
        """
        compensatory_leave = LeaveGeneralSetting.objects.first()
        if not compensatory_leave:
            compensatory_leave = LeaveGeneralSetting()

        enable = request.data.get("compensatory_leave", False)
        compensatory_leave.compensatory_leave = enable
        compensatory_leave.save()

        if enable:
            messages.success(request, _("Compensatory leave is enabled successfully!"))
            return Response({"message": _("Compensatory leave is enabled successfully!")}, status=200)
        else:
            messages.success(request, _("Compensatory leave is disabled successfully!"))
            return Response({"message": _("Compensatory leave is disabled successfully!")}, status=200)



class DeleteLeaveRequestCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, comment_id):
       
        comment = LeaverequestComment.objects.filter(id=comment_id)
  
        if not request.user.has_perm("leave.delete_leaverequestcomment"):
            comment = comment.filter(employee_id__employee_user_id=request.user)
   
        if comment.exists():
            leave_id = comment.first().request_id.id
        else:
            return Response({"detail": "Comment not found or you do not have permission to delete it."}, status=status.HTTP_404_NOT_FOUND)
    
        comment.delete()
        messages.success(request, _("Comment deleted successfully!"))

        return Response({"detail": "Comment deleted successfully!", "leave_id": leave_id}, status=status.HTTP_204_NO_CONTENT)




class DeleteCommentFileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        ids = request.GET.getlist("ids")
        LeaverequestFile.objects.filter(id__in=ids).delete()
        
        leave_id = request.GET.get("leave_id")
        comments = LeaverequestComment.objects.filter(request_id=leave_id).order_by("-created_at")
        
        return Response({
            "comments": LeaverequestCommentSerializer(comments, many=True).data,
            "request_id": leave_id
        }, status=status.HTTP_200_OK)



class GetLeaveAttendanceDatesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee_id = request.GET.get("employee_id")
            if employee_id:
                employee = get_object_or_404(Employee, id=employee_id)
                holiday_attendance = get_leave_day_attendance(employee)
                # Get a list of tuples containing (id, attendance_date)
                attendance_dates = list(
                    holiday_attendance.values_list("id", "attendance_date")
                )
                return Response({
                    "attendance_dates": attendance_dates
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Employee ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteCommentCompensatoryFileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        ids = request.GET.getlist("ids")
        LeaverequestFile.objects.filter(id__in=ids).delete()
        
        leave_id = request.GET.get("leave_id")
        comments = CompensatoryLeaverequestComment.objects.all()

        if not request.user.has_perm("leave.delete_compensatoryleaverequestcomment"):
            comments = comments.filter(employee_id__employee_user_id=request.user)

        comments = comments.filter(request_id=leave_id).order_by("-created_at")
        template = "leave/compensatory_leave/compensatory_leave_comment.html" if request.GET.get("compensatory") else "leave/leave_request/leave_comment.html"
        
        return Response({
            "comments": CompensatoryLeaverequestCommentSerializer(comments, many=True).data,
            "request_id": leave_id,
            "template": template
        }, status=status.HTTP_200_OK)




class DeleteLeaverequestCompensatoryCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, comment_id):
        if request.GET.get("compensatory"):
            comment = CompensatoryLeaverequestComment.objects.filter(id=comment_id)
            if not request.user.has_perm("leave.delete_compensatoryleaverequestcomment"):
                comment = comment.filter(employee_id__employee_user_id=request.user)
            redirect_url = "view-compensatory-leave-comment"
        else:
            comment = LeaverequestComment.objects.filter(id=comment_id)
            if not request.user.has_perm("leave.delete_leaverequestcomment"):
                comment = comment.filter(employee_id__employee_user_id=request.user)
            redirect_url = "leave-request-view-comment"
        
        leave_id = comment.first().request_id.id if comment.exists() else None
        if leave_id:
            comment.delete()
            messages.success(request, _("Comment deleted successfully!"))
            return Response({"redirect_url": redirect_url, "leave_id": leave_id}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "Comment not found or you do not have permission to delete it."}, status=status.HTTP_404_NOT_FOUND)








class CompensatoryLeaveRequestPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ViewCompensatoryLeaveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employee = request.user.employee_get
            queryset = CompensatoryLeaveRequest.objects.all().order_by("-id")
            filtered_qs = CompensatoryLeaveRequestFilter(request.GET, queryset).qs
            filtered_qs = filtersubordinates(request, filtered_qs, "leave.view_compensatoryleaverequest")
            
            paginator = CompensatoryLeaveRequestPagination()
            paginated_qs = paginator.paginate_queryset(filtered_qs, request)
            
            comp_leave_requests = CompensatoryLeaveRequestSerializer(paginated_qs, many=True)
            requests_ids = json.dumps([obj.id for obj in paginated_qs])

            my_comp_leave_requests = CompensatoryLeaveRequest.objects.filter(employee_id=employee.id).order_by("-id")
            filtered_my_comp_leave_requests = CompensatoryLeaveRequestFilter(request.GET, my_comp_leave_requests).qs
            paginated_my_comp_leave_requests = paginator.paginate_queryset(filtered_my_comp_leave_requests, request)
            
            my_comp_leave_requests_data = CompensatoryLeaveRequestSerializer(paginated_my_comp_leave_requests, many=True)
            my_requests_ids = json.dumps([obj.id for obj in paginated_my_comp_leave_requests])

            previous_data = request.GET.urlencode()
            data_dict = parse_qs(previous_data)
            data_dict = get_key_instances(CompensatoryLeaveRequest, data_dict)

            context = {
                "my_comp_leave_requests": my_comp_leave_requests_data.data,
                "comp_leave_requests": comp_leave_requests.data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "requests_ids": requests_ids,
                "my_requests_ids": my_requests_ids,
            }
            
            return Response(context, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class FilterCompensatoryLeaveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        field = request.GET.get("field")
        employee = request.user.employee_get
        page_number = request.GET.get("page")
        my_page_number = request.GET.get("m_page")
        previous_data = request.GET.urlencode()

        # Filter compensatory leave requests
        comp_leave_requests_filtered = CompensatoryLeaveRequestFilter(
            request.GET
        ).qs.order_by("-id")
        my_comp_leave_requests_filtered = CompensatoryLeaveRequest.objects.filter(
            employee_id=employee.id
        ).order_by("-id")
        my_comp_leave_requests_filtered = CompensatoryLeaveRequestFilter(
            request.GET, my_comp_leave_requests_filtered
        ).qs
        comp_leave_requests_filtered = filtersubordinates(
            request, comp_leave_requests_filtered, "leave.view_leaveallocationrequest"
        )

        # Sort compensatory leave requests if requested
        if request.GET.get("sortby"):
            comp_leave_requests_filtered = sortby(
                request, comp_leave_requests_filtered, "sortby"
            )
            my_comp_leave_requests_filtered = sortby(
                request, my_comp_leave_requests_filtered, "sortby"
            )

        # Group compensatory leave requests if field parameter is provided
        if field:
            comp_leave_requests = group_by_queryset(
                comp_leave_requests_filtered, field, page_number, "page"
            )
            my_comp_leave_requests = group_by_queryset(
                my_comp_leave_requests_filtered, field, my_page_number, "m_page"
            )

            # Convert IDs to JSON format for details view
            list_values = [entry["list"] for entry in comp_leave_requests]
            id_list = [
                instance.id for value in list_values for instance in value.object_list
            ]
            requests_ids = json.dumps(list(id_list))

            list_values = [entry["list"] for entry in my_comp_leave_requests]
            id_list = [
                instance.id for value in list_values for instance in value.object_list
            ]
            my_requests_ids = json.dumps(list(id_list))
            template = (
                "leave/leave_allocation_request/leave_allocation_request_group_by.html"
            )
        else:
            comp_leave_requests = paginator_qry(
                comp_leave_requests_filtered, page_number
            )
            my_comp_leave_requests = paginator_qry(
                my_comp_leave_requests_filtered, my_page_number
            )
            requests_ids = json.dumps(
                list(comp_leave_requests.object_list.values_list("id", flat=True))
            )
            my_requests_ids = json.dumps(
                list(my_comp_leave_requests.object_list.values_list("id", flat=True))
            )

        # Parse previous data and construct context for filter tag
        data_dict = parse_qs(previous_data)
        data_dict = get_key_instances(CompensatoryLeaveRequest, data_dict)
        data_dict.pop("m_page", None)

        context = {
            "comp_leave_requests": CompensatoryLeaveRequestSerializer(comp_leave_requests, many=True).data,
            "my_comp_leave_requests": CompensatoryLeaveRequestSerializer(my_comp_leave_requests, many=True).data,
            "previous_data": previous_data,
            "filter_dict": data_dict,
            "field": field,
            "requests_ids": requests_ids,
            "my_requests_ids": my_requests_ids,
        }
        
        return Response(context, status=status.HTTP_200_OK)




class CompensatoryLeaveRequestCreate(APIView):
    def post(self, request, comp_id=None):
        employee = request.user.employee_get

        instance = None
        if comp_id is not None:
            try:
                instance = CompensatoryLeaveRequest.objects.get(id=comp_id)
            except CompensatoryLeaveRequest.DoesNotExist:
                return Response({"detail": _("Not found.")}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        data['employee'] = employee.id  # Assuming `employee` is an instance of the Employee model

        form = CompensatoryLeaveForm(data, instance=instance)
        if form.is_valid():
            comp_req = form.save()
            comp_req.requested_days = attendance_days(
                comp_req.employee_id, comp_req.attendance_id.all()
            )
            comp_req.save()
            if comp_id is not None:
                message = _("Compensatory Leave updated.")
            else:
                message = _("Compensatory Leave created.")
            return Response({"detail": message}, status=status.HTTP_201_CREATED)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteCompensatoryLeaveRequestView(generics.DestroyAPIView):
    queryset = CompensatoryLeaveRequest.objects.all()
    lookup_field = 'id'

    def delete(self, request, comp_id, *args, **kwargs):
        try:
            comp_leave_req = CompensatoryLeaveRequest.objects.get(id=comp_id)
            comp_leave_req.delete()
            return Response({"detail": _("Compensatory leave request deleted.")}, status=status.HTTP_204_NO_CONTENT)
        except CompensatoryLeaveRequest.DoesNotExist:
            return Response({"detail": _("Compensatory leave request not found!")}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": _("An error occurred: {}").format(str(e))}, status=status.HTTP_400_BAD_REQUEST)


class ApproveCompensatoryLeaveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comp_id):
        try:
         
            comp_leave_req = get_object_or_404(CompensatoryLeaveRequest, id=comp_id)
            
            if comp_leave_req.status == "requested":
     
                comp_leave_req.status = "approved"
                comp_leave_req.assign_compensatory_leave_type()
                comp_leave_req.save()
                
                messages.success(request, _("Compensatory leave request approved."))
                
 
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=comp_leave_req.employee_id.employee_user_id,
                        verb="Your compensatory leave request has been approved",
                        verb_ar="تمت الموافقة على طلب إجازة الاعتذار الخاص بك",
                        verb_de="Ihr Antrag auf Freizeitausgleich wurde genehmigt",
                        verb_es="Su solicitud de permiso compensatorio ha sido aprobada",
                        verb_fr="Votre demande de congé compensatoire a été approuvée",
                        redirect=reverse("view-compensatory-leave") + f"?id={comp_leave_req.id}",
                    )
            else:
                messages.info(request, _("The compensatory leave request is not in the 'requested' status."))

        except Exception as e:
            messages.error(request, _("Sorry, something went wrong!"))
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
        if request.GET.get("individual"):
            return HttpResponse("<script>location.reload();</script>", status=status.HTTP_200_OK)
        return Response({"message": "Compensatory leave request approved successfully."}, status=status.HTTP_200_OK)








from django.core.exceptions import MultipleObjectsReturned


class LeaveRequestCreateAPI(APIView):
    """
    API endpoint to create leave requests.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        JsonResponse: Success or error message with status.
    """

    def post(self, request):
        previous_data = request.data.get("pd", "")
        emp = request.user.employee_get
        emp_id = emp.id

        form = UserLeaveRequestCreationForm(request.data, request.FILES, employee=emp)
        if int(form.data.get("employee_id")) == int(emp_id):
            if form.is_valid():
                leave_request = form.save(commit=False)
                save = True

                if leave_request.leave_type_id.require_approval == "no":
                    try:
                        available_leaves = AvailableLeave.objects.filter(
                            leave_type_id=leave_request.leave_type_id, 
                            employee_id=leave_request.employee_id
                        )
                        if available_leaves.count() == 0:
                            return Response({"error": "No available leave records found."}, status=status.HTTP_404_NOT_FOUND)
                        elif available_leaves.count() > 1:
                            available_leave = available_leaves.first()  # Using the first record as a fallback
                            # Optionally log a warning or flag the data issue for further review
                        else:
                            available_leave = available_leaves.first()

                        if leave_request.requested_days > available_leave.available_days:
                            leave = leave_request.requested_days - available_leave.available_days
                            leave_request.approved_available_days = available_leave.available_days
                            available_leave.available_days = 0
                            available_leave.carryforward_days -= leave
                            leave_request.approved_carryforward_days = leave
                        else:
                            available_leave.available_days -= leave_request.requested_days
                            leave_request.approved_available_days = leave_request.requested_days
                        leave_request.status = "approved"
                        available_leave.save()
                    except MultipleObjectsReturned:
                        return Response({"error": "Multiple leave type records found, please check data integrity."}, status=status.HTTP_400_BAD_REQUEST)

                if save:
                    leave_request.created_by = request.user.employee_get
                    leave_request.save()

                    if multiple_approvals_check(leave_request.id):
                        conditional_requests = multiple_approvals_check(leave_request.id)
                        managers = [manager.employee_user_id for manager in conditional_requests["managers"]]
                        with contextlib.suppress(Exception):
                            notify.send(
                                request.user.employee_get,
                                recipient=managers[0],
                                verb="You have a new leave request to validate.",
                                verb_ar="لديك طلب إجازة جديد يجب التحقق منه.",
                                verb_de="Sie haben eine neue Urlaubsanfrage zur Validierung.",
                                verb_es="Tiene una nueva solicitud de permiso que debe validar.",
                                verb_fr="Vous avez une nouvelle demande de congé à valider.",
                                icon="people-circle",
                                redirect=f"/leave/request-view?id={leave_request.id}",
                            )

                    with contextlib.suppress(Exception):
                        notify.send(
                            request.user.employee_get,
                            recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                            verb=f"New leave request created for {leave_request.employee_id}.",
                            verb_ar=f"تم إنشاء طلب إجازة جديد لـ {leave_request.employee_id}.",
                            verb_de=f"Neuer Urlaubsantrag für {leave_request.employee_id} erstellt.",
                            verb_es=f"Nueva solicitud de permiso creada para {leave_request.employee_id}.",
                            verb_fr=f"Nouvelle demande de congé créée pour {leave_request.employee_id}.",
                            icon="people-circle",
                            redirect=f"/leave/request-view?id={leave_request.id}",
                        )

                    return Response({"success": "Leave request created successfully."}, status=status.HTTP_201_CREATED)
            return Response({"error": "Invalid form data.", "details": form.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "You don't have permission to create this leave request."}, status=status.HTTP_403_FORBIDDEN)




class LeaveRequestUpdateAPIView(APIView):
    """
    API endpoint to update leave requests.

    Args:
        request (HttpRequest): The HTTP request object.
        id (int): ID of the leave request to update.

    Returns:
        JsonResponse: Success or error message with status.
    """

    def post(self, request, id):
        leave_request = get_object_or_404(LeaveRequest, id=id)
        leave_type_id = leave_request.leave_type_id
        employee = leave_request.employee_id

        form = LeaveRequestUpdationForm(data=request.data, files=request.FILES, instance=leave_request)
        
        if employee:
            available_leaves = employee.available_leave.all()
            assigned_leave_types = LeaveType.objects.filter(
                id__in=available_leaves.values_list("leave_type_id", flat=True)
            )
            if not assigned_leave_types.filter(id=leave_type_id.id).exists():
                assigned_leave_types = assigned_leave_types | LeaveType.objects.filter(id=leave_type_id.id)
            form.fields["leave_type_id"].queryset = assigned_leave_types

        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.save()
            messages.success(request, _("Leave request is updated successfully."))
            
            with contextlib.suppress(Exception):
                notify.send(
                    request.user.employee_get,
                    recipient=leave_request.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    verb=f"Leave request updated for {leave_request.employee_id}.",
                    verb_ar=f"تم تحديث طلب الإجازة لـ {leave_request.employee_id}.",
                    verb_de=f"Urlaubsantrag aktualisiert für {leave_request.employee_id}.",
                    verb_es=f"Solicitud de permiso actualizada para {leave_request.employee_id}.",
                    verb_fr=f"Demande de congé mise à jour pour {leave_request.employee_id}.",
                    icon="people-circle",
                    redirect=f"/leave/request-view?id={leave_request.id}",
                )

            return Response({"success": "Leave request updated successfully."}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid form data.", "details": form.errors}, status=status.HTTP_400_BAD_REQUEST)







class LeaveRequestsExportAPIView(APIView):
    def get(self, request, *args, **kwargs):
        if request.META.get("HTTP_HX_REQUEST") == "true":
            excel_column = LeaveRequestExportForm()
            export_filter = LeaveRequestFilter()
            context = {
                "excel_column": excel_column,
                "export_filter": export_filter.form,
            }

            return render(
                request,
                "leave/leave_request/leave_requests_export_filter.html",
                context=context,
            )
        
        # Apply filters
        filter_class = LeaveRequestFilter(request.GET, queryset=LeaveRequest.objects.all())
        leave_requests = filter_class.qs

        # Serialize the data
        serializer = LeaveRequestSerializer(leave_requests, many=True)
        
        # Return JSON response
        return Response(serializer.data, status=status.HTTP_200_OK)



class RejectCompensatoryLeaveRequestView(APIView):
    def post(self, request, comp_id):
        """
        Function used to handle POST requests.
        """
        comp_leave_req = get_object_or_404(CompensatoryLeaveRequest, id=comp_id)
        if comp_leave_req.status in ["requested", "approved"]:
            form = CompensatoryLeaveRequestRejectForm(request.POST)
            if form.is_valid():
                comp_leave_req.reject_reason = form.cleaned_data["reason"]
                comp_leave_req.status = "rejected"
                comp_leave_req.exclude_compensatory_leave()
                comp_leave_req.save()
                with contextlib.suppress(Exception):
                    notify.send(
                        request.user.employee_get,
                        recipient=comp_leave_req.employee_id.employee_user_id,
                        verb="Your compensatory leave request has been rejected",
                        verb_ar="تم رفض طلبك للإجازة التعويضية",
                        verb_de="Ihr Antrag auf Freizeitausgleich wurde abgelehnt",
                        verb_es="Se ha rechazado su solicitud de permiso compensatorio",
                        verb_fr="Votre demande de congé compensatoire a été rejetée",
                        redirect=reverse("view-compensatory-leave")
                        + f"?id={comp_leave_req.id}",
                    )
                return Response({"success": _("Compensatory Leave request rejected.")}, status=status.HTTP_200_OK)
            return Response({"error": _("Invalid form data.")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": _("The leave allocation request can't be rejected")}, status=status.HTTP_400_BAD_REQUEST)




class CompensatoryLeaveIndividualView(APIView):
    def get(self, request, comp_leave_id):
        """
        Function used to present the compensatory leave request detailed view.
        """
        requests_ids_json = request.GET.get("instances_ids")
        previous_id, next_id = None, None
        
        if requests_ids_json:
            requests_ids = json.loads(requests_ids_json)
            previous_id, next_id = closest_numbers(requests_ids, comp_leave_id)
        
        comp_leave_req = get_object_or_404(CompensatoryLeaveRequest, id=comp_leave_id)
        comp_leave_req_serializer = CompensatoryLeaveRequestSerializer(comp_leave_req)
        
        context = {
            "comp_leave_req": comp_leave_req_serializer.data,
            "my_request": eval(request.GET.get("my_request", "False")),
            "instances_ids": requests_ids_json,
            "previous": previous_id,
            "next": next_id,
        }
        
        return Response(context)





class CompensatoryLeaveCommentView(APIView):
    def get(self, request, comp_leave_id):
        """
        Method to retrieve comments for a compensatory leave request.
        """
        comments = CompensatoryLeaverequestComment.objects.filter(request_id=comp_leave_id).order_by("-created_at")
        serializer = CompensatoryLeaverequestCommentSerializer(comments, many=True)
        no_comments = not comments.exists()

        context = {
            "comments": serializer.data,
            "no_comments": no_comments,
            "request_id": comp_leave_id,
        }

        return Response(context)



class CreateCompensatoryLeaveCommentView(APIView):
    def post(self, request, comp_leave_id):
        """
        This method handles POST requests to create Compensatory leave comments.
        """
        comp_leave = get_object_or_404(CompensatoryLeaveRequest, id=comp_leave_id)
        emp = request.user.employee_get
        data = request.data.copy()  # Create a mutable copy of the request data
        data["employee_id"] = emp.id
        data["request_id"] = comp_leave.id
        
        serializer = CompensatoryLeaverequestCommentSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()

            messages.success(request, _("Comment added successfully!"))
            work_info = EmployeeWorkInformation.objects.filter(employee_id=comp_leave.employee_id)

            if work_info.exists():
                if comp_leave.employee_id.employee_work_info.reporting_manager_id is not None:
                    if request.user.employee_get.id == comp_leave.employee_id.id:
                        rec = comp_leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{comp_leave.employee_id}'s Compensatory leave request has received a comment.",
                            verb_ar=f"تلقى طلب إجازة الاعتذار لـ {comp_leave.employee_id} تعليقًا.",
                            verb_de=f"Der Antrag auf Freizeitausgleich von {comp_leave.employee_id} hat einen Kommentar erhalten.",
                            verb_es=f"La solicitud de permiso compensatorio de {comp_leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de congé compensatoire de {comp_leave.employee_id} a reçu un commentaire.",
                            redirect=reverse("view-compensatory-leave") + f"?id={comp_leave.id}",
                            icon="chatbox-ellipses",
                        )
                    elif request.user.employee_get.id == comp_leave.employee_id.employee_work_info.reporting_manager_id.id:
                        rec = comp_leave.employee_id.employee_user_id
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb="Your compensatory leave request has received a comment.",
                            verb_ar="تلقى طلب إجازة العوض الخاص بك تعليقًا.",
                            verb_de="Ihr Antrag auf Freizeitausgleich hat einen Kommentar erhalten.",
                            verb_es="Su solicitud de permiso compensatorio ha recibido un comentario.",
                            verb_fr="Votre demande de congé compensatoire a reçu un commentaire.",
                            redirect=reverse("view-compensatory-leave") + f"?id={comp_leave.id}",
                            icon="chatbox-ellipses",
                        )
                    else:
                        rec = [
                            comp_leave.employee_id.employee_user_id,
                            comp_leave.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        ]
                        notify.send(
                            request.user.employee_get,
                            recipient=rec,
                            verb=f"{comp_leave.employee_id}'s compensatory leave request has received a comment.",
                            verb_ar=f"تلقى طلب إجازة التعويض لـ {comp_leave.employee_id} تعليقًا.",
                            verb_de=f"Der Antrag auf Freizeitausgleich von {comp_leave.employee_id} hat einen Kommentar erhalten.",
                            verb_es=f"El pedido de permiso compensatorio de {comp_leave.employee_id} ha recibido un comentario.",
                            verb_fr=f"La demande de congé compensatoire de {comp_leave.employee_id} a reçu un commentaire.",
                            redirect=reverse("view-compensatory-leave") + f"?id={comp_leave.id}",
                            icon="chatbox-ellipses",
                        )
                else:
                    rec = comp_leave.employee_id.employee_user_id
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb="Your compensatory leave request has received a comment.",
                        verb_ar="تلقى طلب إجازة العوض الخاص بك تعليقًا.",
                        verb_de="Ihr Antrag auf Freizeitausgleich hat einen Kommentar erhalten.",
                        verb_es="Su solicitud de permiso compensatorio ha recibido un comentario.",
                        verb_fr="Votre demande de congé compensatoire a reçu un commentaire.",
                        redirect=reverse("view-compensatory-leave") + f"?id={comp_leave.id}",
                        icon="chatbox-ellipses",
                    )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
