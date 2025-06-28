from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404,redirect
from onboarding.models import OnboardingStage, Recruitment, Employee,OnboardingTask,CandidateTask,Candidate,CandidateStage,OnboardingPortal
from .serializers import OnboardingViewStageSerializer,CandidateSerializer,RecruitmentSerializer,OnboardingStageSerializer
from onboarding.views import stage_save,paginator_qry,onboarding_query_grouper,user_save
from onboarding.forms import OnboardingViewStageForm,OnboardingViewTaskForm,OnboardingTaskForm,OnboardingCandidateForm,UserCreationForm
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext as _
from django.urls import reverse
from notifications.signals import notify
from onboarding.filters import CandidateFilter
from django.db.models import ProtectedError
from base.models import HorillaMailTemplate
from recruitment.filters import CandidateReGroup,RecruitmentFilter
from recruitment.models import Candidate
from base.methods import get_key_instances,closest_numbers,sortby
from urllib.parse import parse_qs
from django.utils.translation import gettext as _
import json
from django.contrib import messages
from horilla.group_by import general_group_by
from django.contrib.auth.models import User
import random

class StageCreationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    """
    API view for creating onboarding stage.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    obj_id : recruitment id
    
    Returns:
    POST : return stage save function
    """

    def post(self, request, obj_id):
        try:
            recruitment = Recruitment.objects.get(id=obj_id)
            form = OnboardingViewStageForm(request.POST)
            if form.is_valid():
                stage_obj = form.save()
                stage_obj.employee_id.set(
                    Employee.objects.filter(id__in=form.data.getlist("employee_id"))
                )
                response_data = {
                    "stage": stage_obj.id,
                    "message": "Stage created successfully",
                    # Add other necessary details here
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except Recruitment.DoesNotExist:
            return Response({"error": "Recruitment object not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class StageUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    """
    API view for updating onboarding stage.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    stage_id : stage id
    recruitment_id : recruitment id
    
    Returns:
    POST : return onboarding view or errors
    """

    def post(self, request, stage_id, recruitment_id):
        try:
            onboarding_stage = OnboardingStage.objects.get(id=stage_id)
            form = OnboardingViewStageForm(request.POST, instance=onboarding_stage)
            if form.is_valid():
                stage = form.save()
                stage.employee_id.set(
                    Employee.objects.filter(id__in=form.data.getlist("employee_id"))
                )
                # Send notifications
                users = [employee.employee_user_id for employee in stage.employee_id.all()]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb="You are chosen as onboarding stage manager",
                    verb_ar="لقد تم اختيارك كمدير مرحلة التدريب.",
                    verb_de="Sie wurden als Onboarding-Stage-Manager ausgewählt.",
                    verb_es="Ha sido seleccionado/a como responsable de etapa de incorporación.",
                    verb_fr="Vous avez été choisi(e) en tant que responsable de l'étape d'intégration.",
                    icon="people-circle",
                    redirect=reverse("onboarding-view"),
                )
                response_data = {
                    "stage": stage.id,
                    "message": _("Stage is updated successfully.."),
                    # Add other necessary details here
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except OnboardingStage.DoesNotExist:
            return Response({"error": "OnboardingStage object not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StageDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """
    API view for deleting onboarding stage.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    stage_id : stage id
    
    Returns:
    DELETE : return success or error message
    """

    def delete(self, request, stage_id):
        try:
            onboarding_stage = OnboardingStage.objects.get(id=stage_id)
            onboarding_stage.delete()
            response_data = {
                "message": _("The stage deleted successfully..."),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except OnboardingStage.DoesNotExist:
            return Response({"error": _("Stage not found.")}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError:
            return Response({"error": _("There are candidates in this stage...")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



import logging
logger = logging.getLogger(__name__)

class TaskCreationAPIView(APIView):
    """
    API view for creating onboarding task.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    
    Returns:
    POST : return onboarding view or errors
    """
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            stage_id = request.data.get("stage_id")
            logger.info(f"Received stage_id: {stage_id}")
            
            if not stage_id:
                return Response({"error": "stage_id is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            stage = OnboardingStage.objects.get(id=stage_id)
            form = OnboardingViewTaskForm(request.data, initial={"stage_id": stage})

            if form.is_valid():
                candidates = form.cleaned_data["candidates"]
                stage_id = form.cleaned_data["stage_id"]
                managers = form.cleaned_data["managers"]
                title = form.cleaned_data["task_title"]
                onboarding_task = OnboardingTask(task_title=title, stage_id=stage_id)
                onboarding_task.save()
                onboarding_task.employee_id.set(managers)
                onboarding_task.candidates.set(candidates)
                if candidates:
                    for cand in candidates:
                        task = CandidateTask(
                            candidate_id=cand,
                            stage_id=stage_id,
                            onboarding_task_id=onboarding_task,
                        )
                        task.save()
                users = [
                    manager.employee_user_id
                    for manager in onboarding_task.employee_id.all()
                ]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb="You are chosen as an onboarding task manager",
                    verb_ar="لقد تم اختيارك كمدير مهام التدريب.",
                    verb_de="Sie wurden als Onboarding-Aufgabenmanager ausgewählt.",
                    verb_es="Ha sido seleccionado/a como responsable de tareas de incorporación.",
                    verb_fr="Vous avez été choisi(e) en tant que responsable des tâches d'intégration.",
                    icon="people-circle",
                    redirect=reverse("onboarding-view"),
                )

                response_data = {
                    "task": onboarding_task.id,
                    "message": _("New task created successfully..."),
                    # Add other necessary details here
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        except OnboardingStage.DoesNotExist:
            logger.error(f"OnboardingStage with id {stage_id} not found")
            return Response({"error": "OnboardingStage object not found"}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError:
            logger.error(f"ProtectedError: There are candidates in stage {stage_id}")
            return Response({"error": "There are candidates in this stage..."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class TaskUpdateAPIView(APIView):
    """
    API view for updating onboarding task.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    task_id : task id
    
    Returns:
    POST : return onboarding view or errors
    """
    
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        try:
            onboarding_task = OnboardingTask.objects.get(id=task_id)
            form = OnboardingTaskForm(request.data, instance=onboarding_task)
            if form.is_valid():
                task = form.save()
                task.employee_id.set(
                    Employee.objects.filter(id__in=form.data.getlist("employee_id"))
                )
                for cand_task in onboarding_task.candidatetask_set.all():
                    if cand_task.candidate_id not in task.candidates.all():
                        cand_task.delete()
                    else:
                        cand_task.stage_id = task.stage_id

                users = [employee.employee_user_id for employee in task.employee_id.all()]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb="You are chosen as an onboarding task manager",
                    verb_ar="لقد تم اختيارك كمدير مهام التدريب.",
                    verb_de="Sie wurden als Onboarding-Aufgabenmanager ausgewählt.",
                    verb_es="Ha sido seleccionado/a como responsable de tareas de incorporación.",
                    verb_fr="Vous avez été choisi(e) en tant que responsable des tâches d'intégration.",
                    icon="people-circle",
                    redirect=reverse("onboarding-view"),
                )
                
                response_data = {
                    "task": task.id,
                    "message": _("Task updated successfully.."),
                    # Add other necessary details here
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except OnboardingTask.DoesNotExist:
            return Response({"error": "OnboardingTask object not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class TaskDeleteAPIView(APIView):
    """
    API view for deleting onboarding task.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    task_id : task id
    
    Returns:
    DELETE : return success or error message
    """
    
    permission_classes = [IsAuthenticated]

    def delete(self, request, task_id):
        try:
            task = OnboardingTask.objects.get(id=task_id)
            task.delete()
            response_data = {
                "message": _("The task deleted successfully..."),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except OnboardingTask.DoesNotExist:
            return Response({"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError:
            return Response({"error": "You cannot delete this task because some candidates are associated with it."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class CandidateCreationAPIView(APIView):
    """
    API view for creating hired candidates.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    
    Returns:
    POST : return candidate view or errors
    """
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            form = OnboardingCandidateForm(request.data, request.FILES)
            if form.is_valid():
                candidate = form.save()
                candidate.hired = True
                candidate.save()
                response_data = {
                    "message": _("New candidate created successfully.."),
                    "candidate_id": candidate.id,
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                # Check for specific field errors
                errors = {field: form.errors[field] for field in form.errors}
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.http import JsonResponse


class CandidateUpdateAPIView(APIView):
    """
    API to update hired candidates using a Django form.
    
    Parameters:
    obj_id : recruitment id
    """

    def post(self, request, obj_id):
        """
        Handle POST requests to update candidate details.
        """
        try:
            # Fetch candidate by obj_id
            candidate = Candidate.objects.get(id=obj_id)
        except Candidate.DoesNotExist:
            return JsonResponse({"error": "Candidate not found"}, status=404)

        # Initialize form with the candidate instance and request data
        form = OnboardingCandidateForm(request.POST, request.FILES, instance=candidate)
        
        if form.is_valid():
            try:
                # Save the form data
                form.save()
                return JsonResponse({"message": "Candidate detail is updated successfully."}, status=200)
            except ValidationError as e:
                return JsonResponse({"error": str(e)}, status=400)
        else:
            return JsonResponse({"error": form.errors}, status=400)
        
        
class CandidatesViewAPIView(APIView):
    """
    API view for viewing hired candidates.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    
    Returns:
    GET : return candidate view or errors
    """
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            queryset = Candidate.objects.filter(
                is_active=True,
                hired=True,
                recruitment_id__closed=False,
            )
            candidate_filter_obj = CandidateFilter(request.GET, queryset)
            previous_data = request.GET.urlencode()
            page_number = request.GET.get("page")
            page_obj = paginator_qry(candidate_filter_obj.qs, page_number)
            mail_templates = HorillaMailTemplate.objects.all()
            data_dict = parse_qs(previous_data)
            get_key_instances(Candidate, data_dict)
            
            candidates_data = [
                {
                    "id": candidate.id,
                    "name": candidate.name,
                    "email": candidate.email,
                    # Add other necessary fields
                }
                for candidate in page_obj
            ]
            
            response_data = {
                "candidates": candidates_data,
                "form": candidate_filter_obj.form.data,
                "pd": previous_data,
                "gp_fields": CandidateReGroup.fields,
                "mail_templates": [template.title for template in mail_templates],  # Replace 'title' with the correct attribute
                "hired_candidates": queryset.count(),
                "filter_dict": data_dict,
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.utils.translation import gettext as _
import json

class CandidateSingleViewAPIView(APIView):
    """
    API view for individual view of onboarding candidates.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    id : candidate id
    
    Returns:
    GET : return candidate view or errors
    """
    
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            candidate = get_object_or_404(Candidate, id=id)
            if not CandidateStage.objects.filter(candidate_id=candidate).exists():
                try:
                    onboarding_stage = OnboardingStage.objects.filter(
                        recruitment_id=candidate.recruitment_id
                    ).order_by("sequence")[0]
                    CandidateStage(
                        candidate_id=candidate, onboarding_stage_id=onboarding_stage
                    ).save()
                except Exception:
                    return Response({
                        "error": _("%(recruitment)s has no stage..") % {"recruitment": candidate.recruitment_id}
                    }, status=status.HTTP_400_BAD_REQUEST)
                if tasks := OnboardingTask.objects.filter(
                    recruitment_id=candidate.recruitment_id
                ):
                    for task in tasks:
                        if not CandidateTask.objects.filter(
                            candidate_id=candidate, onboarding_task_id=task
                        ).exists():
                            CandidateTask(
                                candidate_id=candidate, onboarding_task_id=task
                            ).save()

            recruitment = candidate.recruitment_id
            choices = CandidateTask.choice

            context = {
                "recruitment": recruitment.id,
                "choices": choices,
                "candidate": {
                    "id": candidate.id,
                    "name": candidate.name,
                    "email": candidate.email,
                    # Add other necessary fields
                },
                "single_view": True,
            }

            requests_ids_json = request.GET.get("requests_ids")
            if requests_ids_json:
                requests_ids = json.loads(requests_ids_json)
                previous_id, next_id = closest_numbers(requests_ids, id)
                context["requests_ids"] = requests_ids_json
                context["previous"] = previous_id
                context["next"] = next_id

            return Response(context, status=status.HTTP_200_OK)
        
        except Candidate.DoesNotExist:
            return Response({"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class CandidateDeleteAPIView(APIView):
    """
    API view for deleting hired candidates.
    
    Parameters:
    request (HttpRequest): The HTTP request object.
    obj_id : recruitment id
    
    Returns:
    DELETE : return success or error message
    """
    
    permission_classes = [IsAuthenticated]

    def delete(self, request, obj_id):
        try:
            candidate = get_object_or_404(Candidate, id=obj_id)
            candidate.delete()
            return Response({"message": _("Candidate deleted successfully..")}, status=status.HTTP_200_OK)
        except Candidate.DoesNotExist:
            return Response({"error": _("Candidate not found.")}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError as e:
            models_verbose_name_sets = set()
            for obj in e.protected_objects:
                models_verbose_name_sets.add(_(obj._meta.verbose_name))
            models_verbose_name_str = (", ").join(models_verbose_name_sets)
            return Response({
                "error": _(
                    "You cannot delete this candidate. The candidate is included in the {}".format(
                        models_verbose_name_str
                    )
                )
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from rest_framework.pagination import PageNumberPagination
class HiredCandidateAPIView(APIView):
    """
    API to view hired candidates with filtering and pagination.
    """

    def get(self, request):
        previous_data = request.GET.urlencode()

        # Fetch candidates that are hired and not in closed recruitment
        candidates = Candidate.objects.filter(
            hired=True,
            recruitment_id__closed=False,
        )

        # Apply active filter if 'is_active' is not provided
        if request.GET.get("is_active") is None:
            candidates = candidates.filter(is_active=True)

        # Apply custom filters using CandidateFilter
        filtered_candidates = CandidateFilter(request.GET, queryset=candidates).qs

        # Paginate the results
        paginator = PageNumberPagination()
        paginator.page_size = 10  # Set the page size
        result_page = paginator.paginate_queryset(filtered_candidates, request)

        # Serialize the data
        serializer = CandidateSerializer(result_page, many=True)

        # Return paginated and filtered data
        return paginator.get_paginated_response({
            "data": serializer.data,
            "pd": previous_data,
        })



class CandidateFilterAPIView(APIView):
    """
    API to filter hired candidates with filtering and pagination.
    """

    def get(self, request):
        # Fetch candidates that are active, hired, and not in closed recruitment
        queryset = Candidate.objects.filter(
            is_active=True,
            hired=True,
            recruitment_id__closed=False,
        )

        # Apply custom filters using CandidateFilter
        candidates = CandidateFilter(request.GET, queryset).qs
        previous_data = request.GET.urlencode()
        
        # Parse query parameters for custom functionalities
        data_dict = parse_qs(previous_data)
        get_key_instances(Candidate, data_dict)
        
        # Apply sorting if 'orderby' parameter is provided
        candidates = sortby(request, candidates, "orderby")
        
        # Apply group by functionality if 'field' is provided
        field = request.GET.get("field")
        if field:
            candidates = general_group_by(candidates, field, request.GET.get("page"), "page")

        # Paginate the results using paginator_qry
        page_number = request.GET.get("page")
        paginated_candidates = paginator_qry(candidates, page_number)
        
        # Serialize the data
        serializer = CandidateSerializer(paginated_candidates, many=True)
        
        # Return paginated, filtered, and grouped data
        return JsonResponse({
            "candidates": serializer.data,
            "pd": previous_data,
            "filter_dict": data_dict,
        }, safe=False)



from django.core.paginator import Paginator

class OnboardingView(APIView):
    """
    API view for onboarding main view.
    """
    
    def get(self, request):
        """
        Handles GET requests to return filtered recruitments and other related data.
        """
        filter_obj = RecruitmentFilter(request.GET)
        recruitments = filter_obj.qs
        if not request.user.has_perm("onboarding.view_candidatestage"):
            recruitments = recruitments.filter(
                is_active=True, recruitment_managers__in=[request.user.employee_get]
            ) | recruitments.filter(
                onboarding_stage__employee_id__in=[request.user.employee_get]
            )
        employee_tasks = request.user.employee_get.onboarding_task.all()
        for task in employee_tasks:
            if task.stage_id and task.stage_id.recruitment_id not in recruitments:
                recruitments = recruitments | filter_obj.qs.filter(
                    id=task.stage_id.recruitment_id.id
                )
        recruitments = recruitments.filter(is_active=True).distinct()
        status = request.GET.get("closed")
        if not status:
            recruitments = recruitments.filter(closed=False)

        onboarding_stages = OnboardingStage.objects.all()
        choices = CandidateTask.choice
        paginator = Paginator(recruitments.order_by("id"), 4)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        groups = onboarding_query_grouper(request, page_obj)
        for item in groups:
            setattr(item["recruitment"], "stages", item["stages"])
            setattr(item["recruitment"], "employee_ids", item["employee_ids"])
        filter_dict = parse_qs(request.GET.urlencode())
        for key, val in filter_dict.copy().items():
            if val[0] == "unknown" or key == "view":
                del filter_dict[key]

        response_data = {
            "recruitments": RecruitmentSerializer(page_obj, many=True).data,
            "rec_filter_obj": RecruitmentSerializer(filter_obj.qs, many=True).data,
            "onboarding_stages": OnboardingStageSerializer(onboarding_stages, many=True).data,
            "choices": choices,
            "filter_dict": filter_dict,
            "status": status,
            "previous_data": request.GET.urlencode(),
        }

        return Response(response_data)


class CandidateTaskUpdateView(APIView):
    """
    API view for updating candidate task.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, taskId):
        """
        Handles POST requests to update candidate task.
        """
        try:
            status = request.POST.get("status")
            if request.POST.get("single_view"):
                candidate_task = get_object_or_404(CandidateTask, id=taskId)
            else:
                canId = request.POST.get("candId")
                onboarding_task = get_object_or_404(OnboardingTask, id=taskId)
                candidate = get_object_or_404(Candidate, id=canId)
                candidate_task = CandidateTask.objects.filter(
                    candidate_id=candidate, onboarding_task_id=onboarding_task
                ).first()
            candidate_task.status = status
            candidate_task.save()

            users = [
                employee.employee_user_id
                for employee in candidate_task.onboarding_task_id.employee_id.all()
            ]
            notify.send(
                request.user.employee_get,
                recipient=users,
                verb=f"The task {candidate_task.onboarding_task_id} of {candidate_task.candidate_id} was updated to {candidate_task.status}.",
                verb_ar=f"تم تحديث المهمة {candidate_task.onboarding_task_id} للمرشح {candidate_task.candidate_id} إلى {candidate_task.status}.",
                verb_de=f"Die Aufgabe {candidate_task.onboarding_task_id} des Kandidaten {candidate_task.candidate_id} wurde auf {candidate_task.status} aktualisiert.",
                verb_es=f"La tarea {candidate_task.onboarding_task_id} del candidato {candidate_task.candidate_id} se ha actualizado a {candidate_task.status}.",
                verb_fr=f"La tâche {candidate_task.onboarding_task_id} du candidat {candidate_task.candidate_id} a été mise à jour à {candidate_task.status}.",
                icon="people-circle",
                redirect=reverse("onboarding-view"),
            )

            return Response({"message": _("Candidate onboarding task updated"), "type": "success"})
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class GetStatusView(APIView):
    """
    API view that returns the status of a candidate task.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        """
        Handles POST requests to return the status of a candidate task.
        """
        try:
            cand_id = request.GET.get("cand_id")
            cand_stage = request.GET.get("cand_stage")
            cand_stage_obj = get_object_or_404(CandidateStage, id=cand_stage)
            onboarding_task = get_object_or_404(OnboardingTask, id=task_id)
            candidate = get_object_or_404(Candidate, id=cand_id)
            candidate_task = CandidateTask.objects.filter(
                candidate_id=candidate, onboarding_task_id=onboarding_task
            ).first()
            status = candidate_task.status

            response_data = {
                "status": status,
                "task": onboarding_task.id,
                "candidate": cand_stage_obj.id,
                "second_load": True,
                "choices": CandidateTask.choice,
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class AssignTaskView(APIView):
    """
    API view for assigning an onboarding task to a candidate.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        """
        Handles POST requests to assign an onboarding task to a candidate.
        """
        try:
            stage_id = request.GET.get("stage_id")
            cand_id = request.GET.get("cand_id")
            cand_stage = request.GET.get("cand_stage")
            cand_stage_obj = get_object_or_404(CandidateStage, id=cand_stage)
            onboarding_task = get_object_or_404(OnboardingTask, id=task_id)
            candidate = get_object_or_404(Candidate, id=cand_id)
            onboarding_stage = get_object_or_404(OnboardingStage, id=stage_id)
            
            cand_task, created = CandidateTask.objects.get_or_create(
                candidate_id=candidate,
                stage_id=onboarding_stage,
                onboarding_task_id=onboarding_task,
            )
            cand_task.save()
            onboarding_task.candidates.add(candidate)

            response_data = {
                "status": cand_task.status,
                "task": onboarding_task.id,
                "candidate": cand_stage_obj.id,
                "second_load": True,
                "choices": CandidateTask.choice,
            }
            
            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class CandidateStageUpdateView(APIView):
    """
    API view for updating candidate stage.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, candidate_id, recruitment_id):
        """
        Handles POST requests to update candidate stage.
        """
        try:
            stage_id = request.POST.get("stage")
            recruitments = get_object_or_404(Recruitment, id=recruitment_id)
            stage = get_object_or_404(OnboardingStage, id=stage_id)
            candidate = get_object_or_404(Candidate, id=candidate_id)
            candidate_stage = get_object_or_404(CandidateStage, candidate_id=candidate)
            candidate_stage.onboarding_stage_id = stage
            candidate_stage.save()

            onboarding_stages = OnboardingStage.objects.all()
            choices = CandidateTask.choice
            users = [
                employee.employee_user_id
                for employee in candidate_stage.onboarding_stage_id.employee_id.all()
            ]
            
            if request.POST.get("is_ajax") is None:
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb=f"The stage of {candidate_stage.candidate_id} \
                        was updated to {candidate_stage.onboarding_stage_id}.",
                    verb_ar=f"تم تحديث مرحلة المرشح {candidate_stage.candidate_id} إلى {candidate_stage.onboarding_stage_id}.",
                    verb_de=f"Die Phase des Kandidaten {candidate_stage.candidate_id} wurde auf {candidate_stage.onboarding_stage_id} aktualisiert.",
                    verb_es=f"La etapa del candidato {candidate_stage.candidate_id} se ha actualizado a {candidate_stage.onboarding_stage_id}.",
                    verb_fr=f"L'étape du candidat {candidate_stage.candidate_id} a été mise à jour à {candidate_stage.onboarding_stage_id}.",
                    icon="people-circle",
                    redirect=reverse("onboarding-view"),
                )

            groups = onboarding_query_grouper(request, recruitments)
            for item in groups:
                setattr(item["recruitment"], "stages", item["stages"])
                return Response({
                    "recruitment": groups[0]["recruitment"],
                    "onboarding_stages": onboarding_stages,
                    "choices": choices,
                })
            
            return Response({"message": _("Candidate onboarding stage updated"), "type": "success"})
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class CandidateStageBulkUpdateView(APIView):
    """
    API view for bulk updating candidate stages.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to bulk update candidate stages.
        """
        try:
            candiate_ids = request.POST["ids"]
            recruitment_id = request.POST["recruitment"]
            candidate_id_list = json.loads(candiate_ids)
            stage = request.POST["stage"]
            onboarding_stages = OnboardingStage.objects.all()
            recruitments = Recruitment.objects.filter(id=int(recruitment_id))

            choices = CandidateTask.choice

            CandidateStage.objects.filter(candidate_id__id__in=candidate_id_list).update(
                onboarding_stage_id=stage
            )
            type = "info"
            message = "No candidates selected"
            if candidate_id_list:
                type = "success"
                message = "Candidate stage updated successfully"

            groups = onboarding_query_grouper(request, recruitments)
            for item in groups:
                setattr(item["recruitment"], "stages", item["stages"])

            response_data = {
                "recruitment": RecruitmentSerializer(groups[0]["recruitment"]).data,
                "onboarding_stages": OnboardingStageSerializer(onboarding_stages, many=True).data,
                "choices": choices,
                "message": message,
                "type": type,
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class CandidateTaskBulkUpdateView(APIView):
    """
    API view for bulk updating candidate tasks.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to bulk update candidate tasks.
        """
        try:
            candidate_ids = request.POST["ids"]
            candidate_id_list = json.loads(candidate_ids)
            task = request.POST["task"]
            status = request.POST["status"]

            count = CandidateTask.objects.filter(
                candidate_id__id__in=candidate_id_list, onboarding_task_id=task
            ).update(status=status)
            
            response_data = {
                "message": "Candidate task status updated successfully",
                "type": "success",
                "count": count,
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



import random


class OnboardCandidateChartView(APIView):
    """
    API view to show onboard started candidates in recruitments.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return onboard candidate chart data.
        """
        try:
            labels = []
            data = []
            background_color = []
            border_color = []
            recruitments = Recruitment.objects.filter(closed=False, is_active=True)
            for recruitment in recruitments:
                red = random.randint(0, 255)
                green = random.randint(0, 255)
                blue = random.randint(0, 255)
                background_color.append(f"rgba({red}, {green}, {blue}, 0.2)")
                border_color.append(f"rgb({red}, {green}, {blue})")
                labels.append(recruitment.title)
                data.append(recruitment.candidate.filter(start_onboard=True).count())
            
            response_data = {
                "labels": labels,
                "data": data,
                "background_color": background_color,
                "border_color": border_color,
                "message": "No data Found...",
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class UpdateJoiningView(APIView):
    """
    API view to update the joining date of a candidate.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update the joining date of a candidate.
        """
        try:
            cand_id = request.POST["candId"]
            date = request.POST["date"]
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            candidate_obj.joining_date = date
            candidate_obj.save()

            return Response(
                {
                    "type": "success",
                    "message": _("{candidate}'s Date of joining updated successfully").format(
                        candidate=candidate_obj.name
                    ),
                }
            )
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class ViewDashboardView(APIView):
    """
    API view to show the dashboard with recruitments and candidates data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return dashboard data.
        """
        try:
            recruitment = Recruitment.objects.all().values_list("title", flat=True)
            candidates = Candidate.objects.all()
            hired = candidates.filter(start_onboard=True)
            onboard_candidates = candidates.filter(start_onboard=True)
            job_positions = onboard_candidates.values_list(
                "job_position_id__job_position", flat=True
            )

            response_data = {
                "recruitment": list(recruitment),
                "candidates": CandidateSerializer(candidates, many=True).data,
                "hired": CandidateSerializer(hired, many=True).data,
                "onboard_candidates": CandidateSerializer(onboard_candidates, many=True).data,
                "job_positions": list(set(job_positions)),
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class DashboardStageChartView(APIView):
    """
    API view to show onboard started candidates in recruitments.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return dashboard stage chart data.
        """
        try:
            recruitment = request.GET.get("recruitment")
            labels = OnboardingStage.objects.filter(
                recruitment_id__title=recruitment
            ).values_list("stage_title", flat=True)
            labels = list(labels)
            candidate_counts = []
            border_color = []
            background_color = []
            for label in labels:
                red = random.randint(0, 255)
                green = random.randint(0, 255)
                blue = random.randint(0, 255)
                background_color.append(f"rgba({red}, {green}, {blue}, 0.3)")
                border_color.append(f"rgb({red}, {green}, {blue})")
                count = CandidateStage.objects.filter(
                    onboarding_stage_id__stage_title=label,
                    onboarding_stage_id__recruitment_id__title=recruitment,
                ).count()
                candidate_counts.append(count)

            response_data = {
                "labels": labels,
                "data": candidate_counts,
                "recruitment": recruitment,
                "background_color": background_color,
                "border_color": border_color,
                "message": _("No candidates started onboarding...."),
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class CandidateSequenceUpdateView(APIView):
    """
    API view to update the sequence of candidates.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update the sequence of candidates.
        """
        try:
            sequence_data = json.loads(request.POST["sequenceData"])
            updated = False
            for cand_id, seq in sequence_data.items():
                cand = get_object_or_404(CandidateStage, id=cand_id)
                if cand.sequence != seq:
                    cand.sequence = seq
                    cand.save()
                    updated = True
            if updated:
                return Response(
                    {"message": _("Candidate sequence updated"), "type": "info"}
                )
            return Response({"type": "fail"})
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class StageSequenceUpdateView(APIView):
    """
    API view to update the sequence of stages.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update the sequence of stages.
        """
        try:
            sequence_data = json.loads(request.POST["sequenceData"])
            updated = False

            for stage_id, seq in sequence_data.items():
                stage = get_object_or_404(OnboardingStage, id=stage_id)
                if stage.sequence != seq:
                    stage.sequence = seq
                    stage.save()
                    updated = True

            if updated:
                return Response({"type": "success", "message": _("Stage sequence updated")})
            return Response({"type": "fail"})
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class StageNameUpdateView(APIView):
    """
    API view to update the name of a recruitment stage.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, stage_id):
        """
        Handles POST requests to update the name of a recruitment stage.
        """
        try:
            stage_obj = get_object_or_404(OnboardingStage, id=stage_id)
            stage_obj.stage_title = request.POST["stage"]
            stage_obj.save()
            message = _("The stage title has been updated successfully")
            return Response(
                {
                    "message": message,
                    "type": "success"
                }
            )
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class TaskReportView(APIView):
    """
    API view to show the task report.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return task report data.
        """
        try:
            employee_id = request.GET.get("employee_id")
            if not employee_id:
                employee_id = request.user.employee_get.id
            my_tasks = OnboardingTask.objects.filter(
                employee_id__id=employee_id,
                candidates__is_active=True,
                candidates__recruitment_id__closed=False,
            ).distinct()
            tasks = []
            for task in my_tasks:
                tasks.append(
                    {
                        "task": task.id,
                        "total_candidates": task.candidatetask_set.count(),
                        "todo": task.candidatetask_set.filter(status="todo").count(),
                        "scheduled": task.candidatetask_set.filter(status="scheduled").count(),
                        "ongoing": task.candidatetask_set.filter(status="ongoing").count(),
                        "stuck": task.candidatetask_set.filter(status="stuck").count(),
                        "done": task.candidatetask_set.filter(status="done").count(),
                    }
                )
            
            response_data = {
                "tasks": tasks,
                "message": _("Task report generated successfully"),
            }
            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)







