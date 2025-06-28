from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from pms.models import EmployeeObjective, Objective, EmployeeKeyResult,KeyResult,Employee,Comment,Feedback,Answer,AnonymousFeedback,KeyResultFeedback,Question,QuestionOptions,QuestionTemplate,Period,Meetings,MeetingsAnswer,BonusPointSetting
from rest_framework import status
from .serializers import EmployeeObjectiveSerializer,KeyResultSerializer,ObjectiveSerializer,EmployeeKeyResultSerializer,FeedbackSerializer,KeyResultFeedbackSerializer,AnswerSerializer, QuestionSerializer, QuestionOptionsSerializer,QuestionTemplateSerializer,PeriodSerializer,MeetingsSerializer
from pms.views import objective_filter_pagination,obj_form_save ,paginator_qry,sortby, get_key_instances,objective_filter_pagination,objective_history ,get_pagination,group_by_queryset,send_feedback_notifications,filter_pagination_feedback ,check_permission_feedback_detailed_view,filtersubordinates
from pms.forms import ObjectiveForm, PeriodForm, KRForm, AddAssigneesForm,ObjectiveCommentForm,KeyResultForm,EmployeeObjectiveCreateForm,EmployeeObjectiveForm,FeedbackForm,QuestionForm,QuestionTemplateForm,AnonymousFeedbackForm,EmployeeKeyResultForm, MeetingsForm
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.urls import reverse
from django.contrib import messages
from notifications.signals import notify
from pms.filters import ActualKeyResultFilter,EmployeeObjectiveFilter,KeyResultFilter,ObjectiveFilter,MeetingsFilter
import json
from urllib.parse import urlparse, parse_qs, urlencode
from rest_framework.pagination import PageNumberPagination
from itertools import tee
import datetime
from django.core.paginator import Paginator
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.db.models import ProtectedError
from django.db import IntegrityError
from django.contrib.auth.models import User
from dateutil.relativedelta import relativedelta
from base.methods import closest_numbers


from employee.authentication import JWTAuthentication



