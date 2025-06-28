from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib import messages
from rest_framework import status
from django.utils.translation import gettext as _
from django.http import HttpResponse
from .serializers import ShiftRequestSerializer
from base.methods import choosesubordinates, is_reportingmanager
from notifications.signals import notify
from base.views import include_employee_instance
from django.urls import reverse
from django.shortcuts import get_object_or_404
from base.models import (ShiftRequest,
Company,
Department,
JobPosition,
JobRole,
WorkType,
Announcement,
AnnouncementView,
User,
AnnouncementComment,
ShiftRequest, 
ShiftRequestComment,
BaserequestFile,
WorkTypeRequestComment,
WorkTypeRequest,
EmployeeShiftSchedule, 
EmployeeShift,
RotatingShift,
 EmployeeType,
 Tags




)
from base.forms import ShiftRequestForm,CompanyForm,DepartmentForm,JobPositionForm,JobPositionMultiForm,JobRoleForm,WorkTypeForm,EmployeeShiftScheduleForm,EmployeeShiftScheduleUpdateForm,RotatingShiftForm,EmployeeTypeForm
from employee.models import EmployeeWorkInformation
from datetime import datetime
from django.db.models import ProtectedError
from rest_framework.pagination import PageNumberPagination
from .serializers import( CompanySerializer,
DepartmentSerializer ,
JobPositionSerializer,
JobRoleSerializer,
WorkTypeSerializer,
AnnouncementSerializer,
AnnouncementViewSerializer,
AnnouncementCommentSerializer ,
ActiontypeSerializer,
ShiftRequestCommentSerializer,
WorkTypeRequestCommentSerializer,
 EmployeeShiftSerializer,
 EmployeeShiftScheduleSerializer,
 RotatingShiftSerializer,
  EmployeeTypeSerializer ,
  AuditTagSerializer,
  TagsSerializer


)
from employee.models import Employee,Actiontype,DisciplinaryAction
from horilla_audit.models import AuditTag
from employee.authentication import JWTAuthentication

class ShiftRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        data = request.data
        print("Received data:", data)  # Debugging statement
        serializer = ShiftRequestSerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save()
            print("Saved instance:", instance)  # Debugging statement
            try:
                notify.send(
                    instance.employee_id,
                    recipient=(
                        instance.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                    ),
                    verb=f"You have new shift request to approve for {instance.employee_id}",
                    verb_ar=f"لديك طلب وردية جديد للموافقة عليه لـ {instance.employee_id}",
                    verb_de=f"Sie müssen eine neue Schichtanfrage für {instance.employee_id} genehmigen",
                    verb_es=f"Tiene una nueva solicitud de turno para aprobar para {instance.employee_id}",
                    verb_fr=f"Vous avez une nouvelle demande de quart de travail à approuver pour {instance.employee_id}",
                    icon="information",
                    redirect=reverse("shift-request-view") + f"?id={instance.id}",
                )
            except Exception as e:
                print("Notification error:", e)  # Debugging statement
                pass
            messages.success(request, _("Shift request added"))
            return Response({"message": "Shift request added successfully"}, status=status.HTTP_201_CREATED)
        print("Serializer errors:", serializer.errors)  # Debugging statement
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ShiftRequestUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, shift_request_id):
        """
        This method is used to update shift request instance
        args:
            shift_request_id : shift request instance id
        """
        shift_request = get_object_or_404(ShiftRequest, id=shift_request_id)

        if shift_request.approved:
            messages.info(request, _("Can't edit approved shift request"))
            return Response({"detail": "Can't edit approved shift request"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ShiftRequestSerializer(instance=shift_request, data=request.data, partial=True)

        if serializer.is_valid():
            instance = serializer.save()
            instance = choosesubordinates(request, instance, "base.change_shiftrequest")
            messages.success(request, _("Request Updated Successfully"))
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShiftRequestCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, shift_request_id):
        """
        This method is used to update or cancel shift request instance
        args:
            shift_request_id : shift request instance id
        """
        shift_request = get_object_or_404(ShiftRequest, id=shift_request_id)
        
        if not (
            is_reportingmanager(request, shift_request) or
            request.user.has_perm("base.cancel_shiftrequest") or
            (shift_request.employee_id == request.user.employee_get and not shift_request.approved)
        ):
            messages.error(request, _("You don't have permission"))
            return Response({"detail": "You don't have permission"}, status=status.HTTP_403_FORBIDDEN)
        
        today_date = datetime.today().date()
        if (
            shift_request.approved and
            shift_request.requested_date <= today_date <= shift_request.requested_till and
            not shift_request.is_permanent_shift
        ):
            shift_request.employee_id.employee_work_info.shift_id = shift_request.previous_shift_id
            shift_request.employee_id.employee_work_info.save()
        
        shift_request.canceled = True
        shift_request.approved = False
        work_info = EmployeeWorkInformation.objects.filter(employee_id=shift_request.employee_id)
        
        if work_info.exists():
            shift_request.employee_id.employee_work_info.shift_id = shift_request.previous_shift_id
        
        if shift_request.reallocate_to and work_info.exists():
            shift_request.reallocate_to.employee_work_info.shift_id = shift_request.shift_id
            shift_request.reallocate_to.employee_work_info.save()
        
        if work_info.exists():
            shift_request.employee_id.employee_work_info.save()
        
        shift_request.save()
        messages.success(request, _("Shift request rejected"))

        notify.send(
            request.user.employee_get,
            recipient=shift_request.employee_id.employee_user_id,
            verb="Your shift request has been canceled.",
            verb_ar="تم إلغاء طلبك للوردية.",
            verb_de="Ihr Schichtantrag wurde storniert.",
            verb_es="Se ha cancelado su solicitud de turno.",
            verb_fr="Votre demande de quart a été annulée.",
            redirect=reverse("shift-request-view") + f"?id={shift_request.id}",
            icon="close",
        )

        if shift_request.reallocate_to:
            notify.send(
                request.user.employee_get,
                recipient=shift_request.reallocate_to.employee_user_id,
                verb="Your shift request has been rejected.",
                verb_ar="تم إلغاء طلبك للوردية.",
                verb_de="Ihr Schichtantrag wurde storniert.",
                verb_es="Se ha cancelado su solicitud de turno.",
                verb_fr="Votre demande de quart a été annulée.",
                redirect=reverse("shift-request-view") + f"?id={shift_request.id}",
                icon="close",
            )

        return Response({"detail": "Shift request canceled"}, status=status.HTTP_200_OK)





class ShiftRequestApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request, shift_request_id):
        """
        This method is used to approve shift request instance
        args:
            shift_request_id : shift request instance id
        """
        shift_request = get_object_or_404(ShiftRequest, id=shift_request_id)

        if not shift_request:
            messages.error(request, _("Shift request not found."))
            return Response({"detail": "Shift request not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if not (
            is_reportingmanager(request, shift_request) or
            user.has_perm("approve_shiftrequest") or
            (user.has_perm("change_shiftrequest") and not shift_request.approved)
        ):
            messages.error(request, _("You don't have permission"))
            return Response({"detail": "You don't have permission"}, status=status.HTTP_403_FORBIDDEN)

        if shift_request.is_any_request_exists():
            messages.error(
                request,
                _("An approved shift request already exists during this time period."),
            )
            return Response({"detail": "An approved shift request already exists during this time period."}, status=status.HTTP_400_BAD_REQUEST)

        today_date = datetime.today().date()
        if not shift_request.is_permanent_shift:
            if shift_request.requested_date <= today_date <= shift_request.requested_till:
                shift_request.employee_id.employee_work_info.shift_id = shift_request.shift_id
                shift_request.employee_id.employee_work_info.save()
        shift_request.approved = True
        shift_request.canceled = False

        if shift_request.reallocate_to:
            shift_request.reallocate_to.employee_work_info.shift_id = shift_request.previous_shift_id
            shift_request.reallocate_to.employee_work_info.save()

        shift_request.save()
        messages.success(request, _("Shift has been approved."))

        recipients = [shift_request.employee_id.employee_user_id]
        if shift_request.reallocate_to:
            recipients.append(shift_request.reallocate_to.employee_user_id)

        for recipient in recipients:
            notify.send(
                user.employee_get,
                recipient=recipient,
                verb="Your shift request has been approved.",
                verb_ar="تمت الموافقة على طلبك للوردية.",
                verb_de="Ihr Schichtantrag wurde genehmigt.",
                verb_es="Se ha aprobado su solicitud de turno.",
                verb_fr="Votre demande de quart a été approuvée.",
                redirect=reverse("shift-request-view") + f"?id={shift_request.id}",
                icon="checkmark",
            )

        return Response({"detail": "Shift request approved"}, status=status.HTTP_200_OK)





class ShiftRequestDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request, shift_request_id):
        """
        This method is used to delete shift request instance
        args:
            shift_request_id : shift request instance id
        """
        try:
            shift_request = get_object_or_404(ShiftRequest, id=shift_request_id)
            user = shift_request.employee_id.employee_user_id
            shift_request.delete()
            notify.send(
                request.user.employee_get,
                recipient=user,
                verb="Your shift request has been deleted.",
                verb_ar="تم حذف طلب الوردية الخاص بك.",
                verb_de="Ihr Schichtantrag wurde gelöscht.",
                verb_es="Se ha eliminado su solicitud de turno.",
                verb_fr="Votre demande de quart a été supprimée.",
                redirect="#",
                icon="trash",
            )
            messages.success(request, _("Shift request deleted"))
            return Response({"detail": "Shift request deleted"}, status=status.HTTP_200_OK)

        except ShiftRequest.DoesNotExist:
            messages.error(request, _("Shift request not found."))
            return Response({"detail": "Shift request not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError:
            messages.error(request, _("You cannot delete this shift request."))
            return Response({"detail": "You cannot delete this shift request."}, status=status.HTTP_400_BAD_REQUEST)



class CompanyCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        form = CompanyForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return Response({"detail": _("Company has been created successfully!")}, status=status.HTTP_201_CREATED)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)




class CompanyListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        companies = Company.objects.all()
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class CompanyUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id, **kwargs):
        try:
            company = Company.objects.get(id=id)
        except Company.DoesNotExist:
            return Response({"detail": _("Not found.")}, status=status.HTTP_404_NOT_FOUND)
        
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            return Response({"detail": _("Company updated successfully!")}, status=status.HTTP_200_OK)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)




class DepartmentCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            return Response({"detail": _("Department has been created successfully!")}, status=status.HTTP_201_CREATED)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class DepartmentListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        departments = Department.objects.all()
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class DepartmentUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id, **kwargs):
        try:
            department = Department.objects.get(id=id)
        except Department.DoesNotExist:
            return Response({"detail": _("Department not found.")}, status=status.HTTP_404_NOT_FOUND)

        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            return Response({"detail": _("Department updated successfully!")}, status=status.HTTP_200_OK)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)





class JobPositionListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        job_positions = JobPosition.objects.all()
        serializer = JobPositionSerializer(job_positions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data  # Handle JSON data
        form = JobPositionForm(data)
        if form.is_valid():
            form.save()
            return Response({"detail": _("Job Position has been created successfully!")}, status=status.HTTP_201_CREATED)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class JobPositionCreationView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API view for creating job positions.
    """

    def post(self, request):
        serializer = JobPositionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": _("Job Position has been created successfully!")},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class JobPositionUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API view to update a job position using POST.
    """

    def post(self, request, id):
        job_position = get_object_or_404(JobPosition, id=id)

        # Ensure data is provided
        if not request.data:
            return Response(
                {"error": _("No data provided for update.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = JobPositionSerializer(job_position, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": _("Job position updated successfully!")},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class JobRoleCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API view to create a job role.
    """

    def post(self, request):
        serializer = JobRoleSerializer(data=request.data)

        if request.data.get("job_position_id") and request.data.get("job_role"):
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": _("Job role has been created successfully!")},
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"error": _("Both job_position_id and job_role are required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class JobRoleView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API to view job roles with their corresponding job positions.
    """

    def get(self, request, *args, **kwargs):
        try:
            job_positions = JobPosition.objects.all()
            response_data = []

            for job_position in job_positions:
                job_roles = JobRole.objects.filter(job_position_id=job_position.id)

                job_position_data = {
                    "job_position": job_position.job_position,
                    "department": job_position.department_id.department,
                    "job_roles": [
                        {"role_name": job_role.job_role} for job_role in job_roles
                    ]
                }

                response_data.append(job_position_data)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class JobRoleUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id, **kwargs):
        try:
            job_role = JobRole.objects.get(id=id)
        except JobRole.DoesNotExist:
            return Response({"detail": _("Job role not found.")}, status=status.HTTP_404_NOT_FOUND)

        data = request.data  # Handle JSON data
        form = JobRoleForm(data, instance=job_role)
        if form.is_valid():
            form.save(commit=True)  # Ensure commit is passed
            return Response({"detail": _("Job role updated successfully!")}, status=status.HTTP_200_OK)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)




class WorkTypeCreateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        data = request.data  # Handle JSON data
        form = WorkTypeForm(data)
        if form.is_valid():
            form.save()
            return Response({"detail": _("Work Type has been created successfully!")}, status=status.HTTP_201_CREATED)
        else:
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class WorkTypeView(APIView):
    def get(self, request):
        work_types = WorkType.objects.all()
        serializer = WorkTypeSerializer(work_types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class WorkTypeUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API to update the work type instance using POST.
    """

    def get_object(self, id):
        try:
            return WorkType.objects.get(id=id)
        except WorkType.DoesNotExist:
            return None

    def post(self, request, id, *args, **kwargs):
        work_type = self.get_object(id)
        if not work_type:
            return Response({"error": "Work Type not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if request data is empty
        if not request.data:
            return Response({"error": "No data provided for update."}, status=status.HTTP_400_BAD_REQUEST)

        # Using the serializer to validate and update the work type
        serializer = WorkTypeSerializer(work_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Work type updated successfully!"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnnouncementAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        paginator = PageNumberPagination()
        paginator.page_size = 10
        announcements = Announcement.objects.all().order_by('-created_at')
        result_page = paginator.paginate_queryset(announcements, request)
        serializer = AnnouncementSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)



class ViewedByAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def get(self, request):
        announcement_id = request.GET.get('announcement_id')
        if not announcement_id:
            return Response({"error": "announcement_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        viewed_by = AnnouncementView.objects.filter(announcement_id__id=announcement_id, viewed=True)
        serializer = AnnouncementViewSerializer(viewed_by, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class AnnouncementCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        serializer = AnnouncementSerializer(data=request.data)
        if serializer.is_valid():
            anou = serializer.save()
            
            # Handle many-to-many relationships
            employees = request.data.get('employees', [])
            departments = request.data.get('department', [])
            job_positions = request.data.get('job_position', [])
            
            anou.department.set(departments)
            anou.job_position.set(job_positions)
            anou.employees.set(employees)
            anou.save()

            # Notify departments and job positions
            emp_dep = User.objects.filter(
                employee_get__employee_work_info__department_id__in=departments
            )
            emp_jobs = User.objects.filter(
                employee_get__employee_work_info__job_position_id__in=job_positions
            )
            notify.send(
                request.user.employee_get,
                recipient=emp_dep,
                verb="Your department was mentioned in a post.",
                verb_ar="تم ذكر قسمك في منشور.",
                verb_de="Ihr Abteilung wurde in einem Beitrag erwähnt.",
                verb_es="Tu departamento fue mencionado en una publicación.",
                verb_fr="Votre département a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            notify.send(
                request.user.employee_get,
                recipient=emp_jobs,
                verb="Your job position was mentioned in a post.",
                verb_ar="تم ذكر وظيفتك في منشور.",
                verb_de="Ihre Arbeitsposition wurde in einem Beitrag erwähnt.",
                verb_es="Tu puesto de trabajo fue mencionado en una publicación.",
                verb_fr="Votre poste de travail a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            messages.success(request, _("Announcement created successfully."))
            return Response({"message": "Announcement created successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class AnnouncementDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, anoun_id):
        try:
            announcement = Announcement.objects.get(id=anoun_id)
            announcement.delete()
            messages.success(request, _("Announcement deleted successfully."))
            return Response({"message": "Announcement deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found."}, status=status.HTTP_404_NOT_FOUND)





class AnnouncementUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request, anoun_id):
        try:
            announcement = Announcement.objects.get(id=anoun_id)
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AnnouncementSerializer(announcement, data=request.data)
        if serializer.is_valid():
            anou = serializer.save()
            
            # Handle many-to-many relationships
            employees = request.data.get('employees', [])
            departments = request.data.get('department', [])
            job_positions = request.data.get('job_position', [])
            
            anou.department.set(departments)
            anou.job_position.set(job_positions)
            anou.employees.set(employees)
            anou.save()

            # Notify departments and job positions
            emp_dep = User.objects.filter(
                employee_get__employee_work_info__department_id__in=departments
            )
            emp_jobs = User.objects.filter(
                employee_get__employee_work_info__job_position_id__in=job_positions
            )
            notify.send(
                request.user.employee_get,
                recipient=emp_dep,
                verb="Your department was mentioned in a post.",
                verb_ar="تم ذكر قسمك في منشور.",
                verb_de="Ihr Abteilung wurde in einem Beitrag erwähnt.",
                verb_es="Tu departamento fue mencionado en una publicación.",
                verb_fr="Votre département a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            notify.send(
                request.user.employee_get,
                recipient=emp_jobs,
                verb="Your job position was mentioned in a post.",
                verb_ar="تم ذكر وظيفتك في منشور.",
                verb_de="Ihre Arbeitsposition wurde in einem Beitrag erwähnt.",
                verb_es="Tu puesto de trabajo fue mencionado en una publicación.",
                verb_fr="Votre poste de travail a été mentionné dans un post.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            messages.success(request, _("Announcement updated successfully."))
            return Response({"message": "Announcement updated successfully."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






class AnnouncementCommentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request, anoun_id):
        try:
            anoun = Announcement.objects.get(id=anoun_id)
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found."}, status=status.HTTP_404_NOT_FOUND)

        emp_id = request.data.get('employee_id')
        if not emp_id:
            return Response({"error": "Employee ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        if not data.get('comment'):  # Check if comment is provided
            return Response({"error": "Comment is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            emp = Employee.objects.get(id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        data['employee_id'] = emp.id
        data['announcement_id'] = anoun.id
        serializer = AnnouncementCommentSerializer(data=data)

        if serializer.is_valid():
            comment = serializer.save()
            comments = AnnouncementComment.objects.filter(announcement_id=anoun_id)
            commentators = [i.employee_id.employee_user_id for i in comments]
            unique_users = list(set(commentators))

            notify.send(
                request.user.employee_get,
                recipient=unique_users,
                verb=f"Comment under the announcement {anoun.title}.",
                verb_ar=f"تعليق تحت الإعلان {anoun.title}.",
                verb_de=f"Kommentar unter der Ankündigung {anoun.title}.",
                verb_es=f"Comentario bajo el anuncio {anoun.title}.",
                verb_fr=f"Commentaire sous l'annonce {anoun.title}.",
                redirect="/",
                icon="chatbox-ellipses",
            )

            messages.success(request, _("You commented a post."))
            return Response({"message": "Comment added successfully."}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class AnnouncementCommentListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def get(self, request, anoun_id):
        try:
            announcement = Announcement.objects.get(id=anoun_id)
        except Announcement.DoesNotExist:
            return Response({"error": "Announcement not found."}, status=status.HTTP_404_NOT_FOUND)
        
        comments = AnnouncementComment.objects.filter(announcement_id=anoun_id).order_by('-created_at')
        serializer = AnnouncementCommentSerializer(comments, many=True)
        no_comments = not comments.exists()

        return Response({
            "comments": serializer.data,
            "no_comments": no_comments,
            "announcement": {
                "id": announcement.id,
                "title": announcement.title,
                "description": announcement.description,
                "created_at": announcement.created_at,
                "expire_date": announcement.expire_date,
            }
        }, status=status.HTTP_200_OK)



class AnnouncementCommentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, comment_id):
        try:
            comment = AnnouncementComment.objects.get(id=comment_id)
            anoun_id = comment.announcement_id.id
            comment.delete()
            messages.success(request, _("Comment deleted successfully!"))
            return Response({"message": "Comment deleted successfully!"}, status=status.HTTP_204_NO_CONTENT)
        except AnnouncementComment.DoesNotExist:
            return Response({"error": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)



class AnnouncementSingleAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def get(self, request, anoun_id):
        announcement = get_object_or_404(Announcement, id=anoun_id)

        # Check if the user has viewed the announcement
        announcement_view, created = AnnouncementView.objects.get_or_create(
            user=request.user, announcement=announcement
        )

        # Update the viewed status
        announcement_view.viewed = True
        announcement_view.save()

        serializer = AnnouncementSerializer(announcement)
        return Response(serializer.data, status=status.HTTP_200_OK)





class ActiontypeListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def get(self, request):
        action_types = Actiontype.objects.all()
        serializer = ActiontypeSerializer(action_types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class ActiontypeCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request):
        serializer = ActiontypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            messages.success(request, _("Action has been created successfully!"))
            return Response({"message": "Action created successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class ActiontypeUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request, act_id):
        if not request.data:
            return Response({"error": "No data provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        action = get_object_or_404(Actiontype, id=act_id)
        serializer = ActiontypeSerializer(action, data=request.data, partial=True)  # Allow partial updates

        if serializer.is_valid():
            act_type = serializer.validated_data.get("action_type")
            if act_type == "warning":
                serializer.validated_data["block_option"] = False

            serializer.save()
            messages.success(request, _("Action has been updated successfully!"))
            return Response({"message": "Action updated successfully!"}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ActiontypeDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def delete(self, request, act_id):
        if DisciplinaryAction.objects.filter(action=act_id).exists():
            return Response({
                "error": _("This action type is in use in disciplinary actions and cannot be deleted.")
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            Actiontype.objects.filter(id=act_id).delete()
            return Response({"message": _("Action has been deleted successfully!")}, status=status.HTTP_204_NO_CONTENT)


class ShiftRequestCommentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request, shift_id):
        if not request.data.get('comment'):  # Ensure 'comment' field is provided
            return Response({"error": "Comment is required."}, status=status.HTTP_400_BAD_REQUEST)

        shift = get_object_or_404(ShiftRequest, id=shift_id)
        emp = request.user.employee_get
        data = request.data
        data['employee_id'] = emp.id
        data['request_id'] = shift.id
        serializer = ShiftRequestCommentSerializer(data=data)

        if serializer.is_valid():
            comment = serializer.save()
            comments = ShiftRequestComment.objects.filter(request_id=shift_id).order_by('-created_at')
            no_comments = not comments.exists()
            messages.success(request, _("Comment added successfully!"))

            work_info = EmployeeWorkInformation.objects.filter(employee_id=shift.employee_id)
            if work_info.exists():
                rec = []
                if shift.employee_id.employee_work_info.reporting_manager_id:
                    if request.user.employee_get.id == shift.employee_id.id:
                        rec = [shift.employee_id.employee_work_info.reporting_manager_id.employee_user_id]
                    elif request.user.employee_get.id == shift.employee_id.employee_work_info.reporting_manager_id.id:
                        rec = [shift.employee_id.employee_user_id]
                    else:
                        rec = [
                            shift.employee_id.employee_user_id,
                            shift.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                        ]
                else:
                    rec = [shift.employee_id.employee_user_id]
                
                notify.send(
                    request.user.employee_get,
                    recipient=rec,
                    verb=f"{shift.employee_id}'s shift request has received a comment.",
                    verb_ar=f"تلقت طلب تحويل {shift.employee_id} تعليقًا.",
                    verb_de=f"{shift.employee_id}s Schichtantrag hat einen Kommentar erhalten.",
                    verb_es=f"La solicitud de turno de {shift.employee_id} ha recibido un comentario.",
                    verb_fr=f"La demande de changement de poste de {shift.employee_id} a reçu un commentaire.",
                    redirect=reverse("shift-request-view") + f"?id={shift.id}",
                    icon="chatbox-ellipses",
                )
            
            return Response({"message": "Comment added successfully!", "no_comments": no_comments}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






class ShiftRequestCommentListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, shift_id):
        shift_request = get_object_or_404(ShiftRequest, id=shift_id)
        comments = ShiftRequestComment.objects.filter(request_id=shift_id).order_by('-created_at')
        
        if not comments.exists():
            return Response({"message": "No comments available for this shift request."}, status=status.HTTP_200_OK)
        
        serializer = ShiftRequestCommentSerializer(comments, many=True)
        return Response({
            "comments": serializer.data,
            "shift_request": {
                "id": shift_request.id,
                "employee_id": shift_request.employee_id.id
            }
        }, status=status.HTTP_200_OK)






class DeleteShiftCommentFileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API to delete attachments and return updated comments.
    """

    def delete(self, request, *args, **kwargs):
        ids = request.query_params.getlist("ids")
        if not ids:
            return Response(
                {"detail": _("No file IDs provided.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Delete the files
        BaserequestFile.objects.filter(id__in=ids).delete()

        # Fetch and return updated comments
        shift_id = request.query_params.get("shift_id")
        if not shift_id:
            return Response(
                {"detail": _("Shift ID is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comments = ShiftRequestComment.objects.filter(request_id=shift_id).order_by("-created_at")
        comments_data = [
            {
                "id": comment.id,
                "text": getattr(comment, "text", "No content available"),  # Replace "text" with the correct field name
                "created_at": comment.created_at,
            }
            for comment in comments
        ]

        return Response(
            {
                "message": _("File deleted successfully"),
                "comments": comments_data,
            },
            status=status.HTTP_200_OK,
        )



class WorkTypeRequestCommentListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def get(self, request, work_type_id):
        work_type_request = get_object_or_404(WorkTypeRequest, id=work_type_id)
        comments = WorkTypeRequestComment.objects.filter(request_id=work_type_id).order_by('-created_at')
        
        if not comments.exists():
            return Response({"message": "No comments available for this work type request."}, status=status.HTTP_200_OK)
        
        serializer = WorkTypeRequestCommentSerializer(comments, many=True)
        return Response({
            "comments": serializer.data,
            "work_type_request": {
                "id": work_type_request.id,
                "employee_id": work_type_request.employee_id.id
            }
        }, status=status.HTTP_200_OK)

    




class DeleteWorkTypeCommentFileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API to delete attachment files from work type comments.
    """

    def delete(self, request, *args, **kwargs):
        """
        Delete files and return updated comments for a work type.
        """
        try:
            # Get list of file IDs to delete
            ids = request.query_params.getlist("ids")
            if not ids:
                return Response(
                    {"detail": _("No file IDs provided.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Delete the files
            BaserequestFile.objects.filter(id__in=ids).delete()

            # Get work_type_id to fetch updated comments
            work_type_id = request.query_params.get("work_type_id")
            if not work_type_id:
                return Response(
                    {"detail": _("Work type ID is required.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Fetch the updated comments
            comments = WorkTypeRequestComment.objects.filter(request_id=work_type_id)
            comments_data = [
                {
                    "id": comment.id,
                    "content": getattr(comment, "content", "No content available"),  # Replace "content" if needed
                    "created_at": comment.created_at,
                }
                for comment in comments
            ]

            return Response(
                {
                    "message": _("File deleted successfully."),
                    "comments": comments_data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DeleteShiftRequestCommentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    """
    API to delete a shift request comment.
    """

    def delete(self, request, comment_id, *args, **kwargs):
        """
        Delete a specific shift request comment.
        """
        try:
            # Find the comment to delete
            comment = ShiftRequestComment.objects.get(id=comment_id)
            comment.delete()

            return Response(
                {"message": _("Comment deleted successfully!")},
                status=status.HTTP_200_OK,
            )
        except ShiftRequestComment.DoesNotExist:
            return Response(
                {"detail": _("Comment not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)





class WorkTypeRequestCommentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, worktype_id):
        if not request.data.get('comment'):  # Ensure 'comment' field is provided
            return Response({"error": "Comment is required."}, status=status.HTTP_400_BAD_REQUEST)

        work_type = get_object_or_404(WorkTypeRequest, id=worktype_id)
        emp = request.user.employee_get

        data = request.data.copy()
        data['employee_id'] = emp.id
        data['request_id'] = work_type.id
        serializer = WorkTypeRequestCommentSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            comments = WorkTypeRequestComment.objects.filter(request_id=worktype_id).order_by('-created_at')
            messages.success(request, _("Comment added successfully!"))

            work_info = EmployeeWorkInformation.objects.filter(employee_id=work_type.employee_id)
            if work_info.exists() and work_type.employee_id.employee_work_info.reporting_manager_id:
                if request.user.employee_get.id == work_type.employee_id.id:
                    rec = work_type.employee_id.employee_work_info.reporting_manager_id.employee_user_id
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb=f"{work_type.employee_id}'s work type request has received a comment.",
                        redirect=reverse("work-type-request-view") + f"?id={work_type.id}",
                        icon="chatbox-ellipses"
                    )
                elif request.user.employee_get.id == work_type.employee_id.employee_work_info.reporting_manager_id.id:
                    rec = work_type.employee_id.employee_user_id
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb="Your work type request has received a comment.",
                        redirect=reverse("work-type-request-view") + f"?id={work_type.id}",
                        icon="chatbox-ellipses"
                    )
                else:
                    rec = [
                        work_type.employee_id.employee_user_id,
                        work_type.employee_id.employee_work_info.reporting_manager_id.employee_user_id,
                    ]
                    notify.send(
                        request.user.employee_get,
                        recipient=rec,
                        verb=f"{work_type.employee_id}'s work type request has received a comment.",
                        redirect=reverse("work-type-request-view") + f"?id={work_type.id}",
                        icon="chatbox-ellipses"
                    )
            else:
                rec = work_type.employee_id.employee_user_id
                notify.send(
                    request.user.employee_get,
                    recipient=rec,
                    verb="Your work type request has received a comment.",
                    redirect=reverse("work-type-request-view") + f"?id={work_type.id}",
                    icon="chatbox-ellipses"
                )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class WorkTypeRequestCommentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def delete(self, request, comment_id):
        comment = get_object_or_404(WorkTypeRequestComment, id=comment_id)
        comment.delete()
        return Response({"message": _("Comment deleted successfully!")}, status=status.HTTP_200_OK)


class EmployeeShiftScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        shift_schedule_exists = EmployeeShiftSchedule.objects.exists()
        shifts = EmployeeShift.objects.all()
        shift_serializer = EmployeeShiftSerializer(shifts, many=True)

        return Response({
            "shift_schedule": shift_schedule_exists,
            "shifts": shift_serializer.data
        }, status=status.HTTP_200_OK)


from django.core.exceptions import ValidationError
from django.http import QueryDict

class EmployeeShiftScheduleCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        required_fields = ['end_time', 'start_time', 'shift_id', 'day', 'minimum_working_hour']
        for field in required_fields:
            if field not in request.data:
                return Response({field: 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract and validate times
        start_time = datetime.strptime(request.data.get('start_time'), '%H:%M')
        end_time = datetime.strptime(request.data.get('end_time'), '%H:%M')
        minimum_working_hour = request.data.get('minimum_working_hour', "08:15")
        min_work_hours = datetime.strptime(minimum_working_hour, '%H:%M')

        # Validate working hours
        total_hours = (end_time - start_time).seconds / 3600
        min_hours = min_work_hours.hour + min_work_hours.minute / 60.0
        if total_hours < min_hours:
            return Response(
                {'detail': 'Total working hours cannot be less than the minimum required hours.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert `day` field to a list if needed
        if isinstance(request.data.get('day'), str):
            days = request.data['day'].split(',')
        else:
            days = request.data.get('day', [])

        # Prepare data for the form
        mutable_data = QueryDict('', mutable=True)
        mutable_data.update(request.data)
        mutable_data.setlist('day', days)

        # Validate and save the form
        form = EmployeeShiftScheduleForm(mutable_data)
        if form.is_valid():
            try:
                schedule = form.save(commit=False)
                schedule.save()
                form.save_m2m()  # Save ManyToMany relationships
                return Response({'detail': 'Employee Shift Schedule has been created successfully!'}, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({'detail': e.message_dict}, status=status.HTTP_400_BAD_REQUEST)

        # Return form errors
        return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)


class EmployeeShiftScheduleUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        employee_shift_schedule = get_object_or_404(EmployeeShiftSchedule, id=id)
        form = EmployeeShiftScheduleUpdateForm(request.POST, instance=employee_shift_schedule)
        if form.is_valid():
            form.save()
            return Response({"detail": "Shift schedule updated."}, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class RotatingShiftView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        rotating_shifts = RotatingShift.objects.all()
        serializer = RotatingShiftSerializer(rotating_shifts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RotatingShiftCreate(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        form = RotatingShiftForm(request.POST)
        if form.is_valid():
            form.save()
            return Response({"detail": "Rotating shift created."}, status=status.HTTP_201_CREATED)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class RotatingShiftUpdate(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        rotating_shift = get_object_or_404(RotatingShift, id=id)
        form = RotatingShiftForm(request.POST, instance=rotating_shift)
        if form.is_valid():
            form.save()
            return Response({"detail": "Rotating shift updated."}, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)




class ObjectDelete(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, obj_id, model, redirect_path=None, *args, **kwargs):
        delete_error = False
        try:
            instance = get_object_or_404(model, id=obj_id)
            instance.delete()
            return Response({"detail": "The object has been deleted successfully."}, status=status.HTTP_200_OK)
        except model.DoesNotExist:
            delete_error = True
            return Response({"error": f"{model._meta.verbose_name} not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError as e:
            model_verbose_names_set = set()
            for obj in e.protected_objects:
                model_verbose_names_set.add(obj._meta.verbose_name.capitalize())
            model_names_str = ", ".join(model_verbose_names_set)
            delete_error = True
            return Response({"error": f"This object is already in use for {model_names_str}."}, status=status.HTTP_400_BAD_REQUEST)
        


class EmployeeShiftDelete(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, obj_id):
        delete_error = False
        try:
            instance = get_object_or_404(EmployeeShift, id=obj_id)
            instance.delete()
            return Response({"detail": "The employee shift has been deleted successfully."}, status=status.HTTP_200_OK)
        except EmployeeShift.DoesNotExist:
            delete_error = True
            return Response({"error": f"Employee shift not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError as e:
            model_verbose_names_set = set()
            for obj in e.protected_objects:
                model_verbose_names_set.add(obj._meta.verbose_name.capitalize())
            model_names_str = ", ".join(model_verbose_names_set)
            delete_error = True
            return Response({"error": f"This employee shift is already in use for {model_names_str}."}, status=status.HTTP_400_BAD_REQUEST)




class EmployeeShiftDelete(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, obj_id):
        try:
            instance = get_object_or_404(EmployeeShift, id=obj_id)
            instance.delete()
            return Response({"detail": "The employee shift has been deleted successfully."}, status=status.HTTP_200_OK)
        except EmployeeShift.DoesNotExist:
            return Response({"error": "Employee shift not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError as e:
            model_verbose_names_set = set()
            for obj in e.protected_objects:
                model_verbose_names_set.add(obj._meta.verbose_name.capitalize())
            model_names_str = ", ".join(model_verbose_names_set)
            return Response({"error": f"This employee shift is already in use for {model_names_str}."}, status=status.HTTP_400_BAD_REQUEST)



class EmployeeTypeView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        types = EmployeeType.objects.all()
        serializer = EmployeeTypeSerializer(types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class EmployeeTypeCreate(APIView):
    def post(self, request):
        form = EmployeeTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return Response({"detail": "Employee type created."}, status=status.HTTP_201_CREATED)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)




class EmployeeTypeUpdate(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        employee_type = get_object_or_404(EmployeeType, id=id)
        form = EmployeeTypeForm(request.data, instance=employee_type)
        if form.is_valid():
            form.save()
            return Response({"detail": "Employee type updated."}, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class EmployeeTypeDelete(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, obj_id):
        try:
            instance = get_object_or_404(EmployeeType, id=obj_id)
            instance.delete()
            return Response({"detail": "The employee type has been deleted successfully."}, status=status.HTTP_200_OK)
        except EmployeeType.DoesNotExist:
            return Response({"error": "Employee type not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError as e:
            model_verbose_names_set = set()
            for obj in e.protected_objects:
                model_verbose_names_set.add(obj._meta.verbose_name.capitalize())
            model_names_str = ", ".join(model_verbose_names_set)
            return Response({"error": f"This employee type is already in use for {model_names_str}."}, status=status.HTTP_400_BAD_REQUEST)



class TagView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        This method is used to show Audit tags
        """
        audittags = AuditTag.objects.all()
        serializer = AuditTagSerializer(audittags, many=True)
        return Response(serializer.data)




class HelpdeskTagView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        This method is used to show Help desk tags
        """
        tags = Tags.objects.all()
        serializer = TagsSerializer(tags, many=True)
        return Response(serializer.data)