class CandidateTasksStatusView(APIView):
    """
    API view to render template to show the onboarding tasks.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return the onboarding tasks.
        """
        try:
            task_id = request.GET.get("task_id")
            if not task_id:
                return Response({"detail": "task_id parameter is required"}, status=400)

            candidate_tasks = CandidateTask.objects.filter(onboarding_task_id__id=task_id)
            if not candidate_tasks.exists():
                return Response({"detail": "No CandidateTasks found for the given task_id"}, status=404)

            response_data = {
                "candidate_tasks": [
                    {
                        "id": task.id,
                        "candidate_id": task.candidate_id.id,
                        "status": task.status,
                        "onboarding_task_id": task.onboarding_task_id.id,
                    }
                    for task in candidate_tasks
                ]
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class ChangeTaskStatusView(APIView):
    """
    API view to update the status of a candidate task.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update the status of a candidate task.
        """
        try:
            task_id = request.POST.get("task_id")
            status = request.POST.get("status")
            valid_statuses = ["todo", "scheduled", "ongoing", "stuck", "done"]

            if not task_id:
                return Response({"detail": "task_id parameter is required"}, status=400)
            if not status:
                return Response({"detail": "status parameter is required"}, status=400)
            if status not in valid_statuses:
                return Response({"detail": "Invalid status"}, status=400)
            
            candidate_task = get_object_or_404(CandidateTask, id=task_id)
            candidate_task.status = status
            candidate_task.save()
            return Response({"message": "Success"})
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class CandidateSelectView(APIView):
    """
    API view to select all candidates.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to select all candidates.
        """
        try:
            page_number = request.GET.get("page")

            employees = Candidate.objects.filter(
                hired=True,
                recruitment_id__closed=False,
                is_active=True,
            )

            employee_ids = [str(emp.id) for emp in employees]
            total_count = employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}

            return Response(context)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)


  # Ensure you have this import based on your filter implementation

class CandidateSelectFilterView(APIView):
    """
    API view to select all filtered candidates.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to select all filtered candidates.
        """
        try:
            page_number = request.GET.get("page")
            filtered = request.GET.get("filter")
            filters = json.loads(filtered) if filtered else {}

            if page_number == "all":
                candidate_filter = CandidateFilter(
                    filters,
                    queryset=Candidate.objects.filter(
                        hired=True,
                        recruitment_id__closed=False,
                        is_active=True,
                    ),
                )

                # Get the filtered queryset
                filtered_candidates = candidate_filter.qs

                employee_ids = [str(emp.id) for emp in filtered_candidates]
                total_count = filtered_candidates.count()

                context = {"employee_ids": employee_ids, "total_count": total_count}

                return Response(context)
            return Response({"detail": "Invalid page number"}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)