class ObjectiveListView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to show all the objectives and returns objects based on user level.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return the list of objectives.
        """
        try:
            employee = request.user.employee_get
            objective_own = EmployeeObjective.objects.filter(
                employee_id=employee, archive=False
            ).distinct()

            context = objective_filter_pagination(request, objective_own)

            # Assuming 'own_objectives' contains the filtered objectives for the employee
            if 'own_objectives' not in context:
                return Response({"detail": "'own_objectives' key not found in context"}, status=500)

            serializer = EmployeeObjectiveSerializer(context['own_objectives'], many=True)
            return Response(serializer.data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class ObjectiveCreationView(APIView):
    """
    API view for objective creation, and returns an objective form.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


    def post(self, request):
        """
        Handles POST requests to create an objective.
        """
        try:
            objective_form = ObjectiveForm(request.POST)
            if objective_form.is_valid():
                obj_form_save(request, objective_form)
                return Response({"message": "Objective created successfully"})
            
            context = {
                "objective_form_errors": objective_form.errors,
                "period_form": PeriodForm().initial,  # Replace with appropriate data if needed
                "kr_form": KRForm().initial,          # Replace with appropriate data if needed
            }
            return Response(context, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class ObjectiveUpdateView(APIView):
    """
    API view for updating an objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

   
    def post(self, request, obj_id):
        """
        Handles POST requests to update an objective.
        """
        try:
            instance = get_object_or_404(Objective, id=obj_id)
            objective_form = ObjectiveForm(request.POST, instance=instance)
            if objective_form.is_valid():
                objective = objective_form.save()
                assignees = objective_form.cleaned_data["assignees"]
                start_date = objective_form.cleaned_data["start_date"]
                default_krs = objective_form.cleaned_data["key_result_id"]
                new_emp = [assignee for assignee in assignees]

                delete_list = []
                if objective.employee_objective.exists():
                    emp_objectives = objective.employee_objective.all()
                    existing_emp = [emp.employee_id for emp in emp_objectives]
                    delete_list = [
                        employee for employee in existing_emp if employee not in new_emp
                    ]
                if len(delete_list) > 0:
                    for emp in delete_list:
                        EmployeeObjective.objects.filter(
                            employee_id=emp, objective_id=objective
                        ).delete()
                for emp in new_emp:
                    if EmployeeObjective.objects.filter(
                        employee_id=emp, objective_id=objective
                    ).exists():
                        emp_obj = EmployeeObjective.objects.filter(
                            employee_id=emp, objective_id=objective
                        ).first()
                        emp_obj.start_date = start_date
                    else:
                        emp_obj = EmployeeObjective(
                            employee_id=emp, objective_id=objective, start_date=start_date
                        )
                    emp_obj.save()
                    # assigning default key result
                    if default_krs:
                        for key in default_krs:
                            if not EmployeeKeyResult.objects.filter(
                                employee_objective_id=emp_obj, key_result_id=key
                            ).exists():
                                emp_kr = EmployeeKeyResult.objects.create(
                                    employee_objective_id=emp_obj,
                                    key_result_id=key,
                                    progress_type=key.progress_type,
                                    target_value=key.target_value,
                                )
                                emp_kr.save()

                    notify.send(
                        request.user.employee_get,
                        recipient=emp.employee_user_id,
                        verb="You got an OKR!.",
                        verb_ar="لقد حققت هدفًا ونتيجة رئيسية!",
                        verb_de="Du hast ein Ziel-Key-Ergebnis erreicht!",
                        verb_es="¡Has logrado un Resultado Clave de Objetivo!",
                        verb_fr="Vous avez atteint un Résultat Clé d'Objectif !",
                        redirect=reverse(
                            "objective-detailed-view", kwargs={"obj_id": objective.id}
                        ),
                    )
                messages.success(
                    request,
                    _("Objective %(objective)s Updated") % {"objective": instance},
                )
                return Response({"message": "Objective updated successfully"})
            
            context = {
                "objective_form_errors": objective_form.errors,
                "kr_form": KRForm().initial,          # Replace with appropriate data if needed
                "update": True
            }
            return Response(context, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class ViewKeyResultView(APIView):
    """
    API view to view all the key result instances.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to return the key result instances.
        """
        try:
            krs = KeyResult.objects.all()
            krs_filter = ActualKeyResultFilter(request.GET, queryset=krs)
            krs = paginator_qry(krs_filter.qs, request.GET.get("page"))
            krs_ids = [instance.id for instance in krs.object_list]

            serializer = KeyResultSerializer(krs.object_list, many=True)
            context = {
                "krs": serializer.data,
                "filtered_krs": KeyResultSerializer(krs_filter.qs, many=True).data,
                "krs_ids": krs_ids,
            }

            return Response(context)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class FilterKeyResultView(APIView):
    """
    API view to filter and retrieve a list of key results based on the provided query parameters.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to return the filtered key results.
        """
        try:
            query_string = request.GET.urlencode()
            krs = ActualKeyResultFilter(request.GET).qs
            krs = sortby(request, krs, "sortby")
            krs = paginator_qry(krs, request.GET.get("page"))
            allowance_ids = [instance.id for instance in krs.object_list]
            data_dict = parse_qs(query_string)
            get_key_instances(KeyResult, data_dict)

            context = {
                "krs": KeyResultSerializer(krs.object_list, many=True).data,
                "pd": query_string,
                "filter_dict": data_dict,
                "krs_ids": allowance_ids,
            }

            return Response(context)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class KeyResultCreateView(APIView):
    """
    API view to create a key result.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to create a key result.
        """
        try:
            form = KRForm(request.data)  # Use request.data for JSON payload
            if form.is_valid():
                instance = form.save()
                messages.success(
                    request,
                    _("Key result %(key_result)s created successfully")
                    % {"key_result": instance},
                )
                mutable_get = request.GET.copy()

                key_result_ids = mutable_get.getlist("key_result_id", [])
                if "create_new_key_result" in key_result_ids:
                    key_result_ids.remove("create_new_key_result")
                key_result_ids.append(str(instance.id))
                mutable_get.setlist("key_result_id", key_result_ids)
                data = mutable_get.urlencode()
                redirect_url = f"/pms/{request.GET.get('dataUrl')}{data}"
                parsed_url = urlparse(redirect_url)
                query_params = parse_qs(parsed_url.query)
                query_params.pop("dataUrl", None)
                new_query_string = urlencode(query_params, doseq=True)
                redirect_url = f"{parsed_url.path}?{new_query_string}"

                return Response({"message": "Key result created successfully", "redirect_url": redirect_url})
            else:
                return Response({"form_errors": form.errors}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class KeyResultCreateOrUpdateView(APIView):
    """
    API view for creating or updating a key result.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, kr_id=None):
        """
        Handles POST requests to create or update a key result.
        """
        try:
            key_result = None
            if kr_id is not None:
                key_result = get_object_or_404(KeyResult, id=kr_id)
                form = KRForm(request.data, instance=key_result)
                if form.is_valid():
                    instance = form.save()
                    messages.success(
                        request,
                        _("Key result %(key_result)s updated successfully")
                        % {"key_result": instance},
                    )
                    return Response({"message": "Key result updated successfully"})
                return Response({"form_errors": form.errors}, status=400)
            else:
                form = KRForm(request.data)
                if form.is_valid():
                    instance = form.save()
                    messages.success(
                        request,
                        _("Key result %(key_result)s created successfully")
                        % {"key_result": instance},
                    )
                    return Response({"message": "Key result created successfully"})
                return Response({"form_errors": form.errors}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class AddAssigneesView(APIView):
    """
    API view to add assignees to an objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id):
        """
        Handles POST requests to add assignees to an objective.
        """
        try:
            objective = get_object_or_404(Objective, id=obj_id)
            form = AddAssigneesForm(request.data, instance=objective)
            if form.is_valid():
                objective = form.save(commit=False)
                assignees = form.cleaned_data["assignees"]
                start_date = form.cleaned_data["start_date"]
                for emp in assignees:
                    objective.assignees.add(emp)
                    if not EmployeeObjective.objects.filter(
                        employee_id=emp, objective_id=objective
                    ).exists():
                        emp_obj = EmployeeObjective(
                            employee_id=emp, objective_id=objective, start_date=start_date
                        )
                    emp_obj.save()
                    # Assigning default key results
                    default_krs = objective.key_result_id.all()
                    if default_krs:
                        for key_result in default_krs:
                            if not EmployeeKeyResult.objects.filter(
                                employee_objective_id=emp_obj, key_result_id=key_result
                            ).exists():
                                emp_kr = EmployeeKeyResult.objects.create(
                                    employee_objective_id=emp_obj,
                                    key_result_id=key_result,
                                    progress_type=key_result.progress_type,
                                    target_value=key_result.target_value,
                                    start_date=start_date,
                                )
                    notify.send(
                        request.user.employee_get,
                        recipient=emp.employee_user_id,
                        verb="You got an OKR!.",
                        verb_ar="لقد حققت هدفًا ونتيجة رئيسية!",
                        verb_de="Du hast ein Ziel-Key-Ergebnis erreicht!",
                        verb_es="¡Has logrado un Resultado Clave de Objetivo!",
                        verb_fr="Vous avez atteint un Résultat Clé d'Objectif !",
                        redirect=reverse(
                            "objective-detailed-view", kwargs={"obj_id": objective.id}
                        ),
                    )
                objective.save()
                messages.success(
                    request,
                    _("Objective %(objective)s Updated") % {"objective": objective},
                )
                return Response({"message": "Assignees added successfully"})
            return Response({"form_errors": form.errors}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class ObjectiveDeleteView(APIView):
    """
    API view to delete an objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id):
        """
        Handles POST requests to delete an objective.
        """
        try:
            objective = get_object_or_404(Objective, id=obj_id)
            if not objective.employee_objective.exists():
                objective.delete()
                messages.success(
                    request,
                    _("Objective %(objective)s deleted") % {"objective": objective},
                )
                return Response({"message": "Objective deleted successfully"})
            else:
                messages.warning(
                    request,
                    _("You can't delete objective %(objective)s, related entries exist") % {"objective": objective},
                )
                return Response({"detail": "Related entries exist, cannot delete"}, status=400)
        except Objective.DoesNotExist:
            messages.error(request, _("Objective not found."))
            return Response({"detail": "Objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class ObjectiveManagerRemoveView(APIView):
    """
    API view to remove a manager from an objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id, manager_id):
        """
        Handles POST requests to remove a manager from an objective.
        """
        try:
            objective = get_object_or_404(Objective, id=obj_id)
            objective.managers.remove(manager_id)
            return Response({"message": "Manager removed successfully"})
        except Objective.DoesNotExist:
            return Response({"detail": "Objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class KeyResultRemoveView(APIView):
    """
    API view to remove a Key Result from an objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id, kr_id):
        """
        Handles POST requests to remove a Key Result from an objective.
        """
        try:
            objective = get_object_or_404(Objective, id=obj_id)
            objective.key_result_id.remove(kr_id)
            return Response({"message": "Key Result removed successfully"})
        except Objective.DoesNotExist:
            return Response({"detail": "Objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class AssigneesRemoveView(APIView):
    """
    API view to remove an assignee from an objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id, emp_id):
        """
        Handles POST requests to remove an assignee from an objective.
        """
        try:
            objective = get_object_or_404(Objective, id=obj_id)
            employee_objective = get_object_or_404(EmployeeObjective, employee_id=emp_id, objective_id=obj_id)
            employee_objective.delete()
            objective.assignees.remove(emp_id)
            return Response({"message": "Assignee removed successfully"})
        except Objective.DoesNotExist:
            return Response({"detail": "Objective not found"}, status=404)
        except EmployeeObjective.DoesNotExist:
            return Response({"detail": "EmployeeObjective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



 
class ObjectiveListSearchView(APIView):
    """
    API view to search and list objectives.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to return searched and filtered objectives.
        """
        try:
            search_val = request.GET.get("search", "")
            employee = request.user.employee_get

            objective_own = EmployeeObjective.objects.filter(employee_id=employee)
            context = objective_filter_pagination(request, objective_own)

            response_data = {
                "objectives": context["object_list"],  # Assuming 'object_list' key holds filtered objectives
                "pagination": context.get("pagination", {}),  # Include pagination data if available
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



  # Ensure you have this import based on your utility implementation

class ObjectivePagination(PageNumberPagination):
    """
    Custom pagination class to handle objective pagination.
    """
    page_size = 10  # Set default page size
    page_size_query_param = 'page_size'
    max_page_size = 100
class ObjectiveListSearchView(APIView):
    """
    API view to search and list objectives.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

   
    def get(self, request, *args, **kwargs):
        try:
            search_val = request.GET.get("search", "")
            employee = request.user.employee_get

            # Filter objectives based on the employee
            objective_own = EmployeeObjective.objects.filter(employee_id=employee, objective__icontains=search_val)
            
            # Paginate objectives
            paginator = ObjectivePagination()
            page = paginator.paginate_queryset(objective_own, request)
            
            # Serialize paginated data
            serialized_data = EmployeeObjectiveSerializer(page, many=True).data
            
            # Return grouped data or normal list based on 'field' parameter
            if request.GET.get("field"):
                return paginator.get_paginated_response({"grouped_data": serialized_data})
            
            return paginator.get_paginated_response({"objectives": serialized_data})
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class ObjectiveDashboardView(APIView):
    """
    API view for the objective dashboard.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to return searched and filtered objectives.
        """
        try:
            emp_objectives = EmployeeObjectiveFilter(request.GET).qs

            response_data = {
                "emp_objectives": list(emp_objectives.values()),  # Converting queryset to a list of dictionaries
            }

            return Response(response_data)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class ObjectiveHistoryView(APIView):
    """
    API view to get the history of an EmployeeObjective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def pair_history(self, iterable):
        """
        Helper function to return pairs of history records.
        """
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    def key_result_history(self, key_result, changed_key_results):
        """
        Helper function to get the history of a key result.
        """
        key_result_iterator = key_result.history.all().order_by("history_date").iterator()
        for record_pair in self.pair_history(key_result_iterator):
            old_record, new_record = record_pair
            delta = new_record.diff_against(old_record)
            history_user_id = delta.new_record.history_user
            history_change_date = delta.new_record.history_date
            employee = Employee.objects.filter(employee_user_id=history_user_id).first()
            key_result_instance = delta.new_record.key_result_id
            changed_key_results.append(
                {
                    "delta": delta,
                    "changed_user": employee,
                    "changed_date": history_change_date,
                    "k_r": key_result_instance,
                }
            )

    def get(self, request, emp_obj_id):
        """
        Handles GET requests to return the history of an EmployeeObjective.
        """
        try:
            obj_objective = get_object_or_404(EmployeeObjective, id=emp_obj_id)
            all_key_results = EmployeeKeyResult.objects.filter(employee_objective_id=obj_objective)
            changed_key_results = []

            for key_result in all_key_results:
                # Loop each key result and generate its history
                self.key_result_history(key_result, changed_key_results)

            changed_key_results.reverse()

            return Response(changed_key_results)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class ObjectiveDetailedViewActivity(APIView):
    """
    API view to show objective activity.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def pair_history(self, iterable):
        """
        Helper function to return pairs of history records.
        """
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    def get(self, request, id):
        """
        Handles GET requests to return the activity of an objective.
        """
        try:
            objective = get_object_or_404(EmployeeObjective, id=id)
            key_result_history = objective_history(id)
            history = objective.tracking()
            comments = Comment.objects.filter(employee_objective_id=objective)
            activity_list = []

            for hist in history:
                hist["date"] = hist["pair"][0].history_date
                activity_list.append(hist)

            for com in comments:
                comment = {
                    "type": "comment",
                    "comment": com,
                    "date": com.created_at,
                }
                activity_list.append(comment)

            for key in key_result_history:
                key_result = {
                    "type": "key_result",
                    "key_result": key,
                    "date": key["changed_date"],
                }
                activity_list.append(key_result)

            activity_list = sorted(activity_list, key=lambda x: x["date"], reverse=True)

            context = {
                "objective": objective,
                "historys": history,
                "comments": list(comments.values()),  # Converting queryset to a list of dictionaries
                "activity_list": activity_list,
            }

            return Response(context)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class ObjectiveDetailedViewComment(APIView):
    """
    API view to create a comment object for objective activity.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to create a comment for an objective activity.
        """
        comment_form = ObjectiveCommentForm(request.data)
        if comment_form.is_valid():
            objective = get_object_or_404(EmployeeObjective, id=id)
            form = comment_form.save(commit=False)
            form.employee_id = request.user.employee_get
            form.employee_objective_id = objective
            form.save()

            return Response({"message": "Comment created successfully"})
        return Response({"form_errors": comment_form.errors}, status=400)





class EmpObjectiveSearchView(APIView):
    """
    API view to search employee objectives.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, obj_id):
        """
        Handles GET requests to return searched and filtered employee objectives.
        """
        try:
            objective = get_object_or_404(Objective, id=obj_id)
            emp_objectives = objective.employee_objective.all()
            search_val = request.GET.get("search", "")
            emp_objectives = EmployeeObjectiveFilter(request.GET, queryset=emp_objectives).qs
            if not request.GET.get("archive") == "true":
                emp_objectives = emp_objectives.filter(archive=False)
            previous_data = request.GET.urlencode()
            emp_objectives = Paginator(emp_objectives, get_pagination())
            page = request.GET.get("page")
            emp_objectives = emp_objectives.get_page(page)
            data_dict = parse_qs(previous_data)
            get_key_instances(EmployeeObjective, data_dict)

            serializer = EmployeeObjectiveSerializer(emp_objectives, many=True)

            context = {
                "emp_objectives": serializer.data,
                "filter_dict": data_dict,
                "pg": previous_data,
                "objective": {
                    "id": objective.id,
                    "title": objective.title,
                    "description": objective.description,
                    # Include other necessary fields from the Objective model
                },
            }

            return Response(context)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class KRTableView(APIView):
    """
    API view to render a table view of Key Results associated with an employee objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, emp_objective_id):
        """
        Handles GET requests to return the Key Results associated with the specified EmployeeObjective.
        """
        try:
            emp_objective = get_object_or_404(EmployeeObjective, id=emp_objective_id)
            krs = emp_objective.employee_key_result.all()
            krs = Paginator(krs, get_pagination())
            krs_page = request.GET.get("krs_page")
            krs = krs.get_page(krs_page)
            previous_data = request.GET.urlencode()

            serializer = EmployeeKeyResultSerializer(krs, many=True)

            context = {
                "krs": serializer.data,
                "key_result_status": EmployeeKeyResult.STATUS_CHOICES,
                "emp_objective": {
                    "id": emp_objective.id,
                    "objective_id": emp_objective.objective_id.id,
                    "employee_id": emp_objective.employee_id.id,
                    # Include other necessary fields from the EmployeeObjective model
                },
                "pd": previous_data,
                "today": datetime.datetime.today().date(),
            }

            return Response(context)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class ObjectiveDetailedViewObjectiveStatus(APIView):
    """
    API view to update the status of an objective in the detailed view.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to update the status of an objective.
        """
        try:
            objective = get_object_or_404(EmployeeObjective, id=id)
            status = request.data.get("objective_status")
            
            # Validate the status value
            valid_statuses = [choice[0] for choice in EmployeeObjective.STATUS_CHOICES]
            if status not in valid_statuses:
                return Response({"detail": "Invalid objective status provided"}, status=400)

            objective.status = status
            objective.save()
            messages.info(
                request,
                _("Objective %(objective)s status updated") % {"objective": objective.objective},
            )
            return Response({"message": "Objective status updated successfully"})
        except EmployeeObjective.DoesNotExist:
            return Response({"detail": "Objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class ObjectiveDetailedViewKeyResultStatus(APIView):
    """
    API view to update the status of a key result in the objective detailed view.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id, kr_id):
        """
        Handles POST requests to update the status of a key result.
        """
        try:
            employee_key_result = get_object_or_404(EmployeeKeyResult, id=kr_id)
            status = request.data.get("key_result_status")

            # Validate the status value
            valid_statuses = [choice[0] for choice in EmployeeKeyResult.STATUS_CHOICES]
            if status not in valid_statuses:
                return Response({"detail": "Invalid key result status provided"}, status=400)

            current_value = employee_key_result.current_value
            target_value = employee_key_result.target_value

            if current_value >= target_value:
                employee_key_result.status = "Closed"
            else:
                employee_key_result.status = status
            employee_key_result.save()
            messages.info(request, _("Status has been updated"))

            return Response({"message": "Key result status updated successfully"})
        except EmployeeKeyResult.DoesNotExist:
            return Response({"detail": "Key result not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class ObjectiveDetailedViewCurrentValue(APIView):
    """
    API view to update the current value of a key result in the objective detailed view.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, kr_id):
        """
        Handles POST requests to update the current value of a key result.
        """
        try:
            current_value = request.data.get("current_value")
            employee_key_result = get_object_or_404(EmployeeKeyResult, id=kr_id)
            target_value = employee_key_result.target_value
            objective_id = employee_key_result.employee_objective_id.id

            if not current_value:
                return Response({"detail": "Current value not provided"}, status=400)
            
            try:
                current_value = int(current_value)
            except ValueError:
                return Response({"detail": "Invalid current value provided"}, status=400)

            if current_value < target_value:
                employee_key_result.current_value = current_value
                employee_key_result.save()
                messages.info(
                    request,
                    _("Current value of %(employee_key_result)s updated") % {"employee_key_result": employee_key_result},
                )
                return Response({"message": "Current value updated successfully"})
            elif current_value == target_value:
                employee_key_result.current_value = current_value
                employee_key_result.status = "Closed"
                employee_key_result.save()
                messages.info(
                    request,
                    _("Current value of %(employee_key_result)s updated") % {"employee_key_result": employee_key_result},
                )
                return Response({"message": "Current value updated and key result closed successfully"})
            else:
                messages.warning(request, _("Current value is greater than target value"))
                return Response({"detail": "Current value is greater than target value"}, status=400)
        except EmployeeKeyResult.DoesNotExist:
            return Response({"detail": "Key result not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class ObjectiveArchiveView(APIView):
    """
    API view to archive or un-archive an objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to archive or un-archive an objective.
        """
        try:
            objective = get_object_or_404(Objective, id=id)
            if objective.archive:
                objective.archive = False
                messages.info(request, _("Objective un-archived successfully!."))
            else:
                objective.archive = True
                messages.info(request, _("Objective archived successfully!."))
            objective.save()
            return Response({"message": "Objective status updated successfully"})
        except Objective.DoesNotExist:
            return Response({"detail": "Objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class ViewEmployeeObjective(APIView):
    """
    API view to render individual view of the employee objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, emp_obj_id):
        """
        Handles GET requests to return the individual view of the employee objective.
        """
        try:
            emp_objective = get_object_or_404(EmployeeObjective, id=emp_obj_id)
            context = {
                "instance": {
                    "id": emp_objective.id,
                    "employee_id": emp_objective.employee_id.id,
                    "objective_id": emp_objective.objective_id.id,
                    "status": emp_objective.status,
                    "archive": emp_objective.archive,
                    "start_date": emp_objective.start_date,
                    "end_date": emp_objective.end_date,
                    # Include other necessary fields from the EmployeeObjective model
                },
                "objective_key_result_status": EmployeeObjective.STATUS_CHOICES,
            }

            return Response(context)
        except EmployeeObjective.DoesNotExist:
            return Response({"detail": "Employee objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)






class CreateEmployeeObjectiveView(APIView):
    """
    API view to create an employee objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

   
    def post(self, request):
        """
        Handles POST requests to create an employee objective.
        """
        form = EmployeeObjectiveCreateForm(request.data)
        if form.is_valid():
            krs = list(form.cleaned_data.get("key_result_id", []))
            emp_obj = form.save(commit=False)
            obj = emp_obj.objective_id
            if not obj:
                return Response({"detail": "Objective ID is required"}, status=400)
            obj.assignees.add(emp_obj.employee_id)
            krs.extend([key_result for key_result in obj.key_result_id.all()])
            set_krs = set(krs)
            emp_obj.save()
            for kr in set_krs:
                emp_obj.key_result_id.add(kr)
                if not EmployeeKeyResult.objects.filter(
                    employee_objective_id=emp_obj, key_result_id=kr
                ).exists():
                    EmployeeKeyResult.objects.create(
                        employee_objective_id=emp_obj,
                        key_result_id=kr,
                        progress_type=kr.progress_type,
                        target_value=kr.target_value,
                        start_date=emp_obj.start_date,
                    )
            messages.success(request, _("Employee objective created successfully"))
            return HttpResponse("<script>window.location.reload()</script>")
        else:
            return Response({"form_errors": form.errors}, status=400)





class UpdateEmployeeObjectiveView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to update an employee objective with safe attribute handling.
    """

    def post(self, request, emp_obj_id, *args, **kwargs):
        try:
            # Fetch the EmployeeObjective, return 404 if not found
            emp_objective = get_object_or_404(EmployeeObjective, id=emp_obj_id)
            
            # Check if 'assignees' is an attribute and not None
            if hasattr(emp_objective, 'assignees') and emp_objective.assignees is not None:
                form = EmployeeObjectiveForm(request.POST, instance=emp_objective)
                if form.is_valid():
                    form.save()
                    return Response({"detail": _("Employee objective updated successfully")}, status=status.HTTP_200_OK)
                else:
                    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"detail": "Employee objective has no valid assignees."}, status=status.HTTP_400_BAD_REQUEST)

        except EmployeeObjective.DoesNotExist:
            return Response({"detail": "EmployeeObjective not found."}, status=status.HTTP_404_NOT_FOUND)
        except AttributeError as e:
            return Response({"detail": f"Attribute error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ArchiveEmployeeObjectiveView(APIView):
    """
    API view to archive or unarchive an employee objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, emp_obj_id):
        """
        Handles POST requests to archive or unarchive an employee objective.
        """
        try:
            emp_objective = get_object_or_404(EmployeeObjective, id=emp_obj_id)
            if emp_objective.archive:
                emp_objective.archive = False
                messages.success(request, _("Objective un-archived successfully!."))
            else:
                emp_objective.archive = True
                messages.success(request, _("Objective archived successfully!."))
            emp_objective.save()
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
        except EmployeeObjective.DoesNotExist:
            return Response({"detail": "Employee objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)


from django.http import HttpResponseRedirect, HttpResponse


class DeleteEmployeeObjectiveView(APIView):
    """
    API view to delete an employee objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, emp_obj_id):
        """
        Handles POST requests to delete an employee objective.
        """
        try:
            emp_objective = get_object_or_404(EmployeeObjective, id=emp_obj_id)
            single_view = request.GET.get("single_view")
            if emp_objective.employee_key_result.exists():
                messages.warning(request, _("You can't delete this objective, related entries exist"))
                return Response({"detail": "You can't delete this objective, related entries exist"}, status=400)
            else:
                employee = emp_objective.employee_id
                objective = emp_objective.objective_id
                emp_objective.delete()
                objective.assignees.remove(employee)
                messages.success(request, _("Objective deleted successfully!"))
                if not single_view:
                    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
                else:
                    return HttpResponse("<script>window.location.reload()</script>")
        except EmployeeObjective.DoesNotExist:
            return Response({"detail": "Employee objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class ChangeEmployeeObjectiveStatusView(APIView):
    """
    API view to change the status of an employee objective.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to change the status of an employee objective.
        """
        try:
            emp_obj_id = request.data.get("empObjId")
            status = request.data.get("status")
            if not emp_obj_id or not status:
                return Response({"detail": "Both empObjId and status are required"}, status=400)
            
            emp_objective = get_object_or_404(EmployeeObjective, id=emp_obj_id)
            if (
                request.user.has_perm("pms.change_employeeobjective")
                or emp_objective.employee_id == request.user.employee_get
                or request.user.employee_get in emp_objective.objective_id.managers.all()
            ):
                if emp_objective.status != status:
                    emp_objective.status = status
                    emp_objective.save()
                    messages.success(
                        request,
                        _(
                            f"The status of the objective '{emp_objective.objective_id}' has been changed to {emp_objective.status}."
                        ),
                    )
                    notify.send(
                        request.user.employee_get,
                        recipient=emp_objective.employee_id.employee_user_id,
                        verb=f"The status of the objective '{emp_objective.objective_id}' has been changed to {emp_objective.status}.",
                        verb_ar=f"تم تغيير حالة الهدف '{emp_objective.objective_id}' إلى {emp_objective.status}.",
                        verb_de=f"Der Status des Ziels '{emp_objective.objective_id}' wurde zu {emp_objective.status} geändert.",
                        verb_es=f"El estado del objetivo '{emp_objective.objective_id}' ha sido cambiado a {emp_objective.status}.",
                        verb_fr=f"Le statut de l'objectif '{emp_objective.objective_id}' a été changé à {emp_objective.status}.",
                        redirect=reverse(
                            "objective-detailed-view",
                            kwargs={"obj_id": emp_objective.objective_id.id},
                        ),
                    )
                    return Response({"message": "Objective status updated successfully"})
                else:
                    messages.info(request, _("The status of the objective is the same as selected."))
                    return Response({"detail": "The status of the objective is the same as selected."}, status=400)
            else:
                messages.info(request, _("You don't have permission."))
                return Response({"detail": "You don't have permission."}, status=403)
        except EmployeeObjective.DoesNotExist:
            return Response({"detail": "Employee objective not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class KeyResultView(APIView):
    """
    API view to view key results.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to return key results.
        """
        try:
            krs = KeyResultFilter(request.GET).qs
            krs = group_by_queryset(
                krs, "employee_objective_id__employee_id", request.GET.get("page"), "page"
            )

            serializer = EmployeeKeyResultSerializer(krs, many=True)

            return Response({
                "krs": serializer.data,
                "key_result_status": EmployeeKeyResult.STATUS_CHOICES,
            })
        except Exception as error:
            return Response({"detail": str(error)}, status=500)







class KeyResultCreationView(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, obj_id, obj_type, *args, **kwargs):
        try:
            employee = request.user.employee_get
            if obj_type == "individual":
                employee_objective = get_object_or_404(EmployeeObjective, id=int(obj_id))
                form_key_result = KeyResultForm(
                    request.POST, initial={"employee_objective_id": employee_objective}
                )
                if form_key_result.is_valid():
                    form = form_key_result.save(commit=False)
                    form.start_value = form.current_value
                    form.employee_objective_id = employee_objective
                    form.save()
                    return Response({"detail": _("Key result created successfully")}, status=status.HTTP_201_CREATED)
                else:
                    return Response(form_key_result.errors, status=status.HTTP_400_BAD_REQUEST)

            elif obj_type == "multiple":
                objective_ids = json.loads(obj_id)
                for objective_id in objective_ids:
                    objective = get_object_or_404(EmployeeObjective, id=objective_id)
                    form_key_result = KeyResultForm(
                        request.POST, initial={"employee_objective_id": objective}
                    )
                    if form_key_result.is_valid():
                        form = form_key_result.save(commit=False)
                        form.start_value = form.current_value
                        form.employee_id = objective.employee_id
                        form.employee_objective_id = objective
                        form.save()
                    else:
                        return Response(form_key_result.errors, status=status.HTTP_400_BAD_REQUEST)
                return Response({"detail": _("Key results created successfully")}, status=status.HTTP_201_CREATED)

            return Response({"detail": _("Invalid objective type.")}, status=status.HTTP_400_BAD_REQUEST)

        except EmployeeObjective.DoesNotExist:
            return Response({"detail": _("Objective not found.")}, status=status.HTTP_404_NOT_FOUND)
        except json.JSONDecodeError:
            return Response({"detail": _("Invalid objective ID format.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






class KeyResultUpdateView(APIView):
    """
    API view to update key results using HTMX.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to update key results.
        """
        try:
            key_result = EmployeeKeyResult.objects.get(id=id)
            key_result_form = KeyResultForm(request.data, instance=key_result)
            key_result_form.initial["employee_objective_id"] = key_result.employee_objective_id

            if key_result_form.is_valid():
                form = key_result_form.save(commit=False)
                form.employee_id = request.user.employee_get  # Assigning the employee_id
                form.save()
                messages.info(request, _("Key result updated"))
                context = {"key_result_form": KeyResultForm(instance=key_result), "key_result_id": key_result.id}
                response = render(request, "okr/key_result/key_result_update.html", context)
                return HttpResponse(
                    response.content.decode("utf-8") + "<script>location.reload();</script>"
                )
            else:
                context = {"key_result_form": key_result_form, "key_result_id": key_result.id}
                return render(request, "okr/key_result/key_result_update.html", context)

        except EmployeeKeyResult.DoesNotExist:
            return Response({"detail": "Key result not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class FeedbackCreationView(APIView):
    """
    API view to create feedback objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to create feedback objects.
        """
        try:
            form = FeedbackForm(request.data)
            if form.is_valid():
                employees = request.data.getlist("subordinate_id")
                if key_result_ids := request.data.getlist("employee_key_results_id"):
                    for key_result_id in key_result_ids:
                        key_result = EmployeeKeyResult.objects.filter(id=key_result_id).first()
                        feedback_form = form.save()
                        feedback_form.employee_key_results_id.add(key_result)
                instance = form.save()
                instance.subordinate_id.set(employees)

                messages.success(request, _("Feedback created successfully."))
                send_feedback_notifications(request, form=instance)
                return Response({"message": "Feedback created successfully"}, status=201)
            else:
                return Response({"form_errors": form.errors}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class FeedbackUpdateView(APIView):
    """
    API view to update feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to update feedback.
        """
        try:
            feedback = Feedback.objects.get(id=id)
            form = FeedbackForm(request.data, instance=feedback)
            feedback_started = Answer.objects.filter(feedback_id=feedback)

            if feedback_started.exists():
                return Response({"error": "Ongoing feedback is not editable!"}, status=400)

            if form.is_valid():
                employees = request.data.getlist("subordinate_id")
                if key_result_ids := request.data.getlist("employee_key_results_id"):
                    for key_result_id in key_result_ids:
                        key_result = EmployeeKeyResult.objects.filter(id=key_result_id).first()
                        feedback_form = form.save()
                        feedback_form.employee_key_results_id.add(key_result)
                instance = form.save()
                instance.subordinate_id.set(employees)
                send_feedback_notifications(request, instance)
                return Response({"message": "Feedback updated successfully!"}, status=200)
            else:
                return Response({"form_errors": form.errors}, status=400)

        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class FeedbackListSearchView(APIView):
    """
    API view to filter or search feedback objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to filter or search feedback objects.
        """
        try:
            feedback_query = request.GET.get("search", "")
            employee_id = get_object_or_404(Employee, employee_user_id=request.user)
            
            self_feedback = Feedback.objects.filter(employee_id=employee_id, review_cycle__icontains=feedback_query)
            requested_feedback_ids = list(
                Feedback.objects.filter(manager_id=employee_id).values_list('id', flat=True)
            ) + list(
                Feedback.objects.filter(colleague_id=employee_id).values_list('id', flat=True)
            ) + list(
                Feedback.objects.filter(subordinate_id=employee_id).values_list('id', flat=True)
            )

            requested_feedback = Feedback.objects.filter(pk__in=requested_feedback_ids, review_cycle__icontains=feedback_query)
            
            all_feedback = Feedback.objects.none()
            if request.user.has_perm("pms.view_feedback"):
                all_feedback = Feedback.objects.filter(review_cycle__icontains=feedback_query)
            else:
                all_feedback = Feedback.objects.filter(manager_id=employee_id, review_cycle__icontains=feedback_query)

            anonymous_feedback = (
                AnonymousFeedback.objects.filter(employee_id=employee_id)
                if not request.user.has_perm("pms.view_feedback")
                else AnonymousFeedback.objects.all()
            )

            context = filter_pagination_feedback(
                request, self_feedback, requested_feedback, all_feedback, anonymous_feedback
            )

            # Convert context data to JSON
            feedback_data = {
                "self_feedback": list(self_feedback.values()),
                "requested_feedback": list(requested_feedback.values()),
                "all_feedback": list(all_feedback.values()),
                "anonymous_feedback": list(anonymous_feedback.values())
            }

            return Response(feedback_data)

        except Exception as error:
            return Response({"detail": str(error)}, status=500)



from django.db.models import Q

class FeedbackListView(APIView):
    """
    API view to filter or search feedback objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to filter or search feedback objects.
        """
        try:
            user = request.user
            employee = user.employee_get
            feedback_own = Feedback.objects.filter(
                employee_id=employee,
                archive=False,
            )

            feedback_requested = Feedback.objects.filter(
                Q(manager_id=employee) | Q(colleague_id=employee) | Q(subordinate_id=employee)
            ).distinct()

            if user.has_perm("pms.view_feedback"):
                feedback_all = Feedback.objects.filter(archive=False)
            else:
                feedback_all = Feedback.objects.filter(manager_id=employee, archive=False)

            anonymous_feedback = (
                AnonymousFeedback.objects.filter(employee_id=employee, archive=False)
                if not request.user.has_perm("pms.view_feedback")
                else AnonymousFeedback.objects.filter(archive=False)
            )
            anonymous_feedback = anonymous_feedback | AnonymousFeedback.objects.filter(
                anonymous_feedback_id=request.user.id, archive=False
            )

            context = filter_pagination_feedback(
                request, feedback_own, feedback_requested, feedback_all, anonymous_feedback
            )

            # Convert context data to JSON
            feedback_data = {
                "feedback_own": list(feedback_own.values()),
                "feedback_requested": list(feedback_requested.values()),
                "feedback_all": list(feedback_all.values()),
                "anonymous_feedback": list(anonymous_feedback.values())
            }

            return Response(feedback_data)

        except Exception as error:
            return Response({"detail": str(error)}, status=500)






class FeedbackDetailedView(APIView):
    """
    API view to display detailed view of feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id):
        """
        Handles GET requests to display detailed view of feedback.
        """
        try:
            feedback = Feedback.objects.get(id=id)
            is_have_perm = check_permission_feedback_detailed_view(
                request, feedback, "pms.view_feedback"
            )

            if is_have_perm:
                serializer = FeedbackSerializer(feedback)
                feedback_data = serializer.data
                feedback_data['today'] = datetime.datetime.today().date()
                return Response(feedback_data, status=200)
            else:
                return Response({"error": "You don't have permission."}, status=403)
        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class FeedbackDetailedViewAnswer(APIView):
    """
    API view to show answers for feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id, emp_id):
        """
        Handles GET requests to show answers for feedback.
        """
        try:
            employee = get_object_or_404(Employee, id=emp_id)
            feedback = get_object_or_404(Feedback, id=id)
            is_have_perm = check_permission_feedback_detailed_view(
                request, feedback, "pms.view_feedback"
            )

            if is_have_perm:
                answers = Answer.objects.filter(employee_id=employee, feedback_id=feedback)
                kr_feedbacks = KeyResultFeedback.objects.filter(
                    feedback_id=feedback, employee_id=employee
                )
                answers_serializer = AnswerSerializer(answers, many=True)
                kr_feedbacks_serializer = KeyResultFeedbackSerializer(kr_feedbacks, many=True)

                return Response({
                    "answers": answers_serializer.data,
                    "kr_feedbacks": kr_feedbacks_serializer.data,
                }, status=200)
            else:
                return Response({"error": "You don't have permission."}, status=403)
        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found"}, status=404)
        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)






class FeedbackAnswerGet(APIView):
    """
    API view to render the feedback questions.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id):
        """
        Handles GET requests to render the feedback questions.
        """
        try:
            user = request.user
            employee = get_object_or_404(Employee, employee_user_id=user)
            feedback = get_object_or_404(Feedback, id=id)
            answer = Answer.objects.filter(feedback_id=feedback, employee_id=employee)
            question_template = feedback.question_template_id
            questions = question_template.question.all()
            options = QuestionOptions.objects.all()

            feedback_employees = (
                [feedback.employee_id]
                + [feedback.manager_id]
                + list(feedback.colleague_id.all())
                + list(feedback.subordinate_id.all())
            )
            if employee not in feedback_employees:
                return Response({"error": "You are not allowed to answer"}, status=403)

            # Employee does not have an answer object
            has_answer = any(
                Answer.objects.filter(employee_id=emp, feedback_id=feedback).exists()
                for emp in feedback_employees
            )
            if has_answer:
                feedback.status = "Closed"
                feedback.save()

            # Check if the feedback has already been answered
            if answer.exists():
                return Response({"message": "Feedback already answered"}, status=400)

            questions_serializer = QuestionSerializer(questions, many=True)
            options_serializer = QuestionOptionsSerializer(options, many=True)

            context = {
                "questions": questions_serializer.data,
                "options": options_serializer.data,
                "feedback": feedback.id,
            }

            return Response(context, status=200)

        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found"}, status=404)
        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class FeedbackAnswerPost(APIView):
    """
    API view to create feedback answers.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to create feedback answers.
        """
        try:
            user = request.user
            employee = get_object_or_404(Employee, employee_user_id=user)
            feedback = get_object_or_404(Feedback, id=id)
            question_template = feedback.question_template_id
            questions = question_template.question.all()

            if request.method == "POST":
                answered = False  # Flag to check if any answer is provided
                for question in questions:
                    if request.data.get(f"answer{question.id}"):
                        answer = request.data.get(f"answer{question.id}")
                        Answer.objects.get_or_create(
                            answer={"answer": answer},
                            question_id=question,
                            feedback_id=feedback,
                            employee_id=employee,
                        )
                        answered = True
                for key_result in feedback.employee_key_results_id.all():
                    if request.data.get(f"key_result{key_result.id}"):
                        answer = request.data.get(f"key_result{key_result.id}")
                        KeyResultFeedback.objects.get_or_create(
                            answer={"answer": answer},
                            key_result_id=key_result,
                            feedback_id=feedback,
                            employee_id=employee,
                        )
                        answered = True

                if answered:
                    feedback.status = "On Track"
                    feedback.save()
                    messages.success(
                        request,
                        _("Feedback %(review_cycle)s has been answered successfully!.")
                        % {"review_cycle": feedback.review_cycle},
                    )
                    return Response({"message": "Feedback answered successfully"}, status=201)
                else:
                    return Response({"error": "No answers provided"}, status=400)

        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found"}, status=404)
        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class FeedbackAnswerView(APIView):
    """
    API view to view the feedback answers for an employee.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id):
        """
        Handles GET requests to view the feedback answers for an employee.
        """
        try:
            user = request.user
            employee = get_object_or_404(Employee, employee_user_id=user)
            feedback = get_object_or_404(Feedback, id=id)
            answers = Answer.objects.filter(feedback_id=feedback, employee_id=employee)
            key_result_feedback = KeyResultFeedback.objects.filter(
                feedback_id=feedback, employee_id=employee
            )

            if not answers.exists():
                return Response({"message": "Feedback is not answered yet"}, status=400)

            answers_serializer = AnswerSerializer(answers, many=True)
            key_result_feedback_serializer = KeyResultFeedbackSerializer(key_result_feedback, many=True)

            context = {
                "answers": answers_serializer.data,
                "feedback_id": feedback.id,
                "key_result_feedback": key_result_feedback_serializer.data,
            }
            return Response(context, status=200)

        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found"}, status=404)
        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)


class FeedbackDeleteView(APIView):
    """
    API view to delete feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to delete feedback.
        """
        try:
            feedback = get_object_or_404(Feedback, id=id)
            answered = Answer.objects.filter(feedback_id=feedback).exists()

            if feedback.status in ["Closed", "Not Started"] and not answered:
                feedback.delete()
                messages.success(
                    request,
                    _("Feedback %(review_cycle)s deleted successfully!")
                    % {"review_cycle": feedback.review_cycle},
                )
                return Response({"message": "Feedback deleted successfully"}, status=200)
            else:
                messages.warning(
                    request,
                    _("You can't delete feedback %(review_cycle)s with status %(status)s")
                    % {"review_cycle": feedback.review_cycle, "status": feedback.status},
                )
                return Response({"error": "Feedback cannot be deleted due to its status"}, status=400)

        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except ProtectedError:
            return Response({"error": "Related entries exist"}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class FeedbackDetailedViewStatus(APIView):
    """
    API view to update the status of feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to update the status of feedback.
        """
        try:
            status = request.data.get("feedback_status")
            feedback = get_object_or_404(Feedback, id=id)
            answer_exists = Answer.objects.filter(feedback_id=feedback).exists()

            if status == "Not Started" and answer_exists:
                return Response({"warning": "Feedback is already started"}, status=400)

            feedback.status = status
            feedback.save()

            if feedback.status == status:
                return Response({"success": f"Feedback status updated to {status}"}, status=200)
            else:
                return Response({"info": f"Error occurred during status update to {status}"}, status=400)

        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class FeedbackOverviewView(APIView):
    """
    API view to get the feedback overview.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, obj_id):
        """
        Handles GET requests to get the feedback overview.
        """
        try:
            feedback = get_object_or_404(Feedback, id=obj_id)
            has_perm = check_permission_feedback_detailed_view(request, feedback, perm="pms.view_feedback")

            if has_perm:
                question_template = feedback.question_template_id
                questions = question_template.question.all()
                feedback_answers = Answer.objects.filter(feedback_id=feedback)
                kr_feedbacks = KeyResultFeedback.objects.filter(feedback_id=feedback)

                feedback_overview = {}
                for question in questions:
                    answer_list = []
                    for answer in feedback_answers:
                        if answer.question_id == question:
                            answer_list.append(
                                {
                                    answer.employee_id.id: [
                                        answer.answer,
                                        {"type": answer.question_id.question_type},
                                    ]
                                }
                            )
                    feedback_overview[question.id] = answer_list

                for kr_feedback in kr_feedbacks:
                    answer_list = []
                    answer_list.append(
                        {kr_feedback.employee_id.id: [kr_feedback.answer, {"type": "6"}]}
                    )
                    feedback_overview[
                        f"Feedback about keyresult: {kr_feedback.key_result_id.id}"
                    ] = answer_list

                return Response({"feedback_overview": feedback_overview}, status=200)
            else:
                return Response({"error": "You don't have permission."}, status=403)
        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class FeedbackArchiveView(APIView):
    """
    API view to archive or un-archive feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to archive or un-archive feedback.
        """
        try:
            feedback = get_object_or_404(Feedback, id=id)
            if feedback.archive:
                feedback.archive = False
                feedback.save()
                return Response({"message": "Feedback un-archived successfully!"}, status=200)
            else:
                feedback.archive = True
                feedback.save()
                return Response({"message": "Feedback archived successfully!"}, status=200)
        except Feedback.DoesNotExist:
            return Response({"detail": "Feedback not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class GetColleaguesView(APIView):
    """
    API view to get colleagues and subordinates for a manager.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to get colleagues and subordinates for a manager.
        """
        try:
            employee_id = request.GET.get("employee_id")
            if not employee_id:
                return Response({"error": "Employee ID is required"}, status=400)
            
            try:
                employee = Employee.objects.get(id=int(employee_id))
            except Employee.DoesNotExist:
                return Response({"error": "Employee not found"}, status=404)
            
            employees_queryset = []
            reporting_manager = (
                employee.employee_work_info.reporting_manager_id
                if employee.employee_work_info
                else None
            )

            data_type = request.GET.get("data")
            if data_type == "colleagues":
                department = employee.get_department()
                # Employee IDs to exclude from colleague list
                exclude_ids = [employee.id]
                if reporting_manager:
                    exclude_ids.append(reporting_manager.id)

                # Get employees in the same department as the employee
                employees_queryset = (
                    Employee.objects.filter(
                        is_active=True, employee_work_info__department_id=department
                    )
                    .exclude(id__in=exclude_ids)
                    .values_list("id", "employee_first_name")
                )
            elif data_type == "manager":
                if reporting_manager:
                    employees_queryset = Employee.objects.filter(
                        id=reporting_manager.id
                    ).values_list("id", "employee_first_name")
            elif data_type == "subordinates":
                employees_queryset = Employee.objects.filter(
                    is_active=True, employee_work_info__reporting_manager_id=employee
                ).values_list("id", "employee_first_name")
            elif data_type == "keyresults":
                employees_queryset = EmployeeKeyResult.objects.filter(
                    employee_objective_id__employee_id=employee
                ).values_list("id", "key_result_id__title")

            employees = list(employees_queryset)
            return Response({"employees": employees}, status=200)
        except Employee.DoesNotExist:
            return Response({"error": "Invalid Employee ID"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


import logging

# Configure logging
logger = logging.getLogger(__name__)

class FeedbackStatusView(APIView):
    """
    API view to check the feedback status.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to check the feedback status.
        """
        try:
            employee_id = request.data.get("employee_id")
            feedback_id = request.data.get("feedback_id")

            if not employee_id or not feedback_id:
                logger.error("Employee ID or Feedback ID is missing.")
                return Response({"status": "Invalid request"}, status=400)

            try:
                feedback = Feedback.objects.get(id=feedback_id)
            except Feedback.DoesNotExist:
                logger.error(f"Feedback with ID {feedback_id} not found.")
                return Response({"error": "Feedback not found"}, status=404)

            employee = Employee.objects.filter(id=employee_id).first()
            if not employee:
                logger.error(f"Employee with ID {employee_id} not found.")
                return Response({"error": "Employee not found"}, status=404)

            answer_exists = Answer.objects.filter(employee_id=employee, feedback_id=feedback).exists()
            status = "Completed" if answer_exists else "Not-completed"

            logger.info(f"Feedback status for Employee ID {employee_id} and Feedback ID {feedback_id} is {status}.")
            return JsonResponse({"status": status})
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return Response({"error": str(e)}, status=500)





class QuestionCreationAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API endpoint to create a question for a specific question template.
    """
    
    def post(self, request, id):
        """
        Handle POST requests to create a question.
        Args:
            id (int): Primary key of the question template.
        
        Returns:
            JSON response indicating success or failure.
        """
        question_template = get_object_or_404(QuestionTemplate, id=id)
        feedback_ongoing = Feedback.objects.filter(question_template_id=question_template).first()
        
        if feedback_ongoing:
            return Response({"message": "Question template is used in feedback."}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = QuestionSerializer(data=request.data)
        if serializer.is_valid():
            obj_question = serializer.save(template_id=question_template)
            
            if obj_question.question_type == "4":  # Multi-choice question
                option_a = request.data.get("option_a")
                option_b = request.data.get("option_b")
                option_c = request.data.get("option_c")
                option_d = request.data.get("option_d")
                QuestionOptions.objects.create(
                    question_id=obj_question,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                )
            
            return Response({"message": "Question created successfully."}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class QuestionView(APIView):
    """
    API view to view question objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id):
        """
        Handles GET requests to view question objects.
        """
        try:
            question_template = get_object_or_404(QuestionTemplate, id=id)
            questions = Question.objects.filter(template_id=question_template)
            question_types = ["text", "ratings", "boolean", "Multi-choices", "likert"]

            questions_serializer = QuestionSerializer(questions, many=True)
            options_serializer = QuestionOptionsSerializer(
                QuestionOptions.objects.filter(question_id__in=questions), many=True
            )

            context = {
                "question_template": question_template.id,
                "questions": questions_serializer.data,
                "question_options": options_serializer.data,
                "question_types": question_types,
            }
            return Response(context, status=200)
        except QuestionTemplate.DoesNotExist:
            return Response({"error": "Question template not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)


class QuestionUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to update question objects.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, temp_id, q_id):
        """
        Handles POST requests to update question objects.
        """
        try:
            question = get_object_or_404(Question, id=q_id)
            form = QuestionForm(request.data, instance=question)

            if form.is_valid():
                question_type = form.cleaned_data["question_type"]
                if question_type == "4":
                    # if question is Multi-choices
                    option_a = form.cleaned_data["option_a"]
                    option_b = form.cleaned_data["option_b"]
                    option_c = form.cleaned_data["option_c"]
                    option_d = form.cleaned_data["option_d"]
                    options, created = QuestionOptions.objects.get_or_create(
                        question_id=question
                    )
                    options.option_a = option_a
                    options.option_b = option_b
                    options.option_c = option_c
                    options.option_d = option_d
                    options.save()
                    form.save()
                    return Response({"message": "Question updated successfully."}, status=200)
                else:
                    form.save()
                    question_options = QuestionOptions.objects.filter(question_id=question)
                    if question_options.exists():
                        question_options.delete()
                    return Response({"message": "Question updated successfully."}, status=200)
            else:
                return Response({"error": "Error occurred during question update.", "form_errors": form.errors}, status=400)
        except Question.DoesNotExist:
            return Response({"error": "Question not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



from django.db import IntegrityError


class QuestionDeleteView(APIView):
    """
    API view to delete question objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, id):
        """
        Handles DELETE requests to delete question objects.
        """
        try:
            question = get_object_or_404(Question, id=id)
            temp_id = question.template_id.id

            # Delete related question options
            QuestionOptions.objects.filter(question_id=question).delete()
            question.delete()

            return Response({"message": "Question deleted successfully!"}, status=200)

        except IntegrityError:
            return Response({"error": "Failed to delete question: Question template is in use."}, status=400)
        except Question.DoesNotExist:
            return Response({"error": "Question not found."}, status=404)
        except ProtectedError:
            return Response({"error": "Related entries exist"}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class QuestionTemplateCreationView(APIView):
    """
    API view to create question template objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to create question template objects.
        """
        try:
            form = QuestionTemplateForm(request.data)
            if form.is_valid():
                instance = form.save()
                return Response({"message": "Question template created successfully!", "id": instance.id}, status=201)
            else:
                form_errors = "\n".join(
                    [
                        f"{field}: {error}"
                        for field, errors in form.errors.items()
                        for error in errors
                    ]
                )
                messages.error(request, form_errors)
                return Response({"error": "Error occurred during question template creation.", "form_errors": form.errors}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class QuestionTemplateView(APIView):
    """
    API view to view question template objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to view question template objects.
        """
        try:
            question_templates = QuestionTemplate.objects.all()
            serializer = QuestionTemplateSerializer(question_templates, many=True)
            return Response({"question_templates": serializer.data}, status=200)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class QuestionTemplateDetailedView(APIView):
    """
    API view to view detailed question template objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, template_id):
        """
        Handles GET requests to view detailed question template objects.
        """
        try:
            question_template = get_object_or_404(QuestionTemplate, id=template_id)
            questions = Question.objects.filter(template_id=question_template).order_by("-id")
            question_types = ["text", "ratings", "boolean", "multi-choices", "likert"]
            options = QuestionOptions.objects.filter(question_id__in=questions)

            question_template_serializer = QuestionTemplateSerializer(question_template)
            questions_serializer = QuestionSerializer(questions, many=True)
            options_serializer = QuestionOptionsSerializer(options, many=True)

            context = {
                "question_template": question_template_serializer.data,
                "questions": questions_serializer.data,
                "question_options": options_serializer.data,
                "question_types": question_types,
            }
            return Response(context, status=200)
        except QuestionTemplate.DoesNotExist:
            return Response({"error": "Question template not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)



class QuestionTemplateCreationView(APIView):
    """
    API view to create question template objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to create question template objects.
        """
        try:
            form = QuestionTemplateForm(request.data)
            if form.is_valid():
                instance = form.save()
                return Response({"message": "Question template created successfully!", "id": instance.id}, status=201)
            else:
                form_errors = "\n".join(
                    [
                        f"{field}: {error}"
                        for field, errors in form.errors.items()
                        for error in errors
                    ]
                )
                return Response({"error": "Error occurred during question template creation.", "form_errors": form.errors}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class QuestionTemplateUpdateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API endpoint to update a question template using POST.
    """

    def post(self, request, template_id):
        """
        Handle POST requests to update a question template.
        Args:
            template_id (int): Primary key of the question template.

        Returns:
            JSON response indicating success or failure.
        """
        question_template = get_object_or_404(QuestionTemplate, id=template_id)
        serializer = QuestionTemplateSerializer(question_template, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Question template updated successfully."}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class QuestionTemplateDeleteView(APIView):
    """
    API view to delete question template objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, template_id):
        """
        Handles DELETE requests to delete question template objects.
        """
        try:
            question_template = get_object_or_404(QuestionTemplate, id=template_id)
            if Feedback.objects.filter(question_template_id=question_template).exists():
                return Response({"info": "This template is in use in a feedback."}, status=400)
            else:
                question_template.delete()
                return Response({"message": "The question template is deleted successfully!"}, status=200)
        except QuestionTemplate.DoesNotExist:
            return Response({"error": "Question template not found."}, status=404)
        except ProtectedError:
            return Response({"error": "Related entries exist."}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class PeriodView(APIView):
    """
    API view to view period objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to view period objects.
        """
        try:
            periods = Period.objects.all()
            serializer = PeriodSerializer(periods, many=True)
            return Response({"periods": serializer.data}, status=200)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class PeriodCreateView(APIView):
    """
    API view to create period objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to create period objects.
        """
        try:
            form = PeriodForm(request.data)
            if form.is_valid():
                form.save()
                return Response({"message": "Period creation was successful!"}, status=201)
            else:
                form_errors = "\n".join(
                    [
                        f"{field}: {error}"
                        for field, errors in form.errors.items()
                        for error in errors
                    ]
                )
                messages.error(request, form_errors)
                return Response({"error": "Error occurred during period creation.", "form_errors": form.errors}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class PeriodUpdateView(APIView):
    """
    API view to update period objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, period_id):
        """
        Handles POST requests to update period objects.
        """
        try:
            period = get_object_or_404(Period, id=period_id)
            form = PeriodForm(request.data, instance=period)

            if form.is_valid():
                form.save()
                return Response({"message": "Period updated successfully!"}, status=200)
            else:
                form_errors = "\n".join(
                    [
                        f"{field}: {error}"
                        for field, errors in form.errors.items()
                        for error in errors
                    ]
                )
                messages.error(request, form_errors)
                return Response({"error": "Error occurred during period update.", "form_errors": form.errors}, status=400)
        except Period.DoesNotExist:
            return Response({"error": "Period not found"}, status=404)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class PeriodDeleteView(APIView):
    """
    API view to delete period objects.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, period_id):
        """
        Handles DELETE requests to delete period objects.
        """
        try:
            period = get_object_or_404(Period, id=period_id)
            period.delete()
            return Response({"message": "Period deleted successfully."}, status=200)
        except Period.DoesNotExist:
            return Response({"error": "Period not found."}, status=404)
        except ProtectedError:
            return Response({"error": "Related entries exist."}, status=400)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)





class DashboardView(APIView):
    """
    API view to view the dashboard.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to view the dashboard.
        """
        try:
            user = request.user
            employee = Employee.objects.filter(employee_user_id=user).first()
            is_manager = Employee.objects.filter(
                employee_work_info__reporting_manager_id=employee
            ).exists()
            count_key_result = KeyResult.objects.all().count()

            if user.has_perm("pms.view_employeeobjective") and user.has_perm("pms.view_feedback"):
                count_objective = EmployeeObjective.objects.all().count()
                count_feedback = Feedback.objects.all().count()
                okr_at_risk = EmployeeObjective.objects.filter(status="At Risk")
            elif is_manager:
                employees_ids = Employee.objects.filter(
                    employee_work_info__reporting_manager_id=employee
                ).values_list('id', flat=True)
                count_objective = EmployeeObjective.objects.filter(
                    employee_id__in=employees_ids
                ).count()
                count_feedback = Feedback.objects.filter(
                    employee_id__in=employees_ids
                ).count()
                okr_at_risk = EmployeeObjective.objects.filter(
                    employee_id__in=employees_ids
                ).filter(status="At Risk")
            else:
                count_objective = EmployeeObjective.objects.filter(
                    employee_id=employee
                ).count()
                count_key_result = EmployeeKeyResult.objects.filter(
                    employee_objective_id__employee_id=employee
                ).count()
                count_feedback = Feedback.objects.filter(employee_id=employee).count()
                okr_at_risk = EmployeeObjective.objects.filter(
                    employee_id=employee
                ).filter(status="At Risk")

            context = {
                "count_objective": count_objective,
                "count_key_result": count_key_result,
                "count_feedback": count_feedback,
                "okr_at_risk": okr_at_risk,
            }
            return Response(context, status=200)
        except Exception as error:
            return Response({"detail": str(error)}, status=500)




class ObjectiveBulkArchiveView(APIView):
    """
    API view to bulk archive/un-archive objectives.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to archive/un-archive bulk objectives.
        """
        try:
            ids = json.loads(request.POST.get("ids", "[]"))
            is_active = False
            message = _("un-archived")
            if request.GET.get("is_active") == "False":
                is_active = True
                message = _("archived")
                
            for objective_id in ids:
                objective_obj = EmployeeObjective.objects.get(id=objective_id)
                objective_obj.archive = is_active
                objective_obj.save()
                success_message = _("{objective} is {message}").format(
                    objective=objective_obj, message=message
                )
                messages.success(request, success_message)

            return JsonResponse({"message": "Success"})
        except EmployeeObjective.DoesNotExist:
            return JsonResponse({"error": "One or more objectives not found."}, status=404)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)





class ObjectiveBulkDeleteView(APIView):
    """
    API view to bulk delete objectives.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to bulk delete objectives.
        """
        try:
            ids = json.loads(request.POST.get("ids", "[]"))
            for objective_id in ids:
                try:
                    objective = EmployeeObjective.objects.get(id=objective_id)
                    if objective.status in ["Not Started", "Closed"]:
                        objective.delete()
                        messages.success(
                            request,
                            _("%(employee)s's %(objective)s deleted")
                            % {
                                "objective": objective.objective,
                                "employee": objective.employee_id,
                            },
                        )
                    else:
                        messages.warning(
                            request,
                            _("You can't delete objective %(objective)s with status %(status)s")
                            % {
                                "objective": objective.objective,
                                "status": objective.status,
                            },
                        )
                except EmployeeObjective.DoesNotExist:
                    messages.error(request, _("Objective not found."))

            return JsonResponse({"message": "Success"})
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)





class FeedbackBulkArchiveView(APIView):
    """
    API view to archive/un-archive bulk feedbacks.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to archive/un-archive bulk feedbacks.
        """
        try:
            ids = json.loads(request.POST.get("ids", "[]"))
            announy_ids = json.loads(request.POST.get("announy_ids", "[]"))
            is_active = False
            message = _("un-archived")
            if request.GET.get("is_active") == "False":
                is_active = True
                message = _("archived")

            for feedback_id in ids:
                feedback = Feedback.objects.get(id=feedback_id)
                feedback.archive = is_active
                feedback.save()
                success_message = _("{feedback} is {message}").format(
                    feedback=feedback, message=message
                )
                messages.success(request, success_message)

            for feedback_id in announy_ids:
                feedback = AnonymousFeedback.objects.get(id=feedback_id)
                feedback.archive = is_active
                feedback.save()
                success_message = _("{feedback} is {message}").format(
                    feedback=feedback.feedback_subject, message=message
                )
                messages.success(request, success_message)

            return JsonResponse({"message": "Success"})
        except Feedback.DoesNotExist:
            return JsonResponse({"error": "One or more feedbacks not found."}, status=404)
        except AnonymousFeedback.DoesNotExist:
            return JsonResponse({"error": "One or more anonymous feedbacks not found."}, status=404)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)





class FeedbackBulkDeleteView(APIView):
    """
    API view to bulk delete feedbacks.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to bulk delete feedbacks.
        """
        try:
            ids = json.loads(request.POST.get("ids", "[]"))
            for feedback_id in ids:
                try:
                    feedback = Feedback.objects.get(id=feedback_id)
                    if feedback.status in ["Closed", "Not Started"]:
                        feedback.delete()
                        messages.success(
                            request,
                            _("Feedback %(review_cycle)s deleted successfully!")
                            % {"review_cycle": feedback.review_cycle},
                        )
                    else:
                        messages.warning(
                            request,
                            _("You can't delete feedback %(review_cycle)s with status %(status)s")
                            % {"review_cycle": feedback.review_cycle, "status": feedback.status},
                        )
                except Feedback.DoesNotExist:
                    messages.error(request, _("Feedback not found."))

            return JsonResponse({"message": "Success"})
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)





class ObjectiveSelectView(APIView):
    """
    API view to return all the IDs of the employees to select the employee row.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to return all the IDs of the employees to select the employee row.
        """
        try:
            page_number = request.GET.get("page")
            table = request.GET.get("tableName")
            user = request.user.employee_get
            employees = EmployeeObjective.objects.filter(employee_id=user, archive=False)

            if page_number == "all":
                if table == "all":
                    if request.user.has_perm("pms.view_employeeobjective"):
                        employees = EmployeeObjective.objects.filter(archive=False)
                    else:
                        employees = EmployeeObjective.objects.filter(
                            employee_id__employee_user_id=request.user
                        ) | EmployeeObjective.objects.filter(
                            employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                        )
                else:
                    employees = EmployeeObjective.objects.filter(
                        employee_id=user, archive=False
                    )

            employee_ids = [str(emp.id) for emp in employees]
            total_count = employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}
            return JsonResponse(context, safe=False)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)




class ObjectiveSelectFilterView(APIView):
    """
    API view to return all the IDs of the filtered employees.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to return all the IDs of the filtered employees.
        """
        try:
            page_number = request.GET.get("page")
            filtered = request.GET.get("filter")
            filters = json.loads(filtered) if filtered else {}
            table = request.GET.get("tableName")
            user = request.user.employee_get

            employee_filter = ObjectiveFilter(filters, queryset=EmployeeObjective.objects.all())
            if page_number == "all":
                if table == "all":
                    if request.user.has_perm("pms.view_employeeobjective"):
                        employee_filter = ObjectiveFilter(
                            filters, queryset=EmployeeObjective.objects.all()
                        )
                    else:
                        employee_filter = ObjectiveFilter(
                            filters,
                            queryset=EmployeeObjective.objects.filter(
                                employee_id__employee_work_info__reporting_manager_id__employee_user_id=request.user
                            ),
                        )
                else:
                    employee_filter = ObjectiveFilter(
                        filters, queryset=EmployeeObjective.objects.filter(employee_id=user)
                    )
            # Get the filtered queryset
            filtered_employees = employee_filter.qs

            employee_ids = [str(emp.id) for emp in filtered_employees]
            total_count = filtered_employees.count()

            context = {"employee_ids": employee_ids, "total_count": total_count}

            return JsonResponse(context)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)


from notifications.signals import notify
from django.urls import reverse

class AnonymousFeedbackAddView(APIView):
    """
    API view for adding anonymous feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to add anonymous feedback.
        """
        try:
            form = AnonymousFeedbackForm(request.data)
            anonymous_id = request.user.id

            if form.is_valid():
                feedback = form.save(commit=False)
                feedback.anonymous_feedback_id = anonymous_id
                feedback.save()
                if feedback.based_on == "employee":
                    try:
                        notify.send(
                            User.objects.filter(username="Horilla Bot").first(),
                            recipient=feedback.employee_id.employee_user_id,
                            verb="You received an anonymous feedback!",
                            verb_ar="لقد تلقيت تقييمًا مجهولًا!",
                            verb_de="Sie haben anonymes Feedback erhalten!",
                            verb_es="¡Has recibido un comentario anónimo!",
                            verb_fr="Vous avez reçu un feedback anonyme!",
                            redirect=reverse("feedback-view"),
                            icon="bag-check",
                        )
                    except Exception as e:
                        pass
                return HttpResponse("<script>window.location.reload();</script>")
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)

    def get(self, request):
        """
        Handles GET requests to render the feedback form.
        """
        form = AnonymousFeedbackForm()
        context = {"form": form, "create": True}
        return render(request, "anonymous/anonymous_feedback_form.html", context)



class EditAnonymousFeedbackView(APIView):
    """
    API view for editing anonymous feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id):
        """
        Handles POST requests to edit anonymous feedback.
        """
        try:
            feedback = AnonymousFeedback.objects.get(id=obj_id)
            form = AnonymousFeedbackForm(request.data, instance=feedback)
            anonymous_id = request.user.id

            if form.is_valid():
                feedback = form.save(commit=False)
                feedback.anonymous_feedback_id = anonymous_id
                feedback.save()
                return HttpResponse("<script>window.location.reload();</script>")
            else:
                return Response({"error": form.errors}, status=400)
        except AnonymousFeedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)

    def get(self, request, obj_id):
        """
        Handles GET requests to render the feedback form pre-filled with existing data.
        """
        try:
            feedback = AnonymousFeedback.objects.get(id=obj_id)
            form = AnonymousFeedbackForm(instance=feedback)
            context = {"form": form, "create": False}
            return render(request, "anonymous/anonymous_feedback_form.html", context)
        except AnonymousFeedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



class ArchiveAnonymousFeedbackView(APIView):
    """
    API view to archive/un-archive anonymous feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, obj_id):
        """
        Handles POST requests to archive/un-archive anonymous feedback.
        """
        try:
            feedback = get_object_or_404(AnonymousFeedback, id=obj_id)
            if feedback.archive:
                feedback.archive = False
                messages.info(request, _("Feedback un-archived successfully!"))
            else:
                feedback.archive = True
                messages.info(request, _("Feedback archived successfully!"))
            
            feedback.save()
            return Response({"message": "Success"}, status=200)
        except AnonymousFeedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class DeleteAnonymousFeedbackView(APIView):
    """
    API view to delete anonymous feedback.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, obj_id):
        """
        Handles DELETE requests to delete anonymous feedback.
        """
        try:
            feedback = get_object_or_404(AnonymousFeedback, id=obj_id)
            feedback.delete()
            messages.success(request, _("Feedback deleted successfully!"))
            return Response({"message": "Feedback deleted successfully!"}, status=200)

        except IntegrityError:
            messages.error(request, _("Failed to delete feedback: Feedback template is in use."))
            return Response({"error": "Failed to delete feedback: Feedback template is in use."}, status=400)

        except AnonymousFeedback.DoesNotExist:
            messages.error(request, _("Feedback not found."))
            return Response({"error": "Feedback not found."}, status=404)

        except ProtectedError:
            messages.error(request, _("Related entries exists"))
            return Response({"error": "Related entries exist."}, status=400)

        except Exception as error:
            messages.error(request, str(error))
            return Response({"error": str(error)}, status=500)




class ViewSingleAnonymousFeedbackView(APIView):
    """
    API view to display a single anonymous feedback entry.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, obj_id):
        """
        Handles GET requests to display a single anonymous feedback entry.
        """
        try:
            feedback = get_object_or_404(AnonymousFeedback, id=obj_id)
            return render(request, "anonymous/single_view.html", {"feedback": feedback})
        except AnonymousFeedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class EmployeeKeyResultCreationView(APIView):
    """
    API view for employee key result creation, returns a key result form.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, emp_obj_id):
  
        try:
            emp_objective = get_object_or_404(EmployeeObjective, id=emp_obj_id)
            
            if not hasattr(emp_objective, 'employee_id') or emp_objective.employee_id is None:
                return Response({"error": "Employee ID is not associated with this objective."}, status=status.HTTP_400_BAD_REQUEST)

            emp_key_result_form = EmployeeKeyResultForm(request.data)

            if emp_key_result_form.is_valid():
                emp_key_result = emp_key_result_form.save()
                emp_objective.update_objective_progress()
                key_result = emp_key_result.key_result_id
                emp_objective.key_result_id.add(key_result)

                employee = emp_objective.employee_id
                if not hasattr(employee, 'employee_user_id') or employee.employee_user_id is None:
                    return Response({"error": "Employee user ID is not available."}, status=status.HTTP_400_BAD_REQUEST)

                notify.send(
                    request.user.employee_get,
                    recipient=employee.employee_user_id,
                    verb="You got a Key Result!",
                    verb_ar="\u0644\u0642\u062f \u062d\u0635\u0644\u062a \u0639\u0644\u0649 \u0646\u062a\u064a\u062c\u0629 \u0631\u0626\u064a\u0633\u064a\u0629!",
                    verb_de="Du hast ein Schlüsselergebnis erreicht!",
                    verb_es="¡Has conseguido un Resultado Clave!",
                    verb_fr="Vous avez obtenu un Résultat Clé!",
                    redirect=reverse(
                        "objective-detailed-view",
                        kwargs={"obj_id": emp_objective.objective_id.id},
                    ),
                )

                return Response(
                    {"message": "Key result assigned successfully."}, status=status.HTTP_201_CREATED
                )

            return Response(emp_key_result_form.errors, status=status.HTTP_400_BAD_REQUEST)
        except EmployeeObjective.DoesNotExist:
            return Response({"error": "EmployeeObjective not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class EmployeeKeyResultUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view for updating employee key result, returns a key result form.
    """
    permission_classes = [IsAuthenticated]


    def post(self, request, kr_id):
        """
        Handles POST requests to update employee key result.
        """
        try:
            emp_kr = get_object_or_404(EmployeeKeyResult, id=kr_id)
            employee = emp_kr.employee_objective_id.employee_id
            emp_key_result = EmployeeKeyResultForm(request.data, instance=emp_kr)
            
            if emp_key_result.is_valid():
                emp_key_result.save()
                emp_kr.employee_objective_id.update_objective_progress()
                messages.success(request, _("Key result updated successfully."))

                notify.send(
                    request.user.employee_get,
                    recipient=employee.employee_user_id,
                    verb="Your Key Result updated.",
                    verb_ar="تم تحديث نتيجتك الرئيسية.",
                    verb_de="Ihr Schlüsselergebnis wurde aktualisiert.",
                    verb_es="Se ha actualizado su Resultado Clave.",
                    verb_fr="Votre Résultat Clé a été mis à jour.",
                    redirect=reverse(
                        "objective-detailed-view",
                        kwargs={"obj_id": emp_kr.employee_objective_id.objective_id.id},
                    ),
                )
                return HttpResponse("<script>window.location.reload()</script>")
            else:
                return Response({"error": emp_key_result.errors}, status=400)
        except EmployeeKeyResult.DoesNotExist:
            return Response({"error": "Employee key result not found."}, status=404)
        except KeyError as ke:
            return Response({"error": f"Missing key in the request data: {str(ke)}"}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



from django.shortcuts import get_object_or_404, redirect



class DeleteEmployeeKeyResultView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to delete employee key result.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, kr_id):
        """
        Handles DELETE requests to delete employee key result.
        """
        try:
            emp_kr = get_object_or_404(EmployeeKeyResult, id=kr_id)
            emp_objective = emp_kr.employee_objective_id
            emp_kr.delete()
            emp_objective.update_objective_progress()
            messages.success(request, _("Objective deleted successfully!"))

            return Response({"message": "Objective deleted successfully!"}, status=200)
        except EmployeeKeyResult.DoesNotExist:
            return Response({"error": "Employee key result not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)







class EmployeeKeyResultUpdateStatusView(APIView):
    """
    API view to update the status of an employee key result.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, kr_id):
        """
        Handles POST requests to update the status of an employee key result.
        """
        try:
            emp_kr = get_object_or_404(EmployeeKeyResult, id=kr_id)
            status = request.POST.get("key_result_status")

            if not status:
                return Response({"error": "Key result status is required."}, status=400)

            emp_kr.status = status
            emp_kr.save()
            messages.success(request, _("Key result status changed to {}.").format(status))

            return Response({"message": "Key result status changed successfully!", "status": status}, status=200)
        except EmployeeKeyResult.DoesNotExist:
            return Response({"error": "Employee key result not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



class KeyResultCurrentValueUpdateView(APIView):
    """
    API view to update the current value of a key result.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        """
        Handles POST requests to update the current value of a key result.
        """
        try:
            current_value = request.POST.get("current_value")
            emp_kr_id = request.POST.get("emp_key_result_id")

            if current_value is None or emp_kr_id is None:
                return JsonResponse({"type": "error", "message": "Current value and key result ID are required."}, status=400)

            try:
                current_value = float(current_value)
                emp_kr_id = int(emp_kr_id)
            except ValueError:
                return JsonResponse({"type": "error", "message": "Invalid data format for current value or key result ID."}, status=400)

            emp_kr = EmployeeKeyResult.objects.get(id=emp_kr_id)

            if current_value <= emp_kr.target_value:
                emp_kr.current_value = current_value
                emp_kr.save()
                emp_kr.employee_objective_id.update_objective_progress()
                return JsonResponse({"type": "success", "message": "Key result current value updated successfully."}, status=200)
            else:
                return JsonResponse({"type": "error", "message": "Current value exceeds the target value."}, status=400)
        except EmployeeKeyResult.DoesNotExist:
            return JsonResponse({"type": "error", "message": "Key result not found."}, status=404)
        except Exception as error:
            return JsonResponse({"type": "error", "message": str(error)}, status=500)





class KeyResultDataView(APIView):
    """
    API view to get the data of key result and return to the form.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Get key result data for form fields.
        """
        try:
            key_id = request.GET.get("key_result_id")
            if not key_id:
                return Response({"error": "Key result ID is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            key_result = KeyResult.objects.filter(id=key_id).first()
            data_update_type = request.GET.get("data-update")
            
            if key_result:
                if data_update_type == "target_value":
                    return Response(
                        {"target_value": key_result.target_value}, 
                        status=status.HTTP_200_OK
                    )
                elif data_update_type == "end_date":
                    start_date_str = request.GET.get("start_date")
                    if start_date_str:
                        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
                        end_date = (start_date + relativedelta(days=key_result.duration)).date()
                        return Response(
                            {"end_date": end_date.strftime("%Y-%m-%d")}, 
                            status=status.HTTP_200_OK
                        )
                    else:
                        return Response({"error": "Start date is required for end date calculation."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                empty_response = {"target_value": ""} if data_update_type == "target_value" else {"end_date": ""}
                return Response(empty_response, status=status.HTTP_200_OK)
        
        except KeyResult.DoesNotExist:
            return Response({"error": "Key result not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as ve:
            return Response({"error": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class ViewMeetingsView(APIView):
    """
    API view to view the meetings.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to view the meetings.
        """
        try:
            previous_data = request.GET.urlencode()
            meetings = Meetings.objects.filter(is_active=True)

            if not request.user.has_perm("pms.view_meetings"):
                employee_id = request.user.employee_get
                meetings = meetings.filter(
                    Q(employee_id=employee_id) | Q(manager=employee_id)
                ).distinct()

            meetings = meetings.order_by("-id")
            filter_form = MeetingsFilter()
            meetings = paginator_qry(meetings, request.GET.get("page"))
            requests_ids = json.dumps([instance.id for instance in meetings.object_list])
            data_dict = parse_qs(previous_data)
            get_key_instances(Meetings, data_dict)
            all_meetings = Meetings.objects.all()

            context = {
                "all_meetings": all_meetings,
                "meetings": list(meetings.object_list.values()),  # Convert queryset to list of dictionaries
                "filter_form": filter_form.form,
                "requests_ids": requests_ids,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class ViewMeetingsView(APIView):
    """
    API view to view the meetings.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to view the meetings.
        """
        try:
            previous_data = request.GET.urlencode()
            meetings = Meetings.objects.filter(is_active=True)

            if not request.user.has_perm("pms.view_meetings"):
                employee_id = request.user.employee_get
                meetings = meetings.filter(
                    Q(employee_id=employee_id) | Q(manager=employee_id)
                ).distinct()

            meetings = meetings.order_by("-id")
            filter_form = MeetingsFilter()
            meetings = paginator_qry(meetings, request.GET.get("page"))
            requests_ids = json.dumps([instance.id for instance in meetings.object_list])
            data_dict = parse_qs(previous_data)
            get_key_instances(Meetings, data_dict)
            all_meetings = Meetings.objects.all()

            # Serialize meetings data using MeetingsSerializer
            meetings_serializer = MeetingsSerializer(meetings.object_list, many=True)
            all_meetings_serializer = MeetingsSerializer(all_meetings, many=True)

            # Get cleaned data from the filter form
            filter_form_data = filter_form.form.cleaned_data if filter_form.is_valid() else {}

            context = {
                "all_meetings": all_meetings_serializer.data,
                "meetings": meetings_serializer.data,
                "filter_form": filter_form_data,
                "requests_ids": requests_ids,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class CreateMeetingsView(APIView):
    """
    API view to create a meeting.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    
    def post(self, request):
        """
        Handles POST requests to create a meeting.
        """
        try:
            instance_id = request.GET.get("instance_id")
            instance = None
            if instance_id and instance_id.isdigit():
                instance = Meetings.objects.filter(id=int(instance_id)).first()
            form = MeetingsForm(request.POST, instance=instance)
            if form.is_valid():
                instance = form.save()
                managers = [manager.employee_user_id for manager in form.cleaned_data["manager"]]
                answer_employees = [answer_emp.employee_user_id for answer_emp in form.cleaned_data["answer_employees"]]
                employees = form.cleaned_data["employee_id"]
                employees = [employee.employee_user_id for employee in employees.exclude(id__in=form.cleaned_data["answer_employees"])]

                try:
                    notify.send(
                        request.user.employee_get,
                        recipient=answer_employees,
                        verb=f"You have been added as an answerable employee for the meeting {instance.title}",
                        verb_ar=f"لقد تمت إضافتك كموظف مسؤول عن الاجتماع {instance.title}",
                        verb_de=f"Du wurden als Mitarbeiter zum Ausfüllen für das {instance.title}-Meeting hinzugefügt",
                        verb_es=f"Se le ha agregado como empleado responsable de la reunión {instance.title}",
                        verb_fr=f"Vous avez été ajouté en tant que employé responsable pour la réunion {instance.title}",
                        icon="information",
                        redirect=reverse("view-meetings") + f"?search={instance.title}",
                    )
                except Exception:
                    pass

                try:
                    notify.send(
                        request.user.employee_get,
                        recipient=employees,
                        verb=f"You have been added to the meeting {instance.title}",
                        verb_ar=f"لقد تمت إضافتك إلى اجتماع {instance.title}.",
                        verb_de=f"Sie wurden zur {instance.title} Besprechung hinzugefügt",
                        verb_es=f"Te han agregado a la reunión {instance.title}",
                        verb_fr=f"Vous avez été ajouté à la réunion {instance.title}",
                        icon="information",
                        redirect=reverse("view-meetings") + f"?search={instance.title}",
                    )
                except Exception:
                    pass

                try:
                    notify.send(
                        request.user.employee_get,
                        recipient=managers,
                        verb=f"You have been added as a manager for the meeting {instance.title}",
                        verb_ar=f"لقد تمت إضافتك كمدير للاجتماع {instance.title}",
                        verb_de=f"Sie wurden als Manager für das Meeting {instance.title} hinzugefügt",
                        verb_es=f"Se le ha agregado como administrador de la reunión {instance.title}",
                        verb_fr=f"Vous avez été ajouté en tant que responsable de réunion {instance.title}",
                        icon="information",
                        redirect=reverse("view-meetings") + f"?search={instance.title}",
                    )
                except Exception:
                    pass

                messages.success(request, _("Meeting added successfully"))
                return HttpResponse("<script>window.location.reload()</script>")
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



class ArchiveMeetingsView(APIView):
    """
    API view to archive and unarchive meetings.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to archive and unarchive meetings.
        """
        try:
            meeting = Meetings.objects.filter(id=id).first()
            if not meeting:
                return Response({"error": "Meeting not found."}, status=404)

            meeting.is_active = not meeting.is_active
            meeting.save()
            return Response({"message": "Meeting status changed successfully!"}, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



class MeetingManagerRemoveView(APIView):
    """
    API view to remove the manager from the meeting.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, meet_id, manager_id):
        """
        Handles DELETE requests to remove the manager from the meeting.
        """
        try:
            meeting = get_object_or_404(Meetings, id=meet_id)
            manager = get_object_or_404(meeting.manager, id=manager_id)

            meeting.manager.remove(manager)
            meeting.save()

            return Response({"message": "Manager removed from the meeting successfully!"}, status=200)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)


class MeetingEmployeeRemoveView(APIView):
    """
    API view to remove employees from the meeting.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, meet_id, employee_id):
        """
        Handles DELETE requests to remove employees from the meeting.
        """
        try:
            meeting = get_object_or_404(Meetings, id=meet_id)
            employee = get_object_or_404(Employee, id=employee_id)

            meeting.employee_id.remove(employee)
            meeting.save()

            return Response({"message": "Employee removed from the meeting successfully!"}, status=200)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class FilterMeetingsView(APIView):
    """
    API view to filter meetings.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to filter meetings.
        """
        try:
            previous_data = request.GET.urlencode()
            filter_obj = MeetingsFilter(request.GET).qs

            if not request.user.has_perm("pms.view_meetings"):
                employee_id = request.user.employee_get
                filter_obj = filter_obj.filter(
                    Q(employee_id=employee_id) | Q(manager=employee_id)
                ).distinct()
            filter_obj = filter_obj.order_by("-id")

            filter_obj = sortby(request, filter_obj, "sortby")
            filter_obj = paginator_qry(filter_obj, request.GET.get("page"))
            requests_ids = json.dumps([instance.id for instance in filter_obj.object_list])

            data_dict = parse_qs(previous_data)
            get_key_instances(EmployeeObjective, data_dict)

            context = {
                "meetings": list(filter_obj.object_list.values()),
                "pd": previous_data,
                "filter_dict": data_dict,
                "requests_ids": requests_ids,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class AddResponseView(APIView):
    """
    API view to add the Minutes of the Meeting (MoM) to a meeting.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to add the Minutes of the Meeting (MoM) to a meeting.
        """
        try:
            meeting = get_object_or_404(Meetings, id=id)
            response = request.POST.get("response")

            if response:
                meeting.response = response
                meeting.save()
                return Response({"message": "Response added to the meeting successfully!"}, status=200)
            else:
                return Response({"error": "Response content is required."}, status=400)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class MeetingAnswerGetView(APIView):
    """
    API view to render the Meeting questions.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id, **kwargs):
        """
        Handles GET requests to render the Meeting questions.
        """
        try:
            employee = request.user.employee_get
            if employee_id := request.GET.get("emp_id"):
                employee = get_object_or_404(Employee, id=employee_id)

            meeting = get_object_or_404(Meetings, id=id)

            if not meeting.question_template:
                return Response({"error": "Meeting does not have a question template."}, status=400)

            answer = MeetingsAnswer.objects.filter(meeting_id=meeting, employee_id=employee)
            questions = meeting.question_template.question.all()
            options = QuestionOptions.objects.all()
            meeting_employees = meeting.manager.all() | meeting.employee_id.all()

            if answer or request.GET.get("emp_id"):
                return redirect("meeting-answer-view", id=meeting.id, emp_id=employee.id)

            if employee not in meeting_employees:
                messages.info(request, _("You are not allowed to answer"))
                return redirect("view_meetings")

            context = {
                "questions": list(questions.values()),
                "options": list(options.values()),
                "meeting": {
                    "id": meeting.id,
                    "title": meeting.title,
                    "date": meeting.date,
                }
            }

            return Response(context, status=200)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



class MeetingAnswerPostView(APIView):
    """
    API view to create meeting answers.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, id):
        """
        Handles POST requests to create meeting answers.
        """
        try:
            employee = request.user.employee_get
            meeting = get_object_or_404(Meetings, id=id)

            if not meeting.question_template:
                return Response({"error": "Meeting does not have a question template."}, status=400)

            question_template = meeting.question_template.question.all()

            for question in question_template:
                answer = request.POST.get(f"answer{question.id}")
                if answer:
                    MeetingsAnswer.objects.get_or_create(
                        question_id=question,
                        meeting_id=meeting,
                        employee_id=employee,
                        defaults={"answer": answer},
                    )
            
            messages.success(
                request,
                _("Questions for meeting %(meeting)s have been answered successfully!")
                % {"meeting": meeting.title},
            )
            return Response({"message": "Questions have been answered successfully!"}, status=200)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class MeetingAnswerView(APIView):
    """
    API view to view the meeting answers for an employee.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id, emp_id):
        """
        Handles GET requests to view the meeting answers for an employee.
        """
        try:
            employee = get_object_or_404(Employee, id=emp_id)
            meeting = get_object_or_404(Meetings, id=id)
            answers = MeetingsAnswer.objects.filter(meeting_id=meeting, employee_id=employee)

            context = {
                "answers": list(answers.values()),
                "meeting": {
                    "id": meeting.id,
                    "title": meeting.title,
                    "date": meeting.date,
                }
            }
            
            return Response(context, status=200)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class MeetingQuestionTemplateView(APIView):
    """
    API view to view the activity sidebar page for employees.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, meet_id):
        """
        Handles GET requests to view the activity sidebar page for employees.
        """
        try:
            employee = request.user.employee_get
            meeting = get_object_or_404(Meetings, id=meet_id)
            answer = MeetingsAnswer.objects.filter(meeting_id=meeting, employee_id=employee)
            is_answered = answer.exists()

            context = {
                "is_answered": is_answered,
                "meeting": {
                    "id": meeting.id,
                    "title": meeting.title,
                    "date": meeting.date,
                },
            }

            return Response(context, status=200)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class MeetingSingleView(APIView):
    """
    API view to render a single meeting view.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, id):
        """
        Handles GET requests to render a single meeting view.
        """
        try:
            meeting = get_object_or_404(Meetings, id=id)
            context = {"meeting": {
                "id": meeting.id,
                "title": meeting.title,
                "date": meeting.date,
                "manager": list(meeting.manager.values()),
                "employee_id": list(meeting.employee_id.values()),
                # Add other meeting fields as needed
            }}
            requests_ids_json = request.GET.get("requests_ids")
            if requests_ids_json:
                requests_ids = json.loads(requests_ids_json)
                previous_id, next_id = closest_numbers(requests_ids, id)
                context["requests_ids"] = requests_ids_json
                context["previous"] = previous_id
                context["next"] = next_id
            
            return Response(context, status=200)
        except Meetings.DoesNotExist:
            return Response({"error": "Meeting not found."}, status=404)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




class PerformanceTabView(APIView):
    """
    API view to view the performance tab of an employee.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, emp_id):
        """
        Handles GET requests to view the performance tab of an employee.
        """
        try:
            feedback_own = Feedback.objects.filter(employee_id=emp_id, archive=False)
            today = datetime.datetime.today()

            context = {
                "self_feedback": list(feedback_own.values()),
                "current_date": today.strftime('%Y-%m-%d'),
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class DashboardFeedbackAnswerView(APIView):
    """
    API view to display the feedback answer dashboard.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """
        Handles GET requests to display the feedback answer dashboard.
        """
        try:
            employee = request.user.employee_get
            feedback_requested = Feedback.objects.filter(
                Q(manager_id=employee, manager_id__is_active=True) |
                Q(colleague_id=employee, colleague_id__is_active=True) |
                Q(subordinate_id=employee, subordinate_id__is_active=True)
            ).distinct()
            feedbacks = feedback_requested.exclude(feedback_answer__employee_id=employee)

            context = {
                "feedbacks": list(feedbacks.values()),
                "current_date": datetime.date.today().strftime('%Y-%m-%d'),
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)
