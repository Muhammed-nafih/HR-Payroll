from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import render
from recruitment.views.views import is_stagemanager, is_recruitmentmanager
from .serializers import (
RecruitmentSerializer,
RecruitmentViewSerializer,
RecruitmentSearchSerializer,
CandidateSerializer, 
StageSerializer,
StageNoteSerializer,
CandidateHistorySerializer,
JobPositionSerializer,
HorillaMailTemplateSerializer,
InterviewScheduleSerializer,RecruitmentSurveySerializer, SurveyTemplateSerializer,SkillZoneSerializer,SkillZoneCandidateSerializer,

)
from recruitment.filters import RecruitmentFilter, StageFilter, CandidateFilter,InterviewFilter,SurveyFilter,SurveyTemplateFilter,SkillZoneCandFilter, SkillZoneFilter
from recruitment.forms import RecruitmentCreationForm, RecruitmentDropDownForm,  StageDropDownForm,StageCreationForm,AddCandidateForm, CandidateCreationForm,StageNoteForm,StageNoteUpdateForm,ScheduleInterviewForm,CandidateExportForm,SurveyPreviewForm,SurveyForm,QuestionForm,TemplateForm,AddQuestionForm,SkillZoneCreateForm,SkillZoneCandidateForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import permission_required, login_required
from django.utils.decorators import method_decorator
from recruitment.models import Recruitment,InterviewSchedule
from django.utils.translation import gettext as _
from recruitment.models import Recruitment, Employee, Stage, Candidate, StageNote,JobPosition,SurveyTemplate,RecruitmentSurvey, SkillZone, SkillZoneCandidate,CandidateRating,StageFiles
from notifications.signals import notify
from base.methods import sortby
from recruitment.methods import recruitment_manages
from django.core.paginator import Paginator
import contextlib
from horilla.decorators import hx_request_required
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import PermissionRequiredMixin
import json
from recruitment.views.views import stage_type_candidate_count, get_key_instances,paginator_qry_recruitment_limited,group_by_queryset,export_data,generate_pdf
from django.core.cache import cache as CACHE
from base.models import HorillaMailTemplate,Department
from base.forms import MailTemplateForm
from horilla.group_by import general_group_by
from employee.models import EmployeeWorkInformation
from django.core import serializers
from base.methods import get_pagination,closest_numbers







def paginator_qry(qryset, page_number):
    """
    This method is used to paginate queryset
    """
    paginator = Paginator(qryset, 50)
    qryset = paginator.get_page(page_number)
    return qryset





class RecruitmentcreateView(APIView):
    """
    API view for creating recruitment.
    """
    permission_classes = [IsAuthenticated]



    def post(self, request):
        """
        Handles POST requests to create a recruitment.
        """
        form = RecruitmentCreationForm(request.POST)
        if form.is_valid():
            recruitment_obj = form.save()
            recruitment_obj.recruitment_managers.set(
                Employee.objects.filter(
                    id__in=form.data.getlist("recruitment_managers")
                )
            )
            recruitment_obj.open_positions.set(
                JobPosition.objects.filter(id__in=form.data.getlist("open_positions"))
            )
            for survey in form.cleaned_data["survey_templates"]:
                for sur in survey.recruitmentsurvey_set.all():
                    sur.recruitment_ids.add(recruitment_obj)
            messages.success(request, _("Recruitment added."))
            with contextlib.suppress(Exception):
                managers = recruitment_obj.recruitment_managers.select_related(
                    "employee_user_id"
                )
                users = [employee.employee_user_id for employee in managers]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb="You are chosen as one of recruitment manager",
                    verb_ar="تم اختيارك كأحد مديري التوظيف",
                    verb_de="Sie wurden als einer der Personalvermittler ausgewählt",
                    verb_es="Has sido elegido/a como uno de los gerentes de contratación",
                    verb_fr="Vous êtes choisi(e) comme l'un des responsables du recrutement",
                    icon="people-circle",
                    redirect=reverse("pipeline"),
                )
            return Response({"message": _("Recruitment added successfully.")}, status=201)
        return Response({"errors": form.errors}, status=400)


class RemoveRecruitmentManagerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, mid, rid):
        """
        Remove selected manager from the recruitment.
        
        Args:
            mid : employee manager_id in the recruitment
            rid : recruitment_id
        """
        recruitment_obj = get_object_or_404(Recruitment, id=rid)
        manager = get_object_or_404(Employee, id=mid)
        
        recruitment_obj.recruitment_managers.remove(manager)
        
        notify.send(
            request.user.employee_get,
            recipient=manager.employee_user_id,
            verb=f"You are removed from recruitment manager from {recruitment_obj}",
            verb_ar=f"تمت إزالتك من وظيفة مدير التوظيف في {recruitment_obj}",
            verb_de=f"Sie wurden als Personalvermittler von {recruitment_obj} entfernt",
            verb_es=f"Has sido eliminado/a como gerente de contratación de {recruitment_obj}",
            verb_fr=f"Vous avez été supprimé(e) en tant que responsable du recrutement de {recruitment_obj}",
            icon="person-remove",
            redirect="",
        )

        recruitment_queryset = Recruitment.objects.all()
        previous_data = request.META.get("QUERY_STRING", "")
        paginated_data = paginator_qry(recruitment_queryset, request.GET.get("page"))

        serializer = RecruitmentSerializer(paginated_data, many=True)

        return Response(
            {
                "message": "Recruitment manager removed successfully.",
                "data": serializer.data,
                "pd": previous_data,
            },
            status=status.HTTP_200_OK
        )


class RecruitmentViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        This method is used to render all recruitment to view
        """
        if not request.GET:
            request.GET = request.GET.copy()
            request.GET.update({"is_active": "on"})
        
        form = RecruitmentCreationForm()
        filter_obj = RecruitmentFilter(request.GET, queryset=Recruitment.objects.all())
        recruitment_data = paginator_qry(filter_obj.qs, request.GET.get("page"))

        serializer = RecruitmentSerializer(recruitment_data, many=True)

        data = {
            "data": serializer.data,
            "filter": request.GET.dict(),
            "form_html": form.as_p()
        }
        return Response(data, status=status.HTTP_200_OK)




from urllib.parse import parse_qs


class RecruitmentSearchAPIView(APIView):
    """
    API view for searching recruitment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to search recruitment.
        """
        try:
            if not request.GET:
                request.GET = request.GET.copy()
                request.GET.update({"is_active": "on"})
            queryset = Recruitment.objects.all()
            if not request.GET.get("is_active"):
                queryset = Recruitment.objects.filter(is_active=True)
            filter_obj = RecruitmentFilter(request.GET, queryset)
            previous_data = request.GET.urlencode()
            recruitment_obj = sortby(request, filter_obj.qs, "orderby")
            data_dict = parse_qs(previous_data)
            get_key_instances(Recruitment, data_dict)

            # Paginate the queryset
            paginator = Paginator(recruitment_obj, 10)  # Show 10 results per page
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            # Convert paginated results to a list of dictionaries
            recruitment_data = list(page_obj.object_list.values())

            context = {
                "data": recruitment_data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "page_info": {
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                    "number": page_obj.number,
                    "num_pages": paginator.num_pages,
                },
            }
            return Response(context, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class RecruitmentUpdateAPIView(APIView):
    """
    API view for updating recruitment.
    """
    permission_classes = [IsAuthenticated]

    
    def post(self, request, rec_id):
        """
        Handles POST requests to update a recruitment.
        """
        try:
            recruitment_obj = get_object_or_404(Recruitment, id=rec_id)
            form = RecruitmentCreationForm(request.data, instance=recruitment_obj)
            if form.is_valid():
                recruitment_obj = form.save()
                for survey in form.cleaned_data["survey_templates"]:
                    for sur in survey.recruitmentsurvey_set.all():
                        sur.recruitment_ids.add(recruitment_obj)
                recruitment_obj.save()
                messages.success(request, _("Recruitment Updated."))
                with contextlib.suppress(Exception):
                    managers = recruitment_obj.recruitment_managers.select_related("employee_user_id")
                    users = [employee.employee_user_id for employee in managers]
                    notify.send(
                        request.user.employee_get,
                        recipient=users,
                        verb=f"{recruitment_obj} is updated, You are chosen as one of the managers",
                        verb_ar=f"{recruitment_obj} تم تحديثه، تم اختيارك كأحد المديرين",
                        verb_de=f"{recruitment_obj} wurde aktualisiert. Sie wurden als einer der Manager ausgewählt",
                        verb_es=f"{recruitment_obj} ha sido actualizado/a. Has sido elegido/a como uno de los gerentes",
                        verb_fr=f"{recruitment_obj} a été mis(e) à jour. Vous êtes choisi(e) comme l'un des responsables",
                        icon="people-circle",
                        redirect=reverse("pipeline"),
                    )
                return Response({"message": _("Recruitment updated successfully.")}, status=200)
            return Response({"errors": form.errors}, status=400)
        except Recruitment.DoesNotExist:
            return Response({"error": "Recruitment not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


from django.db.models import ProtectedError
class RecruitmentDeleteAPIView(APIView):
    """
    API view to permanently delete a recruitment.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, rec_id):
        """
        Handles DELETE requests to delete a recruitment.
        """
        try:
            recruitment_obj = get_object_or_404(Recruitment, id=rec_id)
            recruitment_managers = recruitment_obj.recruitment_managers.all()
            all_stage_permissions = Permission.objects.filter(
                content_type__app_label="recruitment", content_type__model="stage"
            )
            all_candidate_permissions = Permission.objects.filter(
                content_type__app_label="recruitment", content_type__model="candidate"
            )
            
            for manager in recruitment_managers:
                all_this_manager = manager.recruitment_set.all()
                if len(all_this_manager) == 1:
                    for stage_permission in all_stage_permissions:
                        manager.employee_user_id.user_permissions.remove(stage_permission.id)
                    for candidate_permission in all_candidate_permissions:
                        manager.employee_user_id.user_permissions.remove(candidate_permission.id)
            
            try:
                recruitment_obj.delete()
                messages.success(request, _("Recruitment deleted successfully."))
                return Response({"message": _("Recruitment deleted successfully.")}, status=200)
            except ProtectedError as e:
                model_verbose_name_sets = {obj._meta.verbose_name.capitalize() for obj in e.protected_objects}
                model_verbose_name_str = ",".join(model_verbose_name_sets)
                messages.error(
                    request,
                    _("You cannot delete this recruitment as it is using in {}".format(model_verbose_name_str))
                )
                return Response({"error": _("You cannot delete this recruitment as it is using in {}".format(model_verbose_name_str))}, status=400)
        except Recruitment.DoesNotExist:
            messages.error(request, _("Recruitment not found."))
            return Response({"error": _("Recruitment not found.")}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class RecruitmentClosePipelineView(APIView):
    """
    API view to close recruitment from pipeline view.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, rec_id):
        """
        Handles POST requests to close recruitment from pipeline view.
        """
        try:
            recruitment_obj = get_object_or_404(Recruitment, id=rec_id)
            recruitment_obj.closed = True
            recruitment_obj.save()
            messages.success(request, _("Recruitment closed successfully"))
            return Response({"message": _("Recruitment closed successfully")}, status=200)
        except Recruitment.DoesNotExist:
            return Response({"error": _("Recruitment does not exist")}, status=404)
        except OverflowError:
            return Response({"error": _("An overflow error occurred")}, status=500)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class RecruitmentReopenPipelineView(APIView):
    """
    API view to reopen recruitment from pipeline view.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, rec_id):
        """
        Handles POST requests to reopen recruitment from pipeline view.
        """
        try:
            recruitment_obj = get_object_or_404(Recruitment, id=rec_id)
            recruitment_obj.closed = False
            recruitment_obj.save()
            messages.success(request, _("Recruitment reopened successfully"))
            return Response({"message": _("Recruitment reopened successfully")}, status=200)
        except Recruitment.DoesNotExist:
            return Response({"error": _("Recruitment does not exist")}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




from django.utils import timezone
from rest_framework.views import APIView

class RecruitmentPipelineView(APIView):
    """
    API view to filter out candidates through pipeline structure.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to filter out candidates through pipeline structure.
        """
        try:
            filter_obj = RecruitmentFilter(request.GET, queryset=Recruitment.objects.all())
            stage_filter = StageFilter(request.GET, queryset=Stage.objects.all())
            candidate_filter = CandidateFilter(request.GET, queryset=Candidate.objects.all())
            recruitments = paginator_qry_recruitment_limited(filter_obj.qs, request.GET.get("page"))
            recruitment_serializer = RecruitmentSerializer(recruitments, many=True)
            stage_serializer = StageSerializer(stage_filter.qs, many=True)
            candidate_serializer = CandidateSerializer(candidate_filter.qs, many=True)
            now = timezone.now()
            context = {
                "recruitments": recruitment_serializer.data,
                "stages": stage_serializer.data,
                "candidates": candidate_serializer.data,
                "now": now,
            }
            return Response(context, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


from django.db.models import Q

class FilterPipelineView(APIView):
    """
    API view to search/filter from pipeline.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to search/filter from pipeline.
        """
        try:
            filter_obj = RecruitmentFilter(request.GET, queryset=Recruitment.objects.all())
            stage_filter = StageFilter(request.GET, queryset=Stage.objects.all())
            candidate_filter = CandidateFilter(request.GET, queryset=Candidate.objects.all())
            view = request.GET.get("view")
            recruitments = filter_obj.qs.filter(is_active=True)
            if not request.user.has_perm("recruitment.view_recruitment"):
                recruitments = recruitments.filter(
                    Q(recruitment_managers=request.user.employee_get)
                )
                stage_recruitment_ids = (
                    stage_filter.qs.filter(stage_managers=request.user.employee_get)
                    .values_list("recruitment_id", flat=True)
                    .distinct()
                )
                recruitments = recruitments | filter_obj.qs.filter(id__in=stage_recruitment_ids)
                recruitments = recruitments.filter(is_active=True).distinct()

            closed = request.GET.get("closed")
            filter_dict = parse_qs(request.GET.urlencode())
            filter_dict = get_key_instances(Recruitment, filter_dict)

            paginator = Paginator(recruitments, 4)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)
            recruitment_serializer = RecruitmentSerializer(page_obj, many=True)
            stage_serializer = StageSerializer(stage_filter.qs, many=True)
            candidate_serializer = CandidateSerializer(candidate_filter.qs, many=True)

            context = {
                "recruitments": recruitment_serializer.data,
                "stages": stage_serializer.data,
                "candidates": candidate_serializer.data,
                "filter_dict": filter_dict,
                "status": closed,
                "view": view,
                "pd": request.GET.urlencode(),
            }
            return Response(context, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



import logging

logger = logging.getLogger(__name__)

class StageComponentView(APIView):
    """
    API view to get stage tab contents.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, view="list"):
        """
        Handles GET requests to get stage tab contents.
        """
        try:
            recruitment_id = request.GET.get("rec_id")
            if not recruitment_id:
                return Response({"error": "Recruitment ID is required"}, status=400)

            recruitment = get_object_or_404(Recruitment, id=recruitment_id)
            cache_key = request.session.session_key + "pipeline"
            cached_data = CACHE.get(cache_key)

            if not cached_data:
                logger.debug("No cached data found for key: %s", cache_key)
                # Fallback to retrieve stages directly from the database
                ordered_stages = Stage.objects.filter(recruitment_id=recruitment_id)
                if not ordered_stages:
                    return Response({"error": "No stages found for this recruitment"}, status=404)
                filter_dict = get_key_instances(Recruitment, {"recruitment_id": [recruitment_id]})
            elif "stages" not in cached_data:
                logger.debug("Pipeline stages not found in cached data for key: %s", cache_key)
                # Fallback to retrieve stages directly from the database
                ordered_stages = Stage.objects.filter(recruitment_id=recruitment_id)
                if not ordered_stages:
                    return Response({"error": "No stages found for this recruitment"}, status=404)
                filter_dict = get_key_instances(Recruitment, {"recruitment_id": [recruitment_id]})
            else:
                ordered_stages = cached_data["stages"].filter(recruitment_id__id=recruitment_id)
                filter_dict = cached_data.get("filter_dict", {})

            recruitment_serializer = RecruitmentSerializer(recruitment)
            stage_serializer = StageSerializer(ordered_stages, many=True)

            context = {
                "rec": recruitment_serializer.data,
                "ordered_stages": stage_serializer.data,
                "filter_dict": filter_dict,
            }
            return Response(context, status=200)
        except Exception as e:
            logger.error("An error occurred: %s", str(e))
            return Response({"error": str(e)}, status=500)



class UpdateCandidateSequenceAPI(APIView):
    """
    API to update the sequence of candidates within a stage.
    """

    def post(self, request, *args, **kwargs):
        # Extract the order list and stage ID from the request data
        order_list = request.data.get("order", [])
        stage_id = request.data.get("stage_id")

        if not stage_id:
            return Response({"error": "Stage ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not order_list:
            return Response({"error": "Order list is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the stage from the cached pipeline
        pipeline_cache = CACHE.get(request.session.session_key + "pipeline")
        if not pipeline_cache:
            return Response({"error": "Pipeline cache not found."}, status=status.HTTP_404_NOT_FOUND)

        stage = pipeline_cache["stages"].filter(id=stage_id).first()
        if not stage:
            return Response({"error": "Stage not found."}, status=status.HTTP_404_NOT_FOUND)

        data = {}
        for index, cand_id in enumerate(order_list):
            candidate = pipeline_cache["candidates"].filter(id=cand_id)
            if candidate.exists():
                candidate.update(sequence=index, stage_id=stage)

        return JsonResponse(data, status=status.HTTP_200_OK)




class ChangeCandidateStageAPI(APIView):
    """
    API to change the stage of one or multiple candidates.
    """

    def post(self, request, *args, **kwargs):
        can_ids = request.data.get("canIds", [])
        stage_id = request.data.get("stageId")
        is_bulk = request.query_params.get("bulk", "False") == "True"

        if not stage_id:
            return Response({"error": "Stage ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not can_ids:
            return Response({"error": "Candidate IDs are required."}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(can_ids, str):
            try:
                can_ids = json.loads(can_ids)
            except json.JSONDecodeError:
                return Response({"error": "Invalid format for candidate IDs."}, status=status.HTTP_400_BAD_REQUEST)

        context = {}
        if is_bulk:
            for cand_id in can_ids:
                try:
                    candidate = Candidate.objects.get(id=cand_id)
                    stage = Stage.objects.filter(recruitment_id=candidate.recruitment_id, id=stage_id).first()
                    if stage:
                        candidate.stage_id = stage
                        candidate.save()
                        if stage.stage_type == "hired" and stage.recruitment_id.is_vacancy_filled():
                            context["message"] = _("Vacancy is filled")
                            context["vacancy"] = stage.recruitment_id.vacancy
                        messages.success(request, "Candidate stage updated")
                except Candidate.DoesNotExist:
                    messages.error(request, f"Candidate with ID {cand_id} not found.")
        else:
            try:
                candidate_id = can_ids[0] if isinstance(can_ids, list) else can_ids
                candidate = Candidate.objects.get(id=candidate_id)
                stage = Stage.objects.filter(recruitment_id=candidate.recruitment_id, id=stage_id).first()
                if stage:
                    candidate.stage_id = stage
                    candidate.save()
                    if stage.stage_type == "hired" and stage.recruitment_id.is_vacancy_filled():
                        context["message"] = _("Vacancy is filled")
                        context["vacancy"] = stage.recruitment_id.vacancy
                    messages.success(request, "Candidate stage updated")
            except Candidate.DoesNotExist:
                messages.error(request, _("Candidate not found."))

        return JsonResponse(context, status=status.HTTP_200_OK)

class RecruitmentPipelineCardView(APIView):
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        search = request.GET.get("search", "")
        recruitment_obj = Recruitment.objects.all()
        candidates = Candidate.objects.filter(name__icontains=search, is_active=True)
        stages = Stage.objects.all()
        recruitment_serializer = RecruitmentSerializer(recruitment_obj, many=True)
        candidate_serializer = CandidateSerializer(candidates, many=True)
        stage_serializer = StageSerializer(stages, many=True)
        return Response({
            'recruitment': recruitment_serializer.data,
            'candidates': candidate_serializer.data,
            'stages': stage_serializer.data
        }, status=status.HTTP_200_OK)
    


import logging

logger = logging.getLogger(__name__)

class RecruitmentArchiveView(APIView):
    """
    API view to archive and unarchive recruitment.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, rec_id):
        """
        Handles POST requests to archive/unarchive recruitment.
        """
        try:
            recruitment = get_object_or_404(Recruitment, id=rec_id)
            recruitment.is_active = not recruitment.is_active
            recruitment.save()
            status = "archived" if not recruitment.is_active else "unarchived"
            return Response({"message": f"Recruitment {status} successfully"}, status=200)
        except Recruitment.DoesNotExist:
            return Response({"error": "Recruitment does not exist"}, status=404)
        except OverflowError:
            return Response({"error": "An overflow error occurred"}, status=500)
        except Exception as e:
            logger.error("An error occurred: %s", str(e))
            return Response({"error": str(e)}, status=500)



import logging

logger = logging.getLogger(__name__)

class CandidateScheduleDateUpdateView(APIView):
    """
    API view to update schedule date for a candidate.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update schedule date for a candidate.
        """
        try:
            candidate_id = request.data.get("candidateId")
            schedule_date = request.data.get("date")

            if not candidate_id or not schedule_date:
                return Response({"error": "'candidateId' and 'date' are required fields"}, status=400)

            candidate_obj = get_object_or_404(Candidate, id=candidate_id)
            candidate_obj.schedule_date = schedule_date
            candidate_obj.save()
            return Response({"message": "Congratulations! Schedule date updated successfully"}, status=200)
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found"}, status=404)
        except Exception as e:
            logger.error("An error occurred: %s", str(e))
            return Response({"error": str(e)}, status=500)







class StageUpdatePipelineView(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request, stage_id):
        stage_obj = get_object_or_404(Stage, id=stage_id)
        serializer = StageSerializer(stage_obj, data=request.data, partial=True) 
        if serializer.is_valid():
            stage_obj = serializer.save()
            try:
                managers = stage_obj.stage_managers.select_related("employee_user_id")
                users = [employee.employee_user_id for employee in managers]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb=f"{stage_obj.stage} stage in recruitment {stage_obj.recruitment_id} is updated, You are chosen as one of the managers",
                    verb_ar=f"تم تحديث مرحلة {stage_obj.stage} في التوظيف {stage_obj.recruitment_id} ، تم اختيارك كأحد المديرين",
                    verb_de=f"Die Stufe {stage_obj.stage} in der Rekrutierung {stage_obj.recruitment_id} wurde aktualisiert. Sie wurden als einer der Manager ausgewählt",
                    verb_es=f"Se ha actualizado la etapa {stage_obj.stage} en la contratación {stage_obj.recruitment_id}. Has sido elegido/a como uno de los gerentes",
                    verb_fr=f"L'étape {stage_obj.stage} dans le recrutement {stage_obj.recruitment_id} a été mise à jour. Vous avez été choisi(e) comme l'un des responsables",
                    icon="people-circle",
                    redirect=reverse("pipeline"),
                )
            except Exception:
                pass
            return Response({"message": "Stage updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



class UpdateCandidateStageAndSequenceAPI(APIView):
    """
    API to update the sequence of candidates within a stage.
    """

    def post(self, request, *args, **kwargs):
        # Extract the order list and stage ID from the request data
        order_list = request.data.get("order", [])
        stage_id = request.data.get("stage_id")

        if not stage_id:
            return Response({"error": "Stage ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not order_list:
            return Response({"error": "Order list is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the stage from the cached pipeline
        pipeline_cache = CACHE.get(request.session.session_key + "pipeline")
        if not pipeline_cache:
            return Response({"error": "Pipeline cache not found."}, status=status.HTTP_404_NOT_FOUND)

        stage = pipeline_cache["stages"].filter(id=stage_id).first()
        if not stage:
            return Response({"error": "Stage not found."}, status=status.HTTP_404_NOT_FOUND)

        context = {}
        for index, cand_id in enumerate(order_list):
            candidate = pipeline_cache["candidates"].filter(id=cand_id)
            if not candidate.exists():
                continue
            candidate.update(sequence=index, stage_id=stage)

        # Handle logic for when the stage type is "hired"
        if stage.stage_type == "hired" and stage.recruitment_id.is_vacancy_filled():
            context["message"] = _("Vacancy is filled")
            context["vacancy"] = stage.recruitment_id.vacancy

        return JsonResponse(context, status=status.HTTP_200_OK)



class RecruitmentUpdatePipelineAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, rec_id):
        """
        This method is used to update recruitment from pipeline view
        """
        recruitment_obj = get_object_or_404(Recruitment, id=rec_id)
        form = RecruitmentCreationForm(request.POST, instance=recruitment_obj)

        if form.is_valid():
            recruitment_obj = form.save()
            messages.success(request, _("Recruitment updated."))
            with contextlib.suppress(Exception):
                managers = recruitment_obj.recruitment_managers.select_related("employee_user_id")
                users = [employee.employee_user_id for employee in managers]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb=f"{recruitment_obj} is updated, You are chosen as one of the managers",
                    verb_ar=f"تم تحديث {recruitment_obj}، تم اختيارك كأحد المديرين",
                    verb_de=f"{recruitment_obj} wurde aktualisiert. Sie wurden als einer der Manager ausgewählt",
                    verb_es=f"{recruitment_obj} ha sido actualizado/a. Has sido elegido/a como uno de los gerentes",
                    verb_fr=f"{recruitment_obj} a été mis(e) à jour. Vous avez été choisi(e) comme l'un des responsables",
                    icon="people-circle",
                    redirect=reverse("pipeline"),
                )
            return Response(
                {"message": "Recruitment updated successfully."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"errors": form.errors},
            status=status.HTTP_400_BAD_REQUEST
        )



class RecruitmentDeletePipelineView(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request, rec_id):
        recruitment_obj = get_object_or_404(Recruitment, id=rec_id)
        try:
            recruitment_obj.delete()
            return Response({"message": _("Recruitment deleted successfully.")}, status=status.HTTP_204_NO_CONTENT)
        except Exception as error:
            return Response({"error": str(error), "message": _("Recruitment could not be deleted. It might be in use.")}, status=status.HTTP_400_BAD_REQUEST)





class CandidateStageUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cand_id):
        """
        Handles POST requests to update candidate stage when drag and drop
        the candidate from one stage to another on the pipeline template.
        Args:
            cand_id : candidate_id
        """
        try:
            stage_id = request.POST.get("stageId")
            if not stage_id:
                return JsonResponse({"type": "error", "message": _("Stage ID is required.")}, status=400)

            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            stage_obj = get_object_or_404(Stage, id=stage_id)

            if candidate_obj.stage_id == stage_obj:
                return JsonResponse({"type": "noChange", "message": _("No change detected.")})

            # Here set the last updated schedule date on this stage if schedule exists in history
            history_queryset = candidate_obj.history_set.filter(stage_id=stage_obj)
            schedule_date = None
            if history_queryset.exists():
                # this condition is executed when a candidate dropped back to any previous
                # stage, if there any scheduled date then set it back
                schedule_date = history_queryset.first().schedule_date

            stage_manager_on_this_recruitment = (
                is_stagemanager(request)[1]
                .filter(recruitment_id=stage_obj.recruitment_id)
                .exists()
            )

            if (
                stage_manager_on_this_recruitment
                or request.user.is_superuser
                or is_recruitmentmanager(rec_id=stage_obj.recruitment_id.id)[0]
            ):
                candidate_obj.stage_id = stage_obj
                candidate_obj.hired = stage_obj.stage_type == "hired"
                candidate_obj.canceled = stage_obj.stage_type == "cancelled"
                candidate_obj.schedule_date = schedule_date
                candidate_obj.start_onboard = False
                candidate_obj.save()

                with contextlib.suppress(Exception):
                    managers = stage_obj.stage_managers.select_related("employee_user_id")
                    users = [employee.employee_user_id for employee in managers]
                    notify.send(
                        request.user.employee_get,
                        recipient=users,
                        verb=f"New candidate arrived on stage {stage_obj.stage}",
                        verb_ar=f"وصل مرشح جديد إلى المرحلة {stage_obj.stage}",
                        verb_de=f"Neuer Kandidat ist auf der Stufe {stage_obj.stage} angekommen",
                        verb_es=f"Nuevo candidato llegó a la etapa {stage_obj.stage}",
                        verb_fr=f"Nouveau candidat arrivé à l'étape {stage_obj.stage}",
                        icon="person-add",
                        redirect=reverse("pipeline"),
                    )

                return JsonResponse({"type": "success", "message": _("Candidate stage updated")})
            
            return JsonResponse({"type": "danger", "message": _("Something went wrong, Try again.")})

        except Candidate.DoesNotExist:
            return JsonResponse({"type": "error", "message": _("Candidate not found.")}, status=404)
        except Stage.DoesNotExist:
            return JsonResponse({"type": "error", "message": _("Stage not found.")}, status=404)
        except Exception as e:
            return JsonResponse({"type": "error", "message": str(e)}, status=500)







class ViewNoteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cand_id):
        """
        Handles GET requests to view candidate remarks or notes.
        Args:
            cand_id : candidate instance id
        """
        try:
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            notes = candidate_obj.stagenote_set.all().order_by("-id")
            serializer = StageNoteSerializer(notes, many=True)
            return JsonResponse({"cand": candidate_obj.id, "notes": serializer.data}, status=200)
        except Candidate.DoesNotExist:
            return JsonResponse({"error": "Candidate not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)




class AddNoteAPIView(APIView):
    """
    API to add a candidate remark (note).
    """

    def post(self, request, cand_id=None, *args, **kwargs):
        form = StageNoteForm(request.data, request.FILES)
        
        try:
            candidate = Candidate.objects.get(id=cand_id)
        except Candidate.DoesNotExist:
            return Response(
                {"error": _("Candidate not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if form.is_valid():
            # Save note and associated files
            note, attachment_ids = form.save(commit=False)
            note.candidate_id = candidate
            note.stage_id = candidate.stage_id
            note.updated_by = request.user.employee_get
            note.save()
            note.stage_files.set(attachment_ids)

            return Response(
                {"message": _("Note added successfully.")},
                status=status.HTTP_201_CREATED,
            )
        else:
            # Return form errors
            return Response(
                {"errors": form.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )



class CreateNoteAPI(APIView):
    """
    API to add a note for a specific candidate.
    """

    def post(self, request, cand_id=None):
        try:
            # Fetch the candidate object or return a 404 error if not found
            candidate_obj = get_object_or_404(Candidate, id=cand_id)

            # Initialize the form with request data
            form = StageNoteForm(request.data, request.FILES)
            if form.is_valid():
                try:
                    # Save the note and its attachments
                    note, attachment_ids = form.save(commit=False)
                    note.candidate_id = candidate_obj
                    note.stage_id = candidate_obj.stage_id
                    note.updated_by = request.user.employee_get
                    note.save()
                    note.stage_files.set(attachment_ids)

                    # Return a success response
                    return Response(
                        {"message": _("Note added successfully.")},
                        status=status.HTTP_201_CREATED,
                    )
                except Exception as e:
                    # Handle unexpected errors during save operation
                    return Response(
                        {"error": _("An error occurred while saving the note.")},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                # Return form validation errors
                return Response(
                    {"errors": form.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Candidate.DoesNotExist:
            # Handle case where the candidate does not exist
            return Response(
                {"error": _("Candidate not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            # Handle any other unexpected errors
            return Response(
                {"error": _("An unexpected error occurred: ") + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class UpdateNoteAPI(APIView):
    """
    API to update a stage note using POST request.
    """

    def post(self, request, note_id):
        """
        Handles updating the stage note.
        """
        try:
            # Fetch the note object or return 404 if not found
            note = get_object_or_404(StageNote, id=note_id)

            # Initialize the form with the existing note and updated data
            form = StageNoteUpdateForm(request.POST, request.FILES, instance=note)
            if form.is_valid():
                form.save()
                messages.success(request, _("Note updated successfully."))

                # Return a success response
                return Response(
                    {"message": _("Note updated successfully.")},
                    status=status.HTTP_200_OK,
                )
            else:
                # Return form validation errors
                return Response(
                    {"errors": form.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except StageNote.DoesNotExist:
            # Handle case where the stage note does not exist
            return Response(
                {"error": _("Stage note not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            # Handle any other unexpected errors
            return Response(
                {"error": _("An unexpected error occurred: ") + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )





class NoteUpdateIndividualAPI(APIView):
    """
    API for updating an individual stage note and returning a JSON response.
    """

    def post(self, request, note_id):
        """
        Handles the update of an individual stage note.
        """
        try:
            # Fetch the note or return 404
            note = get_object_or_404(StageNote, id=note_id)

            # Initialize the form with the existing note and request data
            form = StageNoteForm(request.POST, request.FILES, instance=note)
            if form.is_valid():
                form.save()
                # Return success message in JSON format
                return Response(
                    {"message": _("Note updated successfully...")},
                    status=status.HTTP_200_OK,
                )
            else:
                # Return form errors in JSON format
                return Response(
                    {"errors": form.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except StageNote.DoesNotExist:
            return Response(
                {"error": _("Stage note not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": _("An unexpected error occurred: ") + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class NoteDeleteAPIView(APIView):

    permission_classes = [IsAuthenticated] 

    def delete(self, request, note_id):
        try:
            note = StageNote.objects.get(id=note_id)
        except StageNote.DoesNotExist:
            raise NotFound(_("Stage note not found."))
        if not request.user.has_perm("recruitment.delete_stagenote"):
            raise PermissionDenied(_("You do not have permission to delete this note."))
        candidate = note.candidate_id
        try:
            note.delete()
            return Response(
                {
                    "message": _("Stage note deleted successfully."),
                    "candidate": CandidateSerializer(candidate).data, 
                },
                status=status.HTTP_200_OK,
            )
        except Exception as error:
            return Response(
                {
                    "message": _("You cannot delete this note."),
                    "error": str(error),
                },status=status.HTTP_400_BAD_REQUEST,)
        




class NoteDeleteIndividualAPI(APIView):
    """
    API for deleting an individual stage note and returning a JSON response.
    """

    def delete(self, request, note_id):
        """
        Handles the deletion of an individual stage note.
        """
        try:
            # Fetch the note or return 404 if it doesn't exist
            note = get_object_or_404(StageNote, id=note_id)
            candidate_id = note.candidate_id.id
            note.delete()

            # Return success message in JSON format
            return Response(
                {"message": _("Note deleted successfully."), "candidate_id": candidate_id},
                status=status.HTTP_200_OK,
            )
        except StageNote.DoesNotExist:
            return Response(
                {"error": _("Stage note not found.")},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": _("An unexpected error occurred: ") + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class SendMailFormAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cand_id=None):
        """
        Handles GET requests to render the bootstrap modal content body form.
        """
        try:
            candidate_obj = None
            stage_id = request.GET.get("stage_id")
            if stage_id:
                stage_id = int(stage_id)
            if cand_id:
                candidate_obj = get_object_or_404(Candidate, id=cand_id)

            candidates = Candidate.objects.all()
            if stage_id:
                candidates = candidates.filter(stage_id__id=stage_id)
            else:
                stage_id = None

            templates = HorillaMailTemplate.objects.all()
            candidate_serializer = CandidateSerializer(candidate_obj) if candidate_obj else None
            templates_serializer = HorillaMailTemplateSerializer(templates, many=True)
            candidates_serializer = CandidateSerializer(candidates, many=True)

            context = {
                "cand": candidate_serializer.data if candidate_serializer else None,
                "templates": templates_serializer.data,
                "candidates": candidates_serializer.data,
                "stage_id": stage_id,
                "searchWords": MailTemplateForm().get_template_language(),
            }
            return JsonResponse(context, status=200)
        except Candidate.DoesNotExist:
            return JsonResponse({"error": "Candidate not found."}, status=404)
        except HorillaMailTemplate.DoesNotExist:
            return JsonResponse({"error": "Mail template not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class ScheduleInterviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cand_id):
        """
        Handles POST requests to schedule an interview for a candidate.
        Args:
            cand_id : candidate instance id
        """
        try:
            candidate = get_object_or_404(Candidate, id=cand_id)
            form = ScheduleInterviewForm(request.POST, initial={"candidate_id": candidate})
            form.fields["candidate_id"].queryset = Candidate.objects.filter(id=cand_id)

            if form.is_valid():
                interview = form.save()
                emp_ids = form.cleaned_data["employee_id"]
                interview_candidate = form.cleaned_data["candidate_id"]
                interview_date = form.cleaned_data["interview_date"]
                interview_time = form.cleaned_data["interview_time"]
                users = [employee.employee_user_id for employee in emp_ids]

                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb=f"You are scheduled as an interviewer for an interview with {interview_candidate.name} on {interview_date} at {interview_time}.",
                    verb_ar=f"أنت مجدول كمقابلة مع {interview_candidate.name} يوم {interview_date} في توقيت {interview_time}.",
                    verb_de=f"Sie sind als Interviewer für ein Interview mit {interview_candidate.name} am {interview_date} um {interview_time} eingeplant.",
                    verb_es=f"Estás programado como entrevistador para una entrevista con {interview_candidate.name} el {interview_date} a las {interview_time}.",
                    verb_fr=f"Vous êtes programmé en tant qu'intervieweur pour un entretien avec {interview_candidate.name} le {interview_date} à {interview_time}.",
                    icon="people-circle",
                    redirect=reverse("interview-view"),
                )

                return JsonResponse({"message": _("Interview Scheduled successfully.")}, status=201)
            return JsonResponse({"errors": form.errors}, status=400)

        except Candidate.DoesNotExist:
            return JsonResponse({"error": "Candidate not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



class EditInterviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, interview_id):
        """
        Handles POST requests to edit a scheduled interview.
        Args:
            interview_id : interview schedule instance id
        """
        try:
            interview = get_object_or_404(InterviewSchedule, id=interview_id)
            view = request.GET.get("view", "false")
            if view == "true":
                candidates = Candidate.objects.all()
            else:
                candidates = Candidate.objects.filter(id=interview.candidate_id.id)

            form = ScheduleInterviewForm(request.POST, instance=interview)
            form.fields["candidate_id"].queryset = candidates

            if form.is_valid():
                emp_ids = form.cleaned_data["employee_id"]
                interview_candidate = form.cleaned_data["candidate_id"]
                interview_date = form.cleaned_data["interview_date"]
                interview_time = form.cleaned_data["interview_time"]
                form.save()

                users = [employee.employee_user_id for employee in emp_ids]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb=f"You are scheduled as an interviewer for an interview with {interview_candidate.name} on {interview_date} at {interview_time}.",
                    verb_ar=f"أنت مجدول كمقابلة مع {interview_candidate.name} يوم {interview_date} في توقيت {interview_time}.",
                    verb_de=f"Sie sind als Interviewer für ein Interview mit {interview_candidate.name} am {interview_date} um {interview_time} eingeplant.",
                    verb_es=f"Estás programado como entrevistador para una entrevista con {interview_candidate.name} el {interview_date} a las {interview_time}.",
                    verb_fr=f"Vous êtes programmé en tant qu'intervieweur pour un entretien avec {interview_candidate.name} le {interview_date} à {interview_time}.",
                    icon="people-circle",
                    redirect=reverse("interview-view"),
                )

                return JsonResponse({"message": _("Interview updated successfully.")}, status=200)
            return JsonResponse({"errors": form.errors}, status=400)

        except InterviewSchedule.DoesNotExist:
            return JsonResponse({"error": "Interview schedule not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)





class DeleteInterviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, interview_id):
        """
        Handles DELETE requests to delete a scheduled interview.
        Args:
            interview_id : interview schedule instance id
        """
        try:
            interview = get_object_or_404(InterviewSchedule, id=interview_id)
            interview.delete()
            return JsonResponse({"message": _("Interview deleted successfully.")}, status=200)
        except InterviewSchedule.DoesNotExist:
            return JsonResponse({"error": "Interview schedule not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)





from itertools import chain

class GetManagersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to retrieve managers for a candidate.
        """
        try:
            cand_id = request.GET.get("cand_id")
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            stage_obj = Stage.objects.filter(recruitment_id=candidate_obj.recruitment_id.id)

            # Combine the querysets into a single iterable
            all_managers = chain(
                candidate_obj.recruitment_id.recruitment_managers.all(),
                *[stage.stage_managers.all() for stage in stage_obj],
            )

            # Extract unique managers from the combined iterable
            unique_managers = list(set(all_managers))

            # Convert the unique managers to a dictionary
            employees_dict = {
                employee.id: employee.get_full_name() for employee in unique_managers
            }
            return JsonResponse({"employees": employees_dict}, status=200)
        except Candidate.DoesNotExist:
            return JsonResponse({"error": "Candidate not found."}, status=404)
        except Stage.DoesNotExist:
            return JsonResponse({"error": "Stage not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



class InterviewViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to retrieve and filter interviews.
        """
        try:
            previous_data = request.GET.urlencode()
            if request.user.has_perm("view_interviewschedule"):
                interviews = InterviewSchedule.objects.all().order_by("-interview_date")
            else:
                interviews = InterviewSchedule.objects.filter(
                    employee_id=request.user.employee_get.id
                ).order_by("-interview_date")

            form = InterviewFilter(request.GET, queryset=interviews)
            page_number = request.GET.get("page")
            paginator = Paginator(form.qs, 10)  # Adjust the number of items per page as needed
            page_obj = paginator.get_page(page_number)
            now = timezone.now()

            serializer = InterviewScheduleSerializer(page_obj, many=True)
            return Response({
                "data": serializer.data,
                "pd": previous_data,
                "form": form.data,
                "now": now
            }, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class InterviewFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to filter interviews.
        """
        try:
            previous_data = request.GET.urlencode()

            if request.user.has_perm("view_interviewschedule"):
                interviews = InterviewSchedule.objects.all().order_by("-interview_date")
            else:
                interviews = InterviewSchedule.objects.filter(
                    employee_id=request.user.employee_get.id
                ).order_by("-interview_date")

            if request.GET.get("sortby"):
                interviews = sortby(request, interviews, "sortby")

            dis_filter = InterviewFilter(request.GET, queryset=interviews).qs

            page_number = request.GET.get("page")
            paginator = Paginator(dis_filter, 10)  # Adjust the number of items per page as needed
            page_obj = paginator.get_page(page_number)

            data_dict = parse_qs(previous_data)
            get_key_instances(InterviewSchedule, data_dict)
            now = timezone.now()

            serializer = InterviewScheduleSerializer(page_obj, many=True)
            return Response({
                "data": serializer.data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "now": now
            }, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class RemoveInterviewEmployeeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, interview_id, employee_id):
        """
        Handles DELETE requests to remove an employee from an interview.
        Args:
            interview_id : primary key of the interview
            employee_id : primary key of the employee
        """
        try:
            interview = get_object_or_404(InterviewSchedule, id=interview_id)
            interview.employee_id.remove(employee_id)
            interview.save()
            return JsonResponse({"message": _("Interviewer removed successfully.")}, status=200)
        except InterviewSchedule.DoesNotExist:
            return JsonResponse({"error": "Interview schedule not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)





class CandidateRemarkDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]  

    def delete(self, request, note_id):
        try:

            stage_note = StageNote.objects.get(id=note_id)
        except StageNote.DoesNotExist:
            raise NotFound(_("Stage note not found."))

        if not request.user.has_perm("recruitment.delete_stagenote"):
            raise PermissionDenied(_("You do not have permission to delete this note."))

        try:
            candidate = stage_note.candidate_note_id.candidate_id
        except AttributeError:
            return Response(
                {"message": _("Associated candidate not found.")},status=status.HTTP_400_BAD_REQUEST,)
        try:
            stage_note.delete()
            return Response(
                {
                    "message": _("Stage note deleted successfully."),
                    "candidate": CandidateSerializer(candidate).data,  
                },status=status.HTTP_200_OK,)
        except Exception as error:
            return Response(
                {
                    "message": _("Failed to delete the note."),
                    "error": str(error),
                },status=status.HTTP_400_BAD_REQUEST,)


class CandidateScheduleDateUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]  

    def post(self, request):
        candidate_id = request.data.get("candidateId")
        schedule_date = request.data.get("date")

        if not candidate_id or not schedule_date:
            raise ValidationError(_("Candidate ID and schedule date are required."))

        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            raise NotFound(_("Candidate not found."))

        if not request.user.has_perm("recruitment.change_candidate"):
            raise PermissionDenied(_("You do not have permission to update candidates."))

        try:
            candidate.schedule_date = schedule_date
            candidate.save()
            return Response(
                {"message": _("Schedule date updated successfully.")},
                status=status.HTTP_200_OK,
            )
        except Exception as error:
            return Response(
                {"message": _("Failed to update schedule date."), "error": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class StagePagination(PageNumberPagination):
    page_size = 10 
    page_size_query_param = 'page_size'
    max_page_size = 100



class CreateStageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        API endpoint to create stages and assign permissions to stage managers
        """
        try:
            serializer = StageSerializer(data=request.data)
            if serializer.is_valid():
                stage_obj = serializer.save()
                recruitment_obj = stage_obj.recruitment_id
                rec_stages = (
                    Stage.objects.filter(recruitment_id=recruitment_obj, is_active=True)
                    .order_by("sequence")
                    .last()
                )
                if rec_stages is None or rec_stages.sequence is None:
                    stage_obj.sequence = 1
                else:
                    stage_obj.sequence = rec_stages.sequence + 1
                stage_obj.save()

                managers = stage_obj.stage_managers.select_related("employee_user_id")
                users = [employee.employee_user_id for employee in managers]
                notify.send(
                    request.user.employee_get,
                    recipient=users,
                    verb=f"Stage {stage_obj} is updated on recruitment {stage_obj.recruitment_id}, You are chosen as one of the managers",
                    verb_ar=f"تم تحديث المرحلة {stage_obj} في التوظيف {stage_obj.recruitment_id}، تم اختيارك كأحد المديرين",
                    verb_de=f"Stufe {stage_obj} wurde in der Rekrutierung {stage_obj.recruitment_id} aktualisiert. Sie wurden als einer der Manager ausgewählt",
                    verb_es=f"La etapa {stage_obj} ha sido actualizada en la contratación {stage_obj.recruitment_id}. Has sido elegido/a como uno de los gerentes",
                    verb_fr=f"L'étape {stage_obj} a été mise à jour dans le recrutement {stage_obj.recruitment_id}. Vous avez été choisi(e) comme l'un des responsables",
                    icon="people-circle",
                    redirect=reverse("pipeline"),
                )

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class StageViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        This method returns all stages
        """
        try:
            stages = Stage.objects.all()
            serializer = StageSerializer(stages, many=True)
            return Response(
                {"data": serializer.data},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class StageSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        This method is used to search stages
        """
        try:
            filter_obj = StageFilter(request.GET)
            previous_data = request.META.get("QUERY_STRING", "")
            stages = sortby(request, filter_obj.qs, "orderby")
            paginated_data = paginator_qry(stages, request.GET.get("page"))

            serializer = StageSerializer(paginated_data, many=True)
            
            return Response(
                {
                    "data": serializer.data,
                    "pd": previous_data,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveStageManagerAPI(APIView):
    permission_classes = [IsAuthenticated] 

    def delete(self, request, mid, sid):
    
        try:
            stage_obj = Stage.objects.get(id=sid)
            manager = Employee.objects.get(id=mid)

            if manager not in stage_obj.stage_managers.all():
                return Response({"detail": "Manager not found in this stage."}, status=status.HTTP_400_BAD_REQUEST)

            notify.send(
                request.user.employee_get,
                recipient=manager.employee_user_id,
                verb=f"You are removed from stage managers from stage {stage_obj}",
                verb_ar=f"تمت إزالتك من مديري المرحلة من المرحلة {stage_obj}",
                verb_de=f"Sie wurden als Bühnenmanager von der Stufe {stage_obj} entfernt",
                verb_es=f"Has sido eliminado/a de los gerentes de etapa de la etapa {stage_obj}",
                verb_fr=f"Vous avez été supprimé(e) en tant que responsable de l'étape {stage_obj}",
                icon="person-remove",
                redirect="",
            )
            stage_obj.stage_managers.remove(manager)
            messages.success(request, _("Stage manager removed successfully."))
            return JsonResponse({"message": "Stage manager removed successfully."}, status=status.HTTP_200_OK)

        except Stage.DoesNotExist:
            return Response({"detail": "Stage not found."}, status=status.HTTP_404_NOT_FOUND)
        except Employee.DoesNotExist:
            return Response({"detail": "Manager not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)






class StageDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, rec_id):
        """
        Handles GET requests to get stage data.
        """
        try:
            stages = StageFilter(request.GET).qs.filter(recruitment_id__id=rec_id)
            previous_data = request.GET.urlencode()
            data_dict = parse_qs(previous_data)
            get_key_instances(Stage, data_dict)
            
            paginator = Paginator(stages, 10)  # Change the number to your desired items per page
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            serializer = StageSerializer(page_obj, many=True)
            
            context = {
                "data": serializer.data,
                "filter_dict": data_dict,
                "pd": previous_data,
                "hx_target": request.META.get("HTTP_HX_TARGET"),
            }
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class StageUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, stage_id):
        """
        Handles GET requests to retrieve stage update form.
        """
        try:
            stage = get_object_or_404(Stage, id=stage_id)
            form = StageCreationForm(instance=stage)
            context = {
                "form": form.as_p()
            }
            return JsonResponse(context)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, stage_id):
        """
        Handles POST requests to update stage.
        """
        try:
            stage = get_object_or_404(Stage, id=stage_id)
            form = StageCreationForm(request.POST, instance=stage)
            if form.is_valid():
                form.save()
                return JsonResponse({"message": "Stage updated successfully"})
            return JsonResponse({"errors": form.errors}, status=400)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)



from django import forms


class ObjectDuplicateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, obj_id, *args, **kwargs):
        """
        Handles GET requests to render the duplication form.
        """
        try:
            model = kwargs.get("model")
            form_class = kwargs.get("form")
            original_object = get_object_or_404(model, id=obj_id)
            form = form_class(instance=original_object)
            for field_name, field in form.fields.items():
                if isinstance(field, forms.CharField):
                    if field.initial:
                        initial_value = field.initial
                    else:
                        initial_value = f"{form.initial.get(field_name, '')} (copy)"
                    form.initial[field_name] = initial_value
                    form.fields[field_name].initial = initial_value
            if hasattr(form.instance, "id"):
                form.instance.id = None
            context = {
                kwargs.get("form_name", "form"): form.as_p(),
                "obj_id": obj_id,
                "duplicate": True,
            }
            return JsonResponse(context)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, obj_id, *args, **kwargs):
        """
        Handles POST requests to duplicate the object.
        """
        try:
            model = kwargs.get("model")
            form_class = kwargs.get("form")
            form = form_class(request.POST)
            if form.is_valid():
                new_object = form.save(commit=False)
                new_object.id = None
                new_object.save()
                return JsonResponse({"message": "Object duplicated successfully"})
            return JsonResponse({"errors": form.errors}, status=400)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)








class StageNameUpdateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, stage_id):

        try:
            stage_obj = Stage.objects.get(id=stage_id)
            stage_obj.stage = request.data.get("stage")
            stage_obj.save()
            return JsonResponse({"message": "success"}, status=status.HTTP_200_OK)
        except Stage.DoesNotExist:
            return JsonResponse({"detail": "Stage not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)        
        

class StageDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, stage_id):
        try:
            stage_obj = Stage.objects.get(id=stage_id)
            stage_managers = stage_obj.stage_managers.all()
            for manager in stage_managers:
                all_this_manager = manager.stage_set.all()
                if len(all_this_manager) == 1:
                    view_recruitment = Permission.objects.get(codename="view_recruitment")
                    manager.employee_user_id.user_permissions.remove(view_recruitment.id)
                initial_stage_manager = all_this_manager.filter(stage_type="initial")
                if len(initial_stage_manager) == 1:
                    add_candidate = Permission.objects.get(codename="add_candidate")
                    change_candidate = Permission.objects.get(codename="change_candidate")
                    manager.employee_user_id.user_permissions.remove(add_candidate.id)
                    manager.employee_user_id.user_permissions.remove(change_candidate.id)
                stage_obj.stage_managers.remove(manager)
            stage_obj.delete()
            messages.success(request, _("Stage deleted successfully."))
            return Response({"detail": "Stage deleted successfully."}, status=204)
        except Stage.DoesNotExist:
            return Response({"error": "Stage not found"}, status=404)
        except Exception as error:
            messages.error(request, str(error))
            messages.error(request, _("You cannot delete this stage"))
            return Response({"error": str(error)}, status=400)


class AddCandidateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to render the add candidate form.
        """
        try:
            stage_id = request.GET.get("stage_id")
            stage = get_object_or_404(Stage, id=stage_id)
            form = AddCandidateForm(initial={"stage_id": stage_id})
            context = {
                "form": form.as_p()
            }
            return JsonResponse(context)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request):
        """
        Handles POST requests to add a candidate directly to the stage.
        """
        try:
            stage_id = request.GET.get("stage_id")
            stage = get_object_or_404(Stage, id=stage_id)
            form = AddCandidateForm(
                request.POST,
                request.FILES,
                initial={"stage_id": stage_id},
            )
            if form.is_valid():
                form.save()
                return JsonResponse({"message": "Candidate Added"}, status=201)
            return JsonResponse({"errors": form.errors}, status=400)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)



class StageUpdatePipelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, stage_id):
        """
        Handles GET requests to render the stage update form.
        """
        try:
            stage_obj = get_object_or_404(Stage, id=stage_id)
            form = StageCreationForm(instance=stage_obj)
            context = {
                "form": form.as_p()
            }
            return JsonResponse(context)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, stage_id):
        """
        Handles POST requests to update stage from pipeline view.
        """
        try:
            stage_obj = get_object_or_404(Stage, id=stage_id)
            form = StageCreationForm(request.POST, instance=stage_obj)
            if form.is_valid():
                stage_obj = form.save()
                messages.success(request, _("Stage updated."))
                with contextlib.suppress(Exception):
                    managers = stage_obj.stage_managers.select_related("employee_user_id")
                    users = [employee.employee_user_id for employee in managers]
                    notify.send(
                        request.user.employee_get,
                        recipient=users,
                        verb=f"{stage_obj.stage} stage in recruitment {stage_obj.recruitment_id} is updated, You are chosen as one of the managers",
                        verb_ar=f"تم تحديث مرحلة {stage_obj.stage} في التوظيف {stage_obj.recruitment_id} ، تم اختيارك كأحد المديرين",
                        verb_de=f"Die Stufe {stage_obj.stage} in der Rekrutierung {stage_obj.recruitment_id} wurde aktualisiert. Sie wurden als einer der Manager ausgewählt",
                        verb_es=f"Se ha actualizado la etapa {stage_obj.stage} en la contratación {stage_obj.recruitment_id}.Has sido elegido/a como uno de los gerentes",
                        verb_fr=f"L'étape {stage_obj.stage} dans le recrutement {stage_obj.recruitment_id} a été mise à jour.Vous avez été choisi(e) comme l'un des responsables",
                        icon="people-circle",
                        redirect=reverse("pipeline"),
                    )
                return JsonResponse({"message": "Stage updated successfully"})
            return JsonResponse({"errors": form.errors}, status=400)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)





class StageTitleUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, stage_id):
        """
        Handles POST requests to update the name of recruitment stage.
        """
        try:
            stage_obj = get_object_or_404(Stage, id=stage_id)
            stage_title = request.POST.get("stage")

            if not stage_title:
                return JsonResponse({"error": "Stage title is required"}, status=400)

            stage_obj.stage = stage_title
            stage_obj.save()
            message = _("The stage title has been updated successfully")
            return JsonResponse(
                {"message": message},
                status=200
            )
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)





class StageDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, stage_id):
        """
        Handles DELETE requests to permanently delete a stage.
        """
        try:
            stage_obj = get_object_or_404(Stage, id=stage_id)
            recruitment_id = stage_obj.recruitment_id.id

            stage_managers = stage_obj.stage_managers.all()
            for manager in stage_managers:
                all_this_manager = manager.stage_set.all()
                if len(all_this_manager) == 1:
                    view_recruitment = Permission.objects.get(codename="view_recruitment")
                    manager.employee_user_id.user_permissions.remove(view_recruitment.id)
                initial_stage_manager = all_this_manager.filter(stage_type="initial")
                if len(initial_stage_manager) == 1:
                    add_candidate = Permission.objects.get(codename="add_candidate")
                    change_candidate = Permission.objects.get(codename="change_candidate")
                    manager.employee_user_id.user_permissions.remove(add_candidate.id)
                    manager.employee_user_id.user_permissions.remove(change_candidate.id)
                stage_obj.stage_managers.remove(manager)
            
            try:
                stage_obj.delete()
                message = _("Stage deleted successfully.")
                return JsonResponse({"message": message}, status=200)
            except ProtectedError as e:
                models_verbose_name_sets = set()
                for obj in e.protected_objects:
                    models_verbose_name_sets.add(_(obj._meta.verbose_name.capitalize()))
                models_verbose_name_str = ", ".join(models_verbose_name_sets)
                error_message = _(
                    "You cannot delete this stage while it's in use for {}".format(models_verbose_name_str)
                )
                return JsonResponse({"error": error_message}, status=400)
        except (Stage.DoesNotExist, OverflowError):
            error_message = _("Stage does not exist.")
            return JsonResponse({"error": error_message}, status=404)
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)



class RemoveStageManagerAPIView(APIView):
    """
    API to remove a stage manager and update permissions if necessary.
    """
    def delete(self, request, mid, sid, *args, **kwargs):
        # Get the stage and manager objects
        stage = get_object_or_404(Stage, id=sid)
        manager = get_object_or_404(Employee, id=mid)
        
        # Send notification
        notify.send(
            request.user.employee_get,
            recipient=manager.employee_user_id,
            verb=f"You are removed from stage managers from stage {stage}",
            verb_ar=f"تمت إزالتك من مديري المرحلة من المرحلة {stage}",
            verb_de=f"Sie wurden als Bühnenmanager von der Stufe {stage} entfernt",
            verb_es=f"Has sido eliminado/a de los gerentes de etapa de la etapa {stage}",
            verb_fr=f"Vous avez été supprimé(e) en tant que responsable de l'étape {stage}",
            icon="person-remove",
            redirect="",
        )

        # Remove the manager from the stage
        stage.stage_managers.remove(manager)

        # Success message
        return Response(
            {"message": _("Stage manager removed successfully.")},
            status=status.HTTP_200_OK,
        )


class CandidateCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to create a candidate.
        """
        form = CandidateCreationForm(request.POST, request.FILES)
        open_recruitment = Recruitment.objects.filter(closed=False, is_active=True)
        if form.is_valid():
            candidate_obj = form.save(commit=False)
            candidate_obj.start_onboard = False
            candidate_obj.source = "software"
            if candidate_obj.stage_id is None:
                candidate_obj.stage_id = Stage.objects.filter(
                    recruitment_id=candidate_obj.recruitment_id, stage_type="initial"
                ).first()
            # when creating new candidate from onboarding view
            if request.GET.get("onboarding") == "True":
                candidate_obj.hired = True
                path = "/onboarding/candidates-view"
            else:
                path = "/recruitment/candidate-view"
            if form.data.get("job_position_id"):
                candidate_obj.save()
                message = _("Candidate added.")
                return Response({"message": message}, status=201)
            else:
                message = _("Job position field is required")
                return Response({"error": message, "form": form.as_p(), "open_recruitment": RecruitmentSerializer(open_recruitment, many=True).data}, status=400)
        return Response({"errors": form.errors, "form": form.as_p(), "open_recruitment": RecruitmentSerializer(open_recruitment, many=True).data}, status=400)






class RecruitmentStageAPIView(APIView):
    permission_classes = [IsAuthenticated]
   

    def get(self, request, rec_id, *args, **kwargs):
        try:
            recruitment_obj = Recruitment.objects.get(id=rec_id)
            all_stages = recruitment_obj.stage_set.all()
            serializer = StageSerializer(all_stages, many=True)
            return Response({"stages": serializer.data}, status=status.HTTP_200_OK)
        except Recruitment.DoesNotExist:
            return Response({"error": "Recruitment not found."}, status=status.HTTP_404_NOT_FOUND)



class CandidateViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        This method renders all candidates
        """
        previous_data = request.META.get("QUERY_STRING", "")
        candidates = Candidate.objects.filter(is_active=True)
        filter_obj = CandidateFilter(request.GET, queryset=candidates)
        paginated_data = paginator_qry(filter_obj.qs, request.GET.get("page"))

        serializer = CandidateSerializer(paginated_data, many=True)

        return Response(
            {
                "data": serializer.data,
                "pd": previous_data,
                "filter": request.GET.dict()
            },
            status=status.HTTP_200_OK
        )



class CandidateFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to filter, paginate, and search candidates.
        """
        try:
            candidates = Candidate.objects.filter(is_active=True)
            template_view = request.GET.get("view", "card")
            template = "candidate/candidate_card.html" if template_view != "list" else "candidate/candidate_list.html"

            previous_data = request.GET.urlencode()
            filter_obj = CandidateFilter(request.GET, queryset=candidates)
            paginator = Paginator(filter_obj.qs, 24)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

            serializer = CandidateSerializer(page_obj, many=True)
            return Response({
                "data": serializer.data,
                "pd": previous_data,
                "template": template
            }, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)






class CandidateSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to search candidate model and return matching objects.
        """
        try:
            previous_data = request.GET.urlencode()
            search = request.GET.get("search", "")
            candidates = Candidate.objects.filter(name__icontains=search)
            candidates = CandidateFilter(request.GET, queryset=candidates).qs
            data_dict = []

            if not request.GET.get("dashboard"):
                data_dict = parse_qs(previous_data)
                get_key_instances(Candidate, data_dict)

            template = "candidate/candidate_card.html"
            if request.GET.get("view") == "list":
                template = "candidate/candidate_list.html"
            candidates = sortby(request, candidates, "orderby")

            field = request.GET.get("field")
            if field:
                candidates = general_group_by(
                    candidates, field, request.GET.get("page"), "page"
                )
                template = "candidate/group_by.html"
            else:
                request.session["filtered_candidates"] = [
                    candidate.id for candidate in candidates
                ]

            paginator = Paginator(candidates, 24)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

            mails = list(Candidate.objects.values_list("email", flat=True))
            existing_emails = list(
                User.objects.filter(username__in=mails).values_list("email", flat=True)
            )

            serializer = CandidateSerializer(page_obj, many=True)
            return Response({
                "data": serializer.data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "field": field,
                "emp_list": existing_emails,
                "template": template
            }, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class CandidateListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to render candidate list or card view.
        """
        try:
            previous_data = request.GET.urlencode()
            candidates = Candidate.objects.all()
            if request.GET.get("is_active") is None:
                candidates = candidates.filter(is_active=True)
            candidates = CandidateFilter(request.GET, queryset=candidates).qs

            template_view = request.GET.get("view", "card")
            template = "candidate/candidate_card.html" if template_view != "list" else "candidate/candidate_list.html"

            paginator = Paginator(candidates, 24)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

            serializer = CandidateSerializer(page_obj, many=True)
            return Response({
                "data": serializer.data,
                "pd": previous_data,
                "template": template
            }, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class CandidateCardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        This method renders all candidates on candidate_card.html template
        """
        previous_data = request.META.get("QUERY_STRING", "")
        candidates = Candidate.objects.all()
        if request.GET.get("is_active") is None:
            candidates = candidates.filter(is_active=True)
        candidates = CandidateFilter(request.GET, queryset=candidates).qs
        paginated_candidates = paginator_qry(candidates, request.GET.get("page"))

        serializer = CandidateSerializer(paginated_candidates, many=True)

        return Response(
            {
                "data": serializer.data,
                "pd": previous_data
            },
            status=status.HTTP_200_OK
        )


  # Assuming export_data is a utility function

class CandidateExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to render the export filter form.
        """
        try:
            if request.META.get("HTTP_HX_REQUEST"):
                export_column = CandidateExportForm()
                export_filter = CandidateFilter()
                content = {
                    "export_filter": export_filter,
                    "export_column": export_column,
                }
                return render(request, "candidate/export_filter.html", context=content)
            return Response({"error": "Invalid request."}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def post(self, request):
        """
        Handles POST requests to export candidate data.
        """
        try:
            return export_data(
                request=request,
                model=Candidate,
                filter_class=CandidateFilter,
                form_class=CandidateExportForm,
                file_name="Candidate_export",
            )
        except Exception as e:
            return Response({"error": str(e)}, status=500)




import ast

class CandidateViewIndividualAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cand_id, **kwargs):
        """
        Handles GET requests to view profile of candidate.
        """
        try:
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            mails = list(Candidate.objects.values_list("email", flat=True))

            # Query the User model to check if any email is present
            existing_emails = list(
                User.objects.filter(username__in=mails).values_list("email", flat=True)
            )
            ratings = candidate_obj.candidate_rating.all()
            rating_list = [rating.rating for rating in ratings]
            avg_rate = round(sum(rating_list) / len(rating_list)) if rating_list else 0

            # Retrieve the filtered candidate from the session
            filtered_candidate_ids = request.session.get("filtered_candidates", [])
            requests_ids = (
                ast.literal_eval(filtered_candidate_ids)
                if isinstance(filtered_candidate_ids, str)
                else filtered_candidate_ids
            )

            next_id = None
            previous_id = None

            for index, req_id in enumerate(requests_ids):
                if req_id == cand_id:
                    next_id = requests_ids[index + 1] if index < len(requests_ids) - 1 else None
                    previous_id = requests_ids[index - 1] if index > 0 else None
                    break

            now = timezone.now()

            context = {
                "candidate": candidate_obj.id,
                "previous": previous_id,
                "next": next_id,
                "requests_ids": requests_ids,
                "emp_list": existing_emails,
                "average_rate": avg_rate,
                "now": now
            }
            return JsonResponse(context, status=200)

        except Candidate.DoesNotExist:
            messages.error(request, _("Candidate not found"))
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)




class CandidateUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]


    def post(self, request, cand_id, **kwargs):
        """
        Handles POST requests to update or change the candidate.
        """
        try:
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            form = CandidateCreationForm(request.POST, request.FILES, instance=candidate_obj)
            if form.is_valid():
                candidate_obj = form.save()
                if candidate_obj.stage_id is None:
                    candidate_obj.stage_id = Stage.objects.filter(
                        recruitment_id=candidate_obj.recruitment_id,
                        stage_type="initial",
                    ).first()
                if candidate_obj.stage_id is not None:
                    if candidate_obj.stage_id.recruitment_id != candidate_obj.recruitment_id:
                        candidate_obj.stage_id = candidate_obj.recruitment_id.stage_set.filter(
                            stage_type="initial"
                        ).first()
                if request.GET.get("onboarding") == "True":
                    candidate_obj.hired = True
                candidate_obj.save()
                return JsonResponse({"message": _("Candidate Updated Successfully.")}, status=200)
            return JsonResponse({"errors": form.errors}, status=400)
        except Candidate.DoesNotExist:
            return JsonResponse({"error": _("Candidate does not exist")}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



class CandidateConversionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cand_id, **kwargs):
        """
        Handles POST requests to convert a candidate into an employee.
        Args:
            cand_id : candidate instance id
        """
        try:
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            can_name = candidate_obj.name
            can_mob = candidate_obj.mobile
            can_job = candidate_obj.job_position_id
            can_dep = can_job.department_id
            can_mail = candidate_obj.email
            can_gender = candidate_obj.gender
            can_company = candidate_obj.recruitment_id.company_id
            user_exists = User.objects.filter(username=can_mail).exists()
            
            if user_exists:
                return JsonResponse({"error": _("Employee instance already exists.")}, status=400)
            elif not Employee.objects.filter(employee_user_id__username=can_mail).exists():
                new_employee = Employee.objects.create(
                    employee_first_name=can_name,
                    email=can_mail,
                    phone=can_mob,
                    gender=can_gender,
                    is_directly_converted=True,
                )
                candidate_obj.converted_employee_id = new_employee
                candidate_obj.save()
                work_info, created = EmployeeWorkInformation.objects.get_or_create(
                    employee_id=new_employee
                )
                work_info.job_position_id = can_job
                work_info.department_id = can_dep
                work_info.company_id = can_company
                work_info.save()
                return JsonResponse({"message": _("Employee instance created successfully.")}, status=201)
            else:
                return JsonResponse({"info": _("An employee with this email already exists.")}, status=200)
        except Candidate.DoesNotExist:
            return JsonResponse({"error": _("Candidate not found.")}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



from django.conf import settings
import os




class DeleteProfileImageView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, obj_id):
        candidate_obj = get_object_or_404(Candidate, id=obj_id)
        try:
            if candidate_obj.profile:
                file_path = candidate_obj.profile.path
                absolute_path = os.path.join(settings.MEDIA_ROOT, file_path)
                os.remove(absolute_path)
                candidate_obj.profile = None
                candidate_obj.save()
                messages.success(request, _("Profile image removed."))
                return Response({"detail": "Profile image removed."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "An error occurred while deleting the profile image."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"detail": "Profile image does not exist."}, status=status.HTTP_400_BAD_REQUEST)







class CandidateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, cand_id):
        """
        Handles DELETE requests to delete candidate permanently.
        Args:
            cand_id : candidate instance id
        """
        try:
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            try:
                candidate_obj.delete()
                return Response({"message": _("Candidate deleted successfully.")}, status=200)
            except ProtectedError as e:
                models_verbose_name_set = set()
                for obj in e.protected_objects:
                    models_verbose_name_set.add(obj._meta.verbose_name.capitalize())
                models_verbose_name_str = ", ".join(models_verbose_name_set)
                return Response({
                    "error": _(
                        "You cannot delete this candidate because the candidate is in {}.".format(models_verbose_name_str)
                    )
                }, status=400)
        except Candidate.DoesNotExist:
            return Response({"error": _("Candidate not found.")}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class CandidateArchiveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cand_id):
        """
        Handles POST requests to archive or un-archive candidates.
        Args:
            cand_id : candidate instance id
        """
        try:
            candidate_obj = get_object_or_404(Candidate, id=cand_id)
            candidate_obj.is_active = not candidate_obj.is_active
            candidate_obj.save()
            message = _("archived") if not candidate_obj.is_active else _("un-archived")
            return Response({"message": _("Candidate is %(message)s") % {"message": message}}, status=200)
        except Candidate.DoesNotExist:
            return Response({"error": _("Candidate does not exist.")}, status=404)
        except OverflowError:
            return Response({"error": _("Overflow error occurred.")}, status=500)
        except Exception as e:
            return Response({"error": str(e)}, status=500)






class CandidateBulkDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """
        Handles DELETE requests to bulk delete candidates.
        """
        try:
            ids = json.loads(request.body).get("ids", [])
            for cand_id in ids:
                try:
                    candidate_obj = Candidate.objects.get(id=cand_id)
                    candidate_obj.delete()
                except Candidate.DoesNotExist:
                    return Response({"error": _("Candidate not found.")}, status=404)
                except ProtectedError:
                    return Response(
                        {"error": _("You cannot delete %(candidate)s") % {"candidate": candidate_obj}},
                        status=400
                    )
            return Response({"message": "Success"}, status=200)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class CandidateBulkArchiveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to archive/un-archive bulk candidates.
        """
        try:
            ids = json.loads(request.body).get("ids", [])
            is_active = True
            message = _("un-archived")
            if request.GET.get("is_active") == "False":
                is_active = False
                message = _("archived")
            for cand_id in ids:
                candidate_obj = get_object_or_404(Candidate, id=cand_id)
                candidate_obj.is_active = is_active
                candidate_obj.save()
            return Response({"message": "Success"}, status=200)
        except Candidate.DoesNotExist:
            return Response({"error": _("Candidate not found.")}, status=404)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CandidateHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cand_id):
        """
        This method is used to view candidate stage changes
        Args:
            cand_id: candidate_id
        """
        candidate_obj = get_object_or_404(Candidate, id=cand_id)
        candidate_history_queryset = candidate_obj.history.all()
        serializer = CandidateHistorySerializer(candidate_history_queryset, many=True)
        return Response(
            {"history": serializer.data},
            status=status.HTTP_200_OK
        )

class ApplicationFormAPIView( APIView):
    permission_classes = [IsAuthenticated]
  

    def post(self, request, *args, **kwargs):
        serializer = CandidateSerializer(data=request.data)
        if serializer.is_valid():
            candidate_data = serializer.validated_data
            recruitment_obj = candidate_data.get('recruitment_id')
            candidate_obj = Candidate(**candidate_data)
            stages = recruitment_obj.stage_set.all()
            if stages.filter(stage_type="applied").exists():
                candidate_obj.stage_id = stages.filter(stage_type="applied").first()
            else:
                candidate_obj.stage_id = stages.order_by("sequence").first()
            candidate_obj.save()
            return Response({"message": "Application saved.", "candidate": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class FormSendMailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, cand_id, *args, **kwargs):
        try:
            candidate_obj = Candidate.objects.get(id=cand_id)
            serializer = CandidateSerializer(candidate_obj)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)


from django.core.mail import EmailMessage
from django.template import Context, Template


class SendAcknowledgementAPI(APIView):
    """
    API for sending acknowledgment emails to candidates.
    """

    def post(self, request):
        """
        Handles sending acknowledgment emails.
        """
        try:
            candidate_id = request.data.get("id")
            subject = request.data.get("subject")
            body = request.data.get("body")
            candidate_ids = request.data.get("candidates", [])
            other_attachments = request.FILES.getlist("other_attachments")
            template_attachment_ids = request.data.get("template_attachments", [])

            # Retrieve candidates
            candidates = Candidate.objects.filter(id__in=candidate_ids)
            if candidate_id:
                candidate_obj = Candidate.objects.filter(id=candidate_id)
            else:
                candidate_obj = Candidate.objects.none()
            candidates = (candidates | candidate_obj).distinct()

            # Prepare attachments
            attachments = [
                (file.name, file.read(), file.content_type) for file in other_attachments
            ]

            for candidate in candidates:
                # Process template attachments
                bodys = list(
                    HorillaMailTemplate.objects.filter(
                        id__in=template_attachment_ids
                    ).values_list("body", flat=True)
                )
                for html in bodys:
                    template_bdy = Template(html)
                    context = Context(
                        {"instance": candidate, "self": request.user.employee_get}
                    )
                    rendered_body = template_bdy.render(context)
                    pdf_content = generate_pdf(rendered_body, {}, path=False, title="Document").content
                    attachments.append(
                        ("Document", pdf_content, "application/pdf")
                    )

                # Render body template
                template_bdy = Template(body)
                context = Context(
                    {"instance": candidate, "self": request.user.employee_get}
                )
                rendered_body = template_bdy.render(context)

                # Send email
                email = EmailMessage(
                    subject=subject,
                    body=rendered_body,
                    to=[candidate.email],
                )
                email.content_subtype = "html"
                email.attachments = attachments

                try:
                    email.send()
                except Exception as e:
                    logger.exception(e)
                    return Response(
                        {"error": _("Failed to send email to ") + candidate.email},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            return Response(
                {"message": _("Acknowledgment emails sent successfully.")},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception(e)
            return Response(
                {"error": _("An unexpected error occurred: ") + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            candidates = Candidate.objects.all()
            hired_candidates = candidates.filter(hired=True)
            total_candidates = len(candidates)
            total_hired_candidates = len(hired_candidates)
            hire_ratio = 0
            if total_candidates != 0:
                hire_ratio = f"{((total_hired_candidates / total_candidates) * 100):.1f}"

            onboard_candidates = hired_candidates.filter(start_onboard=True)
            data = {
                "total_candidates": total_candidates,
                "total_hired_candidates": total_hired_candidates,
                "hire_ratio": hire_ratio,
                "onboard_candidates": onboard_candidates.count(),  
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)






class DashboardPipelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        try:
            recruitment_obj = Recruitment.objects.filter(closed=False)
            data_set = []
            labels = [type[1] for type in Stage.stage_types]
            for rec in recruitment_obj:
                data = [stage_type_candidate_count(rec, type[0]) for type in Stage.stage_types]
                data_set.append(
                    {
                        "label": (
                            rec.title
                            if rec.title is not None
                            else f"{rec.job_position_id} {rec.start_date}"
                        ),
                        "data": data,
                    }
                )
            return JsonResponse({"dataSet": data_set, "labels": labels}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)




from django.core import serializers


class GetOpenPositionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to render the open position to the recruitment.

        Returns:
            obj: it returns the list of job positions
        """
        try:
            rec_id = request.GET.get("recId")
            if not rec_id:
                return Response({"error": _("Recruitment ID is required.")}, status=400)
            
            recruitment_obj = get_object_or_404(Recruitment, id=rec_id)
            queryset = recruitment_obj.open_positions.all()
            job_info = serializers.serialize("json", queryset)
            rec_info = serializers.serialize("json", [recruitment_obj])
            
            return Response({"openPositions": job_info, "recruitmentInfo": rec_info}, status=200)
        except Recruitment.DoesNotExist:
            return Response({"error": _("Recruitment not found.")}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



import datetime
class DashboardHiringAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to generate employee joining status for the dashboard.
        """
        try:
            selected_year = request.GET.get("id")
            if not selected_year:
                return Response({"error": _("Year ID is required.")}, status=400)

            employee_info = EmployeeWorkInformation.objects.filter(
                date_joining__year=selected_year
            )

            # Create a list to store the count of employees for each month
            employee_count_per_month = [0] * 12  # Initialize with zeros for all months

            # Count the number of employees who joined in each month for the selected year
            for info in employee_info:
                if isinstance(info.date_joining, datetime.date):
                    month_index = info.date_joining.month - 1  # Month index is zero-based
                    employee_count_per_month[month_index] += 1  # Increment the count for the corresponding month

            labels = [
                _("January"),
                _("February"),
                _("March"),
                _("April"),
                _("May"),
                _("June"),
                _("July"),
                _("August"),
                _("September"),
                _("October"),
                _("November"),
                _("December"),
            ]

            data_set = [
                {
                    "label": _("Employees joined in %(year)s") % {"year": selected_year},
                    "data": employee_count_per_month,
                    "backgroundColor": "rgba(236, 131, 25)",
                }
            ]

            return Response({"dataSet": data_set, "labels": labels}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class DashboardVacancyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to generate a recruitment vacancy chart for the dashboard.
        """
        try:
            recruitment_obj = Recruitment.objects.filter(closed=False, is_event_based=False)
            departments = Department.objects.all()
            labels = []
            data_set = [{"label": _("Openings"), "data": []}]

            for dep in departments:
                vacancies_for_department = recruitment_obj.filter(
                    job_position_id__department_id=dep
                )
                if vacancies_for_department.exists():
                    labels.append(dep.department)

                vacancies = [
                    int(rec.vacancy) if rec.vacancy is not None else 0
                    for rec in vacancies_for_department
                ]

                data_set[0]["data"].append(sum(vacancies))

            return Response({"dataSet": data_set, "labels": labels}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)







class CandidateSequenceUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update the sequence of candidates.
        """
        try:
            sequence_data = json.loads(request.body).get("sequenceData", {})
            if not sequence_data:
                return Response({"error": "Sequence data is required."}, status=400)

            for cand_id, seq in sequence_data.items():
                candidate_obj = get_object_or_404(Candidate, id=cand_id)
                candidate_obj.sequence = seq
                candidate_obj.save()

            return Response({"message": "Sequence updated", "type": "info"}, status=200)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format."}, status=400)
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)





class StageSequenceUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update the sequence of stages.
        """
        try:
            sequence_data = request.data.get("sequence")
            if not sequence_data:
                return Response({"error": "Sequence data is required."}, status=400)
            if not isinstance(sequence_data, dict):
                return Response({"error": "Sequence data must be a dictionary."}, status=400)

            for stage_id, seq in sequence_data.items():
                stage = get_object_or_404(Stage, id=stage_id)
                stage.sequence = seq
                stage.save()

            return Response({"type": "success", "message": "Stage sequence updated"}, status=200)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format."}, status=400)
        except Stage.DoesNotExist:
            return Response({"error": "Stage not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


        



class CandidateStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to generate a Candidate status chart for the dashboard.
        """
        try:
            not_sent_candidates = Candidate.objects.filter(
                offer_letter_status="not_sent"
            ).count()
            sent_candidates = Candidate.objects.filter(offer_letter_status="sent").count()
            accepted_candidates = Candidate.objects.filter(
                offer_letter_status="accepted"
            ).count()
            rejected_candidates = Candidate.objects.filter(
                offer_letter_status="rejected"
            ).count()
            joined_candidates = Candidate.objects.filter(offer_letter_status="joined").count()

            data_set = []
            labels = ["Not Sent", "Sent", "Accepted", "Rejected", "Joined"]
            data = [
                not_sent_candidates,
                sent_candidates,
                accepted_candidates,
                rejected_candidates,
                joined_candidates,
            ]

            for i in range(len(data)):
                data_set.append({"label": labels[i], "data": data[i]})

            return Response({"dataSet": data_set, "labels": labels}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class SurveyPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, title):
        """
        Handles GET requests to render survey form to the candidate.
        """
        try:
            template = get_object_or_404(SurveyTemplate, title=str(title))
            form = SurveyPreviewForm(template=template).form
            context = {"form": form, "template": template}
            return render(request, "survey/survey_preview.html", context)
        except SurveyTemplate.DoesNotExist:
            return Response({"error": "Survey template not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class QuestionOrderUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to update the order of questions.
        """
        try:
            question_id = request.data.get("question_id")
            new_position = request.data.get("new_position")

            if question_id is None or new_position is None:
                return Response({"error": "Question ID and new position are required."}, status=400)

            new_position = int(new_position)
            qs = get_object_or_404(RecruitmentSurvey, id=question_id)

            if qs.sequence > new_position:
                new_position = new_position
            if qs.sequence <= new_position:
                new_position = new_position - 1

            old_qs = RecruitmentSurvey.objects.filter(sequence=new_position)
            for i in old_qs:
                i.sequence = new_position + 1
                i.save()

            qs.sequence = new_position
            qs.save()

            return Response(
                {"success": True, "message": "Question order updated successfully"},
                status=200
            )

        except RecruitmentSurvey.DoesNotExist:
            return Response({"error": "Question not found."}, status=404)
        except ValueError:
            return Response({"error": "Invalid new position value."}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class SurveyFormAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to render the survey form.
        """
        try:
            recruitment_id = request.GET.get("recId")
            if not recruitment_id:
                return Response({"error": "Recruitment ID is required."}, status=400)

            recruitment = get_object_or_404(Recruitment, id=recruitment_id)
            form = SurveyForm(recruitment=recruitment).form
            context = {"form": form}

            return render(request, "survey/form.html", context)
        except Recruitment.DoesNotExist:
            return Response({"error": "Recruitment not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CreateQuestionTemplateAPI(APIView):
    """
    API to create a question template using a form.
    """

    def post(self, request, *args, **kwargs):
        # Prepare the form with the request data
        form = QuestionForm(request.data)

        # Validate the form
        if form.is_valid():
            try:
                # Create the RecruitmentSurvey instance
                instance = form.save(commit=False)
                instance.save()

                # Set ManyToMany relationships (if provided)
                recruitment_ids = form.cleaned_data.get('recruitment')
                if recruitment_ids:
                    recruitment_objects = Recruitment.objects.filter(id__in=recruitment_ids)
                    instance.recruitment_ids.set(recruitment_objects)

                template_ids = form.cleaned_data.get('template_id')
                if template_ids:
                    template_objects = SurveyTemplate.objects.filter(id__in=template_ids)
                    instance.template_id.set(template_objects)

                # Return success response
                return JsonResponse(
                    {"success": True, "message": "Question template created successfully."},
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                # Handle unexpected errors
                return JsonResponse(
                    {"success": False, "message": f"An error occurred: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            # If form is not valid, return the errors
            return JsonResponse(
                {"success": False, "message": "Form validation failed", "errors": form.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )







class UpdateQuestionTemplateAPI(APIView):
    """
    API to update an existing question template using a form.
    """

    def post(self, request, survey_id, *args, **kwargs):
        try:
            # Get the instance of RecruitmentSurvey to update
            instance = RecruitmentSurvey.objects.get(id=survey_id)
        except RecruitmentSurvey.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Survey question not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Initialize the form with POST data and the existing instance
        form = QuestionForm(request.data, instance=instance)

        # Validate the form
        if form.is_valid():
            try:
                # Save the updated instance
                instance = form.save(commit=False)
                instance.save()

                # Update ManyToMany fields
                recruitment_ids = form.cleaned_data.get("recruitment")
                if recruitment_ids:
                    recruitment_objects = Recruitment.objects.filter(id__in=recruitment_ids)
                    instance.recruitment_ids.set(recruitment_objects)

                template_ids = form.cleaned_data.get("template_id")
                if template_ids:
                    template_objects = SurveyTemplate.objects.filter(id__in=template_ids)
                    instance.template_id.set(template_objects)

                return JsonResponse(
                    {"success": True, "message": "Question template updated successfully."},
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                # Handle unexpected errors
                return JsonResponse(
                    {"success": False, "message": f"An error occurred: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            # Return form validation errors if any
            return JsonResponse(
                {"success": False, "message": "Form validation failed", "errors": form.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )



class DeleteSurveyQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, survey_id):
        """
        Handles DELETE requests to delete the survey instance.
        """
        try:
            question = get_object_or_404(RecruitmentSurvey, id=survey_id)
            question.delete()
            return Response({"message": _("Question was deleted successfully.")}, status=200)
        except RecruitmentSurvey.DoesNotExist:
            return Response({"error": _("Question not found.")}, status=404)
        except ProtectedError:
            return Response({"error": _("You cannot delete this question.")}, status=403)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class FilterSurveyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to filter/search the recruitment surveys.
        """
        try:
            recs = Recruitment.objects.all()
            ids = []
            for i in recs:
                for manager in i.recruitment_managers.all():
                    if request.user.employee_get == manager:
                        ids.append(i.id)

            if request.user.has_perm("view_recruitmentsurvey"):
                questions = RecruitmentSurvey.objects.all()
            else:
                questions = RecruitmentSurvey.objects.filter(recruitment_ids__in=ids)

            previous_data = request.GET.urlencode()
            filter_obj = SurveyFilter(request.GET, questions)
            questions = filter_obj.qs
            templates = group_by_queryset(
                questions.filter(template_id__isnull=False).distinct(),
                "template_id__title",
                page=request.GET.get("template_page"),
                page_name="template_page",
                records_per_page=get_pagination(),
            )

            all_template_object_list = []
            for template in templates:
                all_template_object_list.append(template)

            survey_templates = SurveyTemplateFilter(request.GET).qs

            all_templates = survey_templates.values_list("title", flat=True)
            used_templates = questions.values_list("template_id__title", flat=True)

            unused_templates = list(set(all_templates) - set(used_templates))
            unused_groups = []
            for template_name in unused_templates:
                unused_groups.append(
                    {
                        "grouper": template_name,
                        "list": [],
                        "dynamic_name": "",
                    }
                )

            all_template_object_list += unused_groups
            templates_page = paginator_qry(all_template_object_list, request.GET.get("template_page"))
            survey_templates_page = paginator_qry(survey_templates, request.GET.get("survey_template_page"))
            questions_page = paginator_qry(questions, request.GET.get("page"))

            requests_ids = json.dumps([instance.id for instance in questions_page.object_list])
            data_dict = parse_qs(previous_data)
            get_key_instances(RecruitmentSurvey, data_dict)

            response_data = {
                "questions": RecruitmentSurveySerializer(questions_page.object_list, many=True).data,
                "templates": [template for template in templates_page.object_list],
                "survey_templates": SurveyTemplateSerializer(survey_templates_page.object_list, many=True).data,
                "previous_data": previous_data,
                "filter_dict": data_dict,
                "requests_ids": requests_ids,
                "pagination": {
                    "questions": {
                        "current_page": questions_page.number,
                        "total_pages": questions_page.paginator.num_pages
                    },
                    "templates": {
                        "current_page": templates_page.number,
                        "total_pages": templates_page.paginator.num_pages
                    },
                    "survey_templates": {
                        "current_page": survey_templates_page.number,
                        "total_pages": survey_templates_page.paginator.num_pages
                    }
                }
            }

            return Response(response_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class SingleSurveyAPI(APIView):
    """
    API to get a single survey question template details and related previous/next questions.
    """

    def get(self, request, survey_id, *args, **kwargs):
        try:
            # Get the instance of the survey question template
            question = RecruitmentSurvey.objects.get(id=survey_id)
        except RecruitmentSurvey.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Survey question not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Assuming the field name for the question is 'question'
        response_data = {
            "question": {
                "id": question.id,
                "question_text": question.question,  # Update field name here
                "template_ids": [template.id for template in question.template_id.all()] 
                if question.template_id.exists() else None,
            }
        }

        # Handle instances_ids for previous and next questions
        requests_ids_json = request.GET.get("instances_ids")
        if requests_ids_json:
            try:
                requests_ids = json.loads(requests_ids_json)
                previous_id, next_id = closest_numbers(requests_ids, survey_id)
                response_data["previous"] = previous_id
                response_data["next"] = next_id
                response_data["requests_ids"] = requests_ids_json
            except ValueError:
                return JsonResponse(
                    {"success": False, "message": "Invalid instances_ids format."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return JsonResponse(response_data, status=status.HTTP_200_OK)





class CreateTemplateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    

    def post(self, request):
        """
        Handles POST requests to create or update a template.
        """
        try:
            title = request.GET.get("title")
            instance = None
            if title:
                instance = SurveyTemplate.objects.filter(title=title).first()
            form = TemplateForm(request.POST, instance=instance)
            if form.is_valid():
                form.save()
                return Response({"message": _("Template saved"), "script": "<script>window.location.reload()</script>"}, status=201)
            else:
                return Response({"errors": form.errors}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class DeleteTemplateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """
        Handles DELETE requests to delete the survey template group.
        """
        try:
            title = request.GET.get("title")
            if title == "None":
                return Response({"message": _("This template group cannot be deleted.")}, status=403)

            SurveyTemplate.objects.filter(title=title).delete()
            return Response({"message": _("Template group deleted.")}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class QuestionAddAPI(APIView):
    """
    API to add a survey question to the templates.
    """

    def get(self, request):
        """
        Handle GET requests to pre-fill the form with template data.
        """
        template = None
        title = request.GET.get("title")
        if title:
            try:
                template = SurveyTemplate.objects.filter(title=title)
                if not template.exists():
                    return Response(
                        {"error": "No template found with the given title."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        form = AddQuestionForm(initial={"template_ids": template})
        return Response(
            {"form_data": form.initial}, status=status.HTTP_200_OK
        )

    def post(self, request):
        """
        Handle POST requests to add a new question.
        """
        try:
            form = AddQuestionForm(request.data)
            if form.is_valid():
                form.save()
                return Response(
                    {"message": "Question added successfully."},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"error": form.errors}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        


class CandidateSelectAPI(APIView):
    """
    API to select all candidates or paginated candidates.
    """

    def get(self, request):
        """
        Handle GET requests to fetch candidates.
        """
        try:
            page_number = request.GET.get("page")

            if page_number == "all":
                candidates = Candidate.objects.filter(is_active=True)
            else:
                candidates = Candidate.objects.all()

            candidate_ids = [str(candidate.id) for candidate in candidates]
            total_count = candidates.count()

            response_data = {
                "candidate_ids": candidate_ids,
                "total_count": total_count,
                "message": "Candidates fetched successfully.",
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        
        



class CandidateSelectFilterAPI(APIView):
    """
    API to select all filtered candidates.
    """

    def get(self, request):
        """
        Handle GET requests to fetch filtered candidates.
        """
        try:
            page_number = request.GET.get("page")
            filtered = request.GET.get("filter")

            # Parse the filter JSON string into a dictionary
            filters = json.loads(filtered) if filtered else {}

            # Apply filters using CandidateFilter
            candidate_filter = CandidateFilter(filters, queryset=Candidate.objects.all())
            filtered_candidates = candidate_filter.qs

            # If page_number is "all", return all active candidates
            if page_number == "all":
                filtered_candidates = filtered_candidates.filter(is_active=True)

            # Prepare response data
            candidate_ids = [str(candidate.id) for candidate in filtered_candidates]
            total_count = filtered_candidates.count()

            response_data = {
                "candidate_ids": candidate_ids,
                "total_count": total_count,
                "message": "Filtered candidates fetched successfully.",
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid JSON format in 'filter' parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )        
 

class ViewQuestionTemplateAPIView(APIView):
    """
    APIView to view the question templates and return data as JSON.
    """

    def _serialize_page(self, page):
        """
        Helper method to serialize paginated data.
        If page is a Django Paginator Page instance, we return pagination details.
        """
        # If the page object has a paginator attribute, we assume it's a Page instance.
        if hasattr(page, "paginator"):
            # If the object_list supports .values() (i.e. it's a QuerySet), convert it to a list of dicts.
            if hasattr(page.object_list, "values"):
                items = list(page.object_list.values())
            else:
                items = list(page.object_list)
            return {
                "results": items,
                "page": page.number,
                "num_pages": page.paginator.num_pages,
                "count": page.paginator.count,
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
            }
        # Otherwise, assume the page is already serializable.
        return page

    def get(self, request, format=None):
        # Fetch all recruitment survey questions.
        questions = RecruitmentSurvey.objects.all()

        # Group questions by template title for those with a non-null template_id.
        templates_grouped = group_by_queryset(
            questions.filter(template_id__isnull=False).distinct(),
            "template_id__title",
            page=request.GET.get("template_page"),
            page_name="template_page",
            records_per_page=get_pagination(),
        )

        # Build a list from the grouped templates.
        all_template_object_list = []
        for template in templates_grouped:
            all_template_object_list.append(template)

        # Fetch all survey templates and extract their titles.
        survey_templates_qs = SurveyTemplate.objects.all()
        all_templates = survey_templates_qs.values_list("title", flat=True)
        used_templates = questions.values_list("template_id__title", flat=True)

        # Identify templates that are not used.
        unused_templates = list(set(all_templates) - set(used_templates))
        unused_groups = [
            {"grouper": template_name, "list": [], "dynamic_name": ""}
            for template_name in unused_templates
        ]
        all_template_object_list += unused_groups

        # Paginate the templates, survey templates, and questions.
        templates_paginated = paginator_qry(
            all_template_object_list, request.GET.get("template_page")
        )
        survey_templates_paginated = paginator_qry(
            survey_templates_qs, request.GET.get("survey_template_page")
        )
        questions_paginated = paginator_qry(questions, request.GET.get("page"))

        # Prepare a list of question IDs from the current page.
        requests_ids = [instance.id for instance in questions_paginated.object_list]

        # Build the response data.
        data = {
            "questions": self._serialize_page(questions_paginated),
            "templates": self._serialize_page(templates_paginated),
            "survey_templates": self._serialize_page(survey_templates_paginated),
            "requests_ids": requests_ids,
        }

        return Response(data)




from urllib.parse import parse_qs

class SkillZoneAPIView(APIView):
    """
    APIView to show Skill Zone data as JSON.
    """

    def _serialize_page(self, page):
        """
        Helper method to serialize paginated data.
        """
        if hasattr(page, "paginator"):
            return {
                "results": page.object_list,
                "page": page.number,
                "num_pages": page.paginator.num_pages,
                "count": page.paginator.count,
                "has_next": page.has_next(),
                "has_previous": page.has_previous(),
            }
        return page

    def get(self, request, format=None):
        # Filter candidates by GET parameters and only active ones.
        candidates = SkillZoneCandFilter(request.GET).qs.filter(is_active=True)

        # Group candidates by 'skill_zone_id' using the provided page number.
        skill_groups_paginated = group_by_queryset(
            candidates,
            "skill_zone_id",
            request.GET.get("page"),
            "page",
        )

        # Build a list of all zone objects from the grouped data.
        all_zones = []
        for zone in skill_groups_paginated:
            all_zones.append(zone["grouper"])

        # Retrieve all active skill zones via another filter.
        skill_zone_filtered = SkillZoneFilter(request.GET).qs.filter(is_active=True)
        all_zone_objects = list(skill_zone_filtered)

        # Identify unused skill zones by subtracting used zones.
        unused_skill_zones = list(set(all_zone_objects) - set(all_zones))

        # For each unused zone, create a group dictionary with empty details.
        unused_zones = []
        for zone in unused_skill_zones:
            unused_zones.append({
                "grouper": zone,
                "list": [],
                "dynamic_name": "",
            })

        # Combine the groups from the candidates with the unused zones.
        combined_skill_groups = skill_groups_paginated.object_list + unused_zones
        skill_groups_final = paginator_qry(combined_skill_groups, request.GET.get("page"))

        # Retrieve GET parameters as a query string and parse them into a dictionary.
        previous_data = request.GET.urlencode()
        data_dict = parse_qs(previous_data)
        get_key_instances(SkillZone, data_dict)

        # Determine if there are any skill zone groups.
        empty = not bool(skill_groups_final.object_list)

        # Build the response context.
        context = {
            "skill_zones": self._serialize_page(skill_groups_final),
            "page": request.GET.get("page"),
            "pd": previous_data,
            "filter_dict": data_dict,
            "empty": empty,
        }

        return Response(context)


class SkillZoneCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]


    def post(self, request):
        """
        Handles POST requests to create a skill zone.
        """
        try:
            form = SkillZoneCreateForm(request.POST)
            if form.is_valid():
                form.save()
                return Response({"message": _("Skill Zone created successfully."), "script": "<script>window.location.reload()</script>"}, status=201)
            else:
                return Response({"errors": form.errors}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)





class SkillZoneUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    

    def post(self, request, sz_id):
        """
        Handles POST requests to update a skill zone.
        """
        try:
            skill_zone = get_object_or_404(SkillZone, id=sz_id)
            form = SkillZoneCreateForm(request.POST, instance=skill_zone)
            if form.is_valid():
                form.save()
                return Response({"message": _("Skill Zone updated successfully."), "script": "<script>window.location.reload()</script>"}, status=200)
            else:
                return Response({"errors": form.errors}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class SkillZoneDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, sz_id):
        """
        Handles DELETE requests to delete a skill zone.
        """
        try:
            skill_zone = get_object_or_404(SkillZone, id=sz_id)
            skill_zone.delete()
            return Response({"message": _("Skill zone deleted successfully.")}, status=200)
        except SkillZone.DoesNotExist:
            return Response({"error": _("Skill zone not found.")}, status=404)
        except ProtectedError:
            return Response({"error": _("Related entries exist, so this skill zone cannot be deleted.")}, status=403)
        except Exception as e:
            return Response({"error": str(e)}, status=500)






class SkillZoneArchiveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sz_id):
        """
        Handles POST requests to archive or un-archive a skill zone.
        """
        try:
            skill_zone = get_object_or_404(SkillZone, id=sz_id)
            is_active = skill_zone.is_active

            if is_active:
                skill_zone.is_active = False
                skill_zone_candidates = SkillZoneCandidate.objects.filter(skill_zone_id=sz_id)
                for candidate in skill_zone_candidates:
                    candidate.is_active = False
                    candidate.save()
                message = _("Skill zone archived successfully.")
            else:
                skill_zone.is_active = True
                skill_zone_candidates = SkillZoneCandidate.objects.filter(skill_zone_id=sz_id)
                for candidate in skill_zone_candidates:
                    candidate.is_active = True
                    candidate.save()
                message = _("Skill zone unarchived successfully.")
                
            skill_zone.save()
            return Response({"message": message}, status=200)
        except SkillZone.DoesNotExist:
            return Response({"error": _("Skill zone not found.")}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)





class SkillZoneFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to filter and show Skill zone view.
        """
        try:
            template = "skill_zone/skill_zone_list.html"
            if request.GET.get("view") == "card":
                template = "skill_zone/skill_zone_card.html"

            candidates = SkillZoneCandFilter(request.GET).qs
            skill_zone_filtered = SkillZoneFilter(request.GET).qs
            if request.GET.get("is_active") == "false":
                skill_zone_filtered = SkillZoneFilter(request.GET).qs.filter(is_active=False)
                candidates = SkillZoneCandFilter(request.GET).qs.filter(is_active=False)
            else:
                skill_zone_filtered = SkillZoneFilter(request.GET).qs.filter(is_active=True)
                candidates = SkillZoneCandFilter(request.GET).qs.filter(is_active=True)

            skill_groups = group_by_queryset(
                candidates,
                "skill_zone_id",
                request.GET.get("page"),
                "page",
            )

            all_zones = []
            for zone in skill_groups:
                all_zones.append(zone["grouper"])

            all_zone_objects = list(skill_zone_filtered)
            unused_skill_zones = list(set(all_zone_objects) - set(all_zones))

            unused_zones = []
            for zone in unused_skill_zones:
                unused_zones.append(
                    {
                        "grouper": SkillZoneSerializer(zone).data,
                        "list": [],
                        "dynamic_name": "",
                    }
                )

            skill_groups_list = skill_groups.object_list + unused_zones
            skill_groups_page = paginator_qry(skill_groups_list, request.GET.get("page"))
            skill_groups_data = [SkillZoneSerializer(zone["grouper"]).data for zone in skill_groups_page.object_list]

            previous_data = request.GET.urlencode()
            data_dict = parse_qs(previous_data)
            get_key_instances(SkillZone, data_dict)

            response_data = {
                "skill_zones": skill_groups_data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "pagination": {
                    "current_page": skill_groups_page.number,
                    "total_pages": skill_groups_page.paginator.num_pages
                }
            }

            return Response(response_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class SkillZoneCandidateCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sz_id):
        """
        Handles GET requests to render the skill zone candidate creation form.
        """
        try:
            skill_zone = get_object_or_404(SkillZone, id=sz_id)
            form = SkillZoneCandidateForm(initial={"skill_zone_id": skill_zone})
            response_data = {"form": form.as_p(), "sz_id": sz_id}
            return Response(response_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def post(self, request, sz_id):
        """
        Handles POST requests to add candidates to a skill zone.
        """
        try:
            skill_zone = get_object_or_404(SkillZone, id=sz_id)
            form = SkillZoneCandidateForm(request.POST)
            if form.is_valid():
                form.save()
                return Response({"message": _("Candidate added successfully."), "script": "<script>window.location.reload()</script>"}, status=201)
            else:
                return Response({"errors": form.errors}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class SkillZoneCandEditAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sz_cand_id):
        """
        Handles GET requests to render the skill zone candidate edit form.
        """
        try:
            skill_zone_cand = get_object_or_404(SkillZoneCandidate, id=sz_cand_id)
            form = SkillZoneCandidateForm(instance=skill_zone_cand)
            response_data = {"form": form.as_p(), "sz_cand_id": sz_cand_id}
            return Response(response_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def post(self, request, sz_cand_id):
        """
        Handles POST requests to edit a candidate in a skill zone.
        """
        try:
            skill_zone_cand = get_object_or_404(SkillZoneCandidate, id=sz_cand_id)
            form = SkillZoneCandidateForm(request.POST, instance=skill_zone_cand)
            if form.is_valid():
                form.save()
                return Response({"message": _("Candidate edited successfully."), "script": "<script>window.location.reload()</script>"}, status=200)
            else:
                return Response({"errors": form.errors}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)





class SkillZoneCandFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to filter the skill zone candidates.
        """
        try:
            template = "skill_zone_cand/skill_zone_cand_card.html"
            if request.GET.get("view") == "list":
                template = "skill_zone_cand/skill_zone_cand_list.html"

            candidates = SkillZoneCandidate.objects.all()
            candidates_filter = SkillZoneCandFilter(request.GET, queryset=candidates).qs
            paginated_candidates = paginator_qry(candidates_filter, request.GET.get("page"))
            
            previous_data = request.GET.urlencode()
            data_dict = parse_qs(previous_data)
            get_key_instances(SkillZoneCandidate, data_dict)

            response_data = {
                "candidates": SkillZoneCandidateSerializer(paginated_candidates.object_list, many=True).data,
                "pd": previous_data,
                "filter_dict": data_dict,
                "f": SkillZoneCandFilter().data,
                "pagination": {
                    "current_page": paginated_candidates.number,
                    "total_pages": paginated_candidates.paginator.num_pages
                }
            }

            return Response(response_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class SkillZoneCandArchiveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sz_cand_id):
        """
        Handles POST requests to archive or un-archive a Skill zone candidate.
        """
        try:
            skill_zone_cand = get_object_or_404(SkillZoneCandidate, id=sz_cand_id)
            is_active = skill_zone_cand.is_active

            if is_active:
                skill_zone_cand.is_active = False
                message = _("Candidate archived successfully.")
            else:
                skill_zone_cand.is_active = True
                message = _("Candidate unarchived successfully.")

            skill_zone_cand.save()
            return Response({"message": message}, status=200)
        except SkillZoneCandidate.DoesNotExist:
            return Response({"error": _("Candidate not found.")}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class SkillZoneCandDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, sz_cand_id):
        """
        Handles DELETE requests to delete a Skill zone candidate.
        """
        try:
            skill_zone_cand = get_object_or_404(SkillZoneCandidate, id=sz_cand_id)
            skill_zone_cand.delete()
            return Response({"message": _("Skill zone deleted successfully.")}, status=200)
        except SkillZoneCandidate.DoesNotExist:
            return Response({"error": _("Skill zone not found.")}, status=404)
        except ProtectedError:
            return Response({"error": _("Related entries exist, so this skill zone candidate cannot be deleted.")}, status=403)
        except Exception as e:
            return Response({"error": str(e)}, status=500)




class GetTemplateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, obj_id=None):
        """
        Handles GET requests to return the mail template.
        """
        try:
            body = ""
            if obj_id:
                template_instance = get_object_or_404(HorillaMailTemplate, id=obj_id)
                template_bdy = Template(template_instance.body)
            elif request.GET.get("word"):
                word = request.GET.get("word")
                template_bdy = Template("{{" + word + "}}")
            else:
                return Response({"error": _("No valid template identifier provided.")}, status=400)

            candidate_id = request.GET.get("candidate_id")
            if candidate_id:
                candidate_obj = get_object_or_404(Candidate, id=candidate_id)
                context = Context(
                    {"instance": candidate_obj, "self": request.user.employee_get}
                )
                body = template_bdy.render(context) or " "

            return JsonResponse({"body": body})
        except HorillaMailTemplate.DoesNotExist:
            return Response({"error": _("Template not found.")}, status=404)
        except Candidate.DoesNotExist:
            return Response({"error": _("Candidate not found.")}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



from django.db import IntegrityError


class CreateCandidateRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, cand_id):
        """
        Handles POST requests to create a rating for the candidate.
        """
        try:
            candidate = get_object_or_404(Candidate, id=cand_id)
            employee_id = request.user.employee_get
            rating = request.POST.get("rating")

            if not rating:
                return Response({"error": "Rating is required."}, status=400)

            try:
                CandidateRating.objects.create(
                    candidate_id=candidate, rating=rating, employee_id=employee_id
                )
            except IntegrityError:
                return Response({"error": "This candidate has already been rated by this employee."}, status=400)

            return Response({"message": "Rating created successfully."}, status=201)
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)





class OpenRecruitmentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return a JSON response with open recruitments.
        """
        try:
            recruitments = Recruitment.default.filter(closed=False, is_published=True)
            serializer = RecruitmentSerializer(recruitments, many=True)
            return Response(serializer.data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class RecruitmentDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        """
        Handles GET requests to return JSON response with recruitment details.
        """
        try:
            recruitment = Recruitment.default.get(id=id)
            serializer = RecruitmentSerializer(recruitment)
            return Response(serializer.data, status=200)
        except Recruitment.DoesNotExist:
            return Response({"error": "Recruitment not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)






class AddMoreFilesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        """
        Handles POST requests to add more files to the stage candidate note.
        """
        try:
            note = StageNote.objects.get(id=id)
            files = request.FILES.getlist("files")
            files_ids = []
            for file in files:
                instance = StageFiles.objects.create(files=file)
                files_ids.append(instance.id)
                note.stage_files.add(instance.id)

            return Response({"message": "Files added successfully.", "files_ids": files_ids}, status=200)
        except StageNote.DoesNotExist:
            return Response({"error": "Stage note not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
