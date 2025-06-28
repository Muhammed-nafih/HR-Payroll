from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from helpdesk.models import TicketType,FAQCategory,FAQ,Ticket,TICKET_STATUS,Attachment,Comment,ClaimRequest,Employee,Department,JobPosition,DepartmentManager
from helpdesk.forms import TicketTypeForm,FAQCategoryForm, FAQForm, CommentForm,AttachmentForm,TicketTagForm,TicketForm,TicketRaisedOnForm,TicketAssigneesForm,DepartmentManagerCreateForm
from django.shortcuts import get_object_or_404
from .serializers import TicketTypeSerializer,FAQCategorySerializer,FAQSerializer,TicketSerializer,AttachmentSerializer,CommentSerializer,ClaimRequestSerializer,CommentEditSerializer,TicketBulkDeleteSerializer
import json
from django.db.models import ProtectedError
from urllib.parse import parse_qs
from base.methods import get_key_instances,filtersubordinates,sortby,is_reportingmanager
from django_filters.rest_framework import DjangoFilterBackend
from helpdesk.filter import FAQCategoryFilter,FAQFilter,TicketFilter,TicketReGroup
from django.db.models import Q
from helpdesk.views import paginator_qry,get_allocated_tickets,get_content_type
from horilla.group_by import group_by_queryset
from datetime import datetime
from base.forms import TagsForm
from helpdesk.methods import is_department_manager
from django.contrib import messages
from django.http import HttpResponse
from base.models import Tags
from employee.authentication import JWTAuthentication
from helpdesk.threading import TicketSendThread,AddAssigneeThread,RemoveAssigneeThread



class TicketTypeCreate(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        data = json.loads(request.body)
        form = TicketTypeForm(data)
        if form.is_valid():
            instance = form.save()
            response_data = {
                "detail": "Ticket type created.",
                "ticket_id": instance.id,
                "title": instance.title,
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)



class TicketTypeUpdate(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, t_type_id):
        data = json.loads(request.body)
        ticket_type = get_object_or_404(TicketType, id=t_type_id)
        form = TicketTypeForm(data, instance=ticket_type)
        if form.is_valid():
            form.save()
            response_data = {
                "detail": "Ticket type updated.",
                "ticket_id": ticket_type.id,
                "title": ticket_type.title,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)




class TicketTypeView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        ticket_types = TicketType.objects.all()
        serializer = TicketTypeSerializer(ticket_types, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class FAQCategoryView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        faq_categories = FAQCategory.objects.all()
        serializer = FAQCategorySerializer(faq_categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class FAQCategoryCreate(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        try:
            form = FAQCategoryForm(request.data)
            if form.is_valid():
                form.save()
                response_data = {
                    "detail": "The FAQ Category created successfully.",
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class FAQCategoryUpdate(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, id):
        try:
            form = FAQCategoryForm(request.data, instance=get_object_or_404(FAQCategory, id=id))
            if form.is_valid():
                form.save()
                response_data = {
                    "detail": "The FAQ category updated successfully.",
                }
                return Response(response_data, status=status.HTTP_200_OK)
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class FAQCategoryDelete(APIView):
    authentication_classes = [JWTAuthentication]
    def delete(self, request, id):
        try:
            faq_category = get_object_or_404(FAQCategory, id=id)
            faq_category.delete()
            response_data = {
                "detail": "The FAQ category has been deleted successfully.",
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ProtectedError:
            return Response({"error": "You cannot delete this FAQ category."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class FAQCategorySearch(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API endpoint for searching and filtering FAQ categories.
    """

    def get(self, request):
        try:
            # Parse query parameters
            previous_data = request.GET.urlencode()
            faq_categories = FAQCategoryFilter(request.GET).qs
            data_dict = parse_qs(previous_data)
            
            # Perform key instance retrieval (assuming it updates data_dict)
            get_key_instances(FAQCategory, data_dict)

            # Serialize the filtered FAQ categories
            serializer = FAQCategorySerializer(faq_categories, many=True)

            response_data = {
                "faq_categories": serializer.data,
                "previous_data": previous_data,
                "filter_dict": data_dict
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            error_message = {
                "error": "An error occurred while processing the request.",
                "details": str(e)
            }
            return Response(error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class FAQView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, cat_id):
        faqs = FAQ.objects.filter(category=cat_id)
        serializer = FAQSerializer(faqs, many=True)
        response_data = {
            "faqs": serializer.data,
            "cat_id": cat_id,
        }
        return Response(response_data, status=status.HTTP_200_OK)




class FAQCreate(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, cat_id):
        try:
            data = request.data.copy()
            data['category'] = cat_id
            form = FAQForm(data)
            if form.is_valid():
                form.save()
                response_data = {
                    "detail": "The FAQ created successfully.",
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class FAQUpdate(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, id):
        try:
            faq = get_object_or_404(FAQ, id=id)
            data = request.data.copy()
            form = FAQForm(data, instance=faq)
            if form.is_valid():
                form.save()
                response_data = {
                    "detail": "The FAQ updated successfully.",
                }
                return Response(response_data, status=status.HTTP_200_OK)
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class FAQSearch(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        query = request.GET.get("search", "")
        category_id = request.GET.get("cat_id", "")
        category = request.GET.get("category", "")
        previous_data = request.GET.urlencode()
        faqs = FAQ.objects.filter(is_active=True)
        data_dict = parse_qs(previous_data)
        
        if query:
            faqs = faqs.filter(Q(question__icontains=query) | Q(answer__icontains=query))
        if category_id:
            faqs = faqs.filter(category_id=category_id)
        if category:
            faqs = faqs.filter(category__name__icontains=category)
        
        serializer = FAQSerializer(faqs, many=True)
        response_data = {
            "faqs": serializer.data,
            "previous_data": previous_data,
            "filter_dict": data_dict,
            "query": query,
        }
        return Response(response_data, status=status.HTTP_200_OK)




class FAQFilterView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, id):
        faqs = FAQ.objects.filter(category=id)
        filtered_faqs = FAQFilter(request.GET, queryset=faqs).qs
        serializer = FAQSerializer(filtered_faqs, many=True)
        previous_data = request.GET.urlencode()
        data_dict = parse_qs(previous_data)
        response_data = {
            "faqs": serializer.data,
            "previous_data": previous_data,
            "filter_dict": data_dict,
        }
        return Response(response_data, status=status.HTTP_200_OK)





class FAQDelete(APIView):
    authentication_classes = [JWTAuthentication]
    def delete(self, request, id):
        try:
            faq = get_object_or_404(FAQ, id=id)
            cat_id = faq.category.id
            faq.delete()
            response_data = {
                "detail": f'The FAQ "{faq}" has been deleted successfully.',
                "category_id": cat_id
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ProtectedError:
            return Response({"error": "You cannot delete this FAQ."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class TicketDelete(APIView):
    authentication_classes = [JWTAuthentication]
    def delete(self, request, ticket_id):
        try:
            ticket = get_object_or_404(Ticket, id=ticket_id)
            if ticket.status == "new":
                # Send mail notification (stub implementation)
                # Replace with actual email sending logic
                # mail_thread = TicketSendThread(request, ticket, type="delete")
                # mail_thread.start()

                employees = ticket.assigned_to.all()
                assignees = [employee.employee_user_id for employee in employees]
                assignees.append(ticket.employee_id.employee_user_id)
                if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                    if ticket.get_raised_on_object().dept_manager.all():
                        manager = (
                            ticket.get_raised_on_object().dept_manager.all().first().manager
                        )
                        assignees.append(manager.employee_user_id)
                # Notify recipients (stub implementation)
                # Replace with actual notification sending logic
                # notify.send(request.user.employee_get, recipient=assignees, verb="The ticket has been deleted.")

                ticket.delete()
                response_data = {
                    "detail": f'The Ticket "{ticket}" has been deleted successfully.',
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'The ticket is not in the "New" status.'}, status=status.HTTP_400_BAD_REQUEST)
        except ProtectedError:
            return Response({"error": "You cannot delete this Ticket."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
class TicketFilterView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        previous_data = request.GET.urlencode()
        tickets = TicketFilter(request.GET, queryset=Ticket.objects.all()).qs
        
        print(f"Filters applied: {request.GET}")
        print(f"Tickets found: {tickets.count()}")

        my_page_number = request.GET.get("my_page")
        all_page_number = request.GET.get("all_page")
        allocated_page_number = request.GET.get("allocated_page")
        
        my_tickets = tickets.filter(employee_id=request.user.employee_get) | tickets.filter(created_by=request.user)
        
        all_tickets = tickets.filter(is_active=True)
        all_tickets = filtersubordinates(request, tickets, "helpdesk.add_tickets")
        
        allocated_tickets = Ticket.objects.none()
        user = request.user.employee_get
        ticket_list = tickets.filter(is_active=True)

        tickets_items1 = tickets_items2 = tickets_items3 = Ticket.objects.none()
        if hasattr(user, "employee_work_info"):
            department = user.employee_work_info.department_id
            job_position = user.employee_work_info.job_position_id
            if department:
                tickets_items1 = ticket_list.filter(raised_on=department.id, assigning_type="department")
            if job_position:
                tickets_items2 = ticket_list.filter(raised_on=job_position.id, assigning_type="job_position")
        
        tickets_items3 = ticket_list.filter(raised_on=user.id, assigning_type="individual")
        allocated_tickets = list(tickets_items1) + list(tickets_items2) + list(tickets_items3)
        
        template = "helpdesk/ticket/ticket_list.html"
        if request.GET.get("view") == "card":
            template = "helpdesk/ticket/ticket_card.html"
        
        if request.GET.get("sortby"):
            all_tickets = sortby(request, all_tickets, "sortby")
            my_tickets = sortby(request, my_tickets, "sortby")
            allocated_tickets = tickets_items1 | tickets_items2 | tickets_items3
            allocated_tickets = sortby(request, allocated_tickets, "sortby")

        field = request.GET.get("field")
        if field != "" and field is not None:
            my_tickets = group_by_queryset(my_tickets, field, request.GET.get("my_page"), "my_page")
            all_tickets = group_by_queryset(all_tickets, field, request.GET.get("all_page"), "all_page")
            tickets_items1 = group_by_queryset(tickets_items1, field, request.GET.get("allocated_page"), "allocated_page")
            tickets_items2 = group_by_queryset(tickets_items2, field, request.GET.get("allocated_page"), "allocated_page")
            tickets_items3 = group_by_queryset(tickets_items3, field, request.GET.get("allocated_page"), "allocated_page")
            template = "helpdesk/ticket/ticket_group.html"
            allocated_tickets = list(tickets_items1) + list(tickets_items2) + list(tickets_items3)
        else:
            my_tickets = paginator_qry(my_tickets, my_page_number)
            all_tickets = paginator_qry(all_tickets, all_page_number)
            allocated_tickets = paginator_qry(allocated_tickets, allocated_page_number)

        data_dict = parse_qs(previous_data)
        get_key_instances(Ticket, data_dict)

        context = {
            "my_tickets": my_tickets,
            "all_tickets": all_tickets,
            "allocated_tickets": allocated_tickets,
            "f": TicketFilter(request.GET),
            "pd": previous_data,
            "ticket_status": TICKET_STATUS,
            "filter_dict": data_dict,
            "field": field,
            "today": datetime.now().date(),
        }

        print(f"Filtered tickets: {allocated_tickets}")
        
        serializer = TicketSerializer(allocated_tickets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class TicketIndividualView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, ticket_id, *args, **kwargs):
        ticket = get_object_or_404(Ticket, id=ticket_id)
        data = {
            "ticket": TicketSerializer(ticket).data,
        }
        return Response(data, status=status.HTTP_200_OK)

 # Custom permission (optional)






class TicketUpdateTagAPI(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API to update the tags of a ticket.
    """

    def post(self, request, *args, **kwargs):
        data = request.data  # POST data instead of GET
        ticket_id = data.get("ticketId")
        
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return Response({"type": "error", "message": _("Ticket not found.")}, status=status.HTTP_404_NOT_FOUND)
        
        # Permissions Check
        if (
            request.user.has_perm("helpdesk.view_ticket")
            or request.user.employee_get == ticket.employee_id
            or is_department_manager(request, ticket)
        ):
            tag_ids = data.get("selectedValues", [])
            ticket.tags.clear()  # Clear existing tags

            for tag_id in tag_ids:
                try:
                    tag = Tags.objects.get(id=tag_id)
                    ticket.tags.add(tag)
                except Tags.DoesNotExist:
                    return Response({"type": "error", "message": _("Tag not found.")}, status=status.HTTP_404_NOT_FOUND)

            response = {
                "type": "success",
                "message": _("The Ticket tag updated successfully."),
            }
            return Response(response, status=status.HTTP_200_OK)

        return Response(
            {"type": "error", "message": _("You don't have permission.")},
            status=status.HTTP_403_FORBIDDEN,
        )



class CreateTagAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to create a tag in the change tag form.
    """
    def post(self, request, format=None):
        data = request.data
        form = TagsForm(data)

        if form.is_valid():
            instance = form.save()
            response = {
                "errors": "no_error",
                "tag_id": instance.id,
                "title": instance.title,
            }
            return Response(response, status=status.HTTP_201_CREATED)

        errors = form.errors.as_json()
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)




class RemoveTagAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to remove a tag from a ticket.
    """
    def post(self, request, format=None):
        data = request.data
        ticket_id = data.get("ticket_id")
        tag_id = data.get("tag_id")
        
        if not ticket_id or not tag_id:
            response = {
                "message": "The ticket_id and tag_id parameters are required.",
                "type": "error"
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.get(id=ticket_id)
            tag = Tags.objects.get(id=tag_id)
            ticket.tags.remove(tag)
            response = {
                "message": _("success"),
                "type": "success"
            }
            return Response(response, status=status.HTTP_200_OK)
        except Ticket.DoesNotExist:
            response = {
                "message": _("The Ticket does not exist."),
                "type": "error"
            }
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Tags.DoesNotExist:
            response = {
                "message": _("The Tag does not exist."),
                "type": "error"
            }
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            response = {
                "message": str(e),
                "type": "error"
            }
            return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CommentCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to create a comment for a ticket.
    """


    def post(self, request, ticket_id, format=None):
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if not request.data:
            return Response({"message": _("No data provided."), "type": "error"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['employee_id'] = request.user.employee_get.id
        data['ticket'] = ticket.id

        c_serializer = CommentSerializer(data=data)

        if c_serializer.is_valid():
            comment = c_serializer.save()

            if 'file' in request.FILES:
                files = request.FILES.getlist('file')
                for file in files:
                    a_serializer = AttachmentSerializer(data={'file': file, 'comment': comment.id, 'ticket': ticket.id})
                    if a_serializer.is_valid():
                        a_serializer.save()
                    else:
                        return Response({"errors": a_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
            response = {
                "message": _("A new comment has been created."),
                "comment_id": comment.id,
                "type": "success"
            }
            return Response(response, status=status.HTTP_201_CREATED)

        return Response({"errors": c_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.exceptions import ValidationError

class CommentEditAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request):
        comment_id = request.data.get("comment_id")
        new_comment = request.data.get("new_comment")

        if not new_comment or len(new_comment) < 2:
            return Response({
                "error": "The comment needs to be at least 2 characters."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            comment = Comment.objects.get(id=comment_id)
            comment.comment = new_comment
            comment.save()
            return Response({
                "message": "The comment updated successfully."
            }, status=status.HTTP_200_OK)
        
        except Comment.DoesNotExist:
            raise ValidationError("Comment not found")





class CommentDeleteAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    """
    API view to delete a comment for a ticket.
    """
    def delete(self, request, comment_id, format=None):
        comment = get_object_or_404(Comment, id=comment_id)
        employee = comment.employee_id

        if not request.user.has_perm("helpdesk.delete_comment") and comment.employee_id.employee_user_id != request.user.id:
            return Response(
                {"message": _("You do not have permission to delete this comment."), "type": "error"},
                status=status.HTTP_403_FORBIDDEN
            )

        comment.delete()
        response = {
            "message": _("{}'s comment has been deleted successfully.").format(employee),
            "type": "success"
        }
        return Response(response, status=status.HTTP_200_OK)



from django.http import JsonResponse


class FAQSuggestionView(APIView):
    """
    API view for providing FAQ suggestions based on filter criteria.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to provide FAQ suggestions based on filter criteria.
        """
        try:
            faqs = FAQFilter(request.GET).qs
            data_list = list(faqs.values())
            response = {
                "faqs": data_list,
            }
            return JsonResponse(response, status=200)
        except Exception as error:
            return JsonResponse({"error": str(error)}, status=500)






class TicketView(APIView):
    """
    API view for rendering the Ticket view.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to render the Ticket view.
        """
        try:
            tickets = Ticket.objects.filter(is_active=True)
            view = request.GET.get("view") if request.GET.get("view") else "list"
            employee = request.user.employee_get
            previous_data = request.GET.urlencode()
            my_page_number = request.GET.get("my_page")
            all_page_number = request.GET.get("all_page")
            allocated_page_number = request.GET.get("allocated_page")

            my_tickets = tickets.filter(employee_id=employee) | tickets.filter(
                created_by=request.user
            )
            all_tickets = []
            if is_reportingmanager(request) or request.user.has_perm("helpdesk.view_ticket"):
                all_tickets = filtersubordinates(request, tickets, "helpdesk.view_ticket")
            allocated_tickets = []
            ticket_list = tickets.filter(is_active=True)
            user = request.user.employee_get
            if hasattr(user, "employee_work_info"):
                department = user.employee_work_info.department_id
                job_position = user.employee_work_info.job_position_id
                if department:
                    tickets_items = ticket_list.filter(
                        raised_on=department.id, assigning_type="department"
                    )
                    allocated_tickets += tickets_items
                if job_position:
                    tickets_items = ticket_list.filter(
                        raised_on=job_position.id, assigning_type="job_position"
                    )
                    allocated_tickets += tickets_items

            tickets_items = ticket_list.filter(raised_on=user.id, assigning_type="individual")
            allocated_tickets += tickets_items

            data_dict = parse_qs(previous_data)
            get_key_instances(Ticket, data_dict)

            context = {
                "my_tickets": TicketSerializer(paginator_qry(my_tickets, my_page_number), many=True).data,
                "all_tickets": TicketSerializer(paginator_qry(all_tickets, all_page_number), many=True).data,
                "allocated_tickets": TicketSerializer(paginator_qry(allocated_tickets, allocated_page_number), many=True).data,
                "f": TicketFilter(request.GET).data,
                "gp_fields": TicketReGroup.fields,
                "ticket_status": TICKET_STATUS,
                "view": view,
                "today": datetime.today().date(),
                "filter_dict": data_dict,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)




from notifications.signals import notify
from django.urls import reverse
from django.utils.translation import gettext as _

class TicketCreateView(APIView):
    """
    API view for creating the Ticket.
    """
    permission_classes = [IsAuthenticated]

    
    
    def post(self, request):
        """
        Handles POST requests to create a new Ticket.
        """
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                ticket = form.save(commit=False)
                
                # Ensure deadline is checked properly
                if ticket.deadline and ticket.deadline < datetime.today().date():
                    return Response({"errors": {"deadline": _("Deadline should be greater than today")}}, status=status.HTTP_400_BAD_REQUEST)
                
                ticket.save()
                form.save_m2m()  # Save many-to-many relationships

                attachments = form.files.getlist("attachment")
                for attachment in attachments:
                    Attachment.objects.create(file=attachment, ticket=ticket)

                mail_thread = TicketSendThread(request, ticket, type="create")
                mail_thread.start()
                messages.success(request, _("The Ticket created successfully."))

                employees = ticket.assigned_to.all()
                assignees = [employee.employee_user_id for employee in employees]
                assignees.append(ticket.employee_id.employee_user_id)

                if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                    if ticket.get_raised_on_object().dept_manager.all():
                        manager = ticket.get_raised_on_object().dept_manager.all().first().manager
                        assignees.append(manager.employee_user_id)

                notify.send(
                    request.user.employee_get,
                    recipient=assignees,
                    verb="You have been assigned to a new Ticket",
                    verb_ar="لقد تم تعيينك لتذكرة جديدة",
                    verb_de="Ihnen wurde ein neues Ticket zugewiesen",
                    verb_es="Se te ha asignado un nuevo ticket",
                    verb_fr="Un nouveau ticket vous a été attribué",
                    icon="infinite",
                    redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
                )
                return Response({"message": _("The Ticket created successfully.")}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"errors": {"non_field_errors": [str(e)]}}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)



class TicketUpdateView(APIView):
    """
    API view for updating the Ticket.
    """
    permission_classes = [IsAuthenticated]

   
    def post(self, request, ticket_id):
        """
        Handles POST requests to update the Ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if (
            request.user.has_perm("helpdesk.change_ticket")
            or is_department_manager(request, ticket)
            or request.user.employee_get == ticket.employee_id
            or request.user.employee_get in ticket.assigned_to.all()
        ):
            form = TicketForm(request.POST, request.FILES, instance=ticket)
            if form.is_valid():
                try:
                    ticket = form.save()
                    attachments = request.FILES.getlist("attachment")
                    for attachment in attachments:
                        Attachment.objects.create(file=attachment, ticket=ticket)
                    messages.success(request, _("The Ticket updated successfully."))
                    return Response({"message": _("The Ticket updated successfully.")}, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response({"errors": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            messages.info(request, _("You don't have permission."))
            return Response({"message": "You don't have permission."}, status=status.HTTP_403_FORBIDDEN)




class TicketArchiveView(APIView):
    """
    API view for archiving the Ticket.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        """
        Handles POST requests to archive the Ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)

        if (
            request.user.has_perm("helpdesk.delete_ticket")
            or ticket.employee_id == request.user.employee_get
            or is_department_manager(request, ticket)
        ):
            # Toggle the ticket's active state
            ticket.is_active = not ticket.is_active
            ticket.save()

            if ticket.is_active:
                messages.success(request, _("The Ticket un-archived successfully."))
            else:
                messages.success(request, _("The Ticket archived successfully."))

            return Response({"message": _("Ticket status updated successfully.")}, status=200)
        else:
            messages.info(request, _("You don't have permission."))
            return Response({"message": _("You don't have permission.")}, status=403)



from django.utils import timezone


class ChangeTicketStatusView(APIView):
    """
    API view for changing the Ticket status.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        """
        Handles POST requests to change the Ticket status.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        pre_status = ticket.get_status_display()
        status = request.POST.get("status")
        
        if status is None:
            return Response({"errors": _("Status is required.")}, status=400)

        user = request.user.employee_get
        
        if ticket.status != status:
            if (
                user == ticket.employee_id
                or user in ticket.assigned_to.all()
                or request.user.has_perm("helpdesk.change_ticket")
            ):
                try:
                    ticket.status = status
                    if ticket.status == "resolved":
                        ticket.resolved_date = timezone.now()
                    ticket.save()
                    
                    time = timezone.now().strftime("%b. %d, %Y, %I:%M %p")
                    response = {
                        "type": "success",
                        "message": _("The Ticket status updated successfully."),
                        "user": user.get_full_name(),
                        "pre_status": pre_status,
                        "cur_status": ticket.get_status_display(),
                        "time": time,
                    }

                    employees = ticket.assigned_to.all()
                    assignees = [employee.employee_user_id for employee in employees]
                    assignees.append(ticket.employee_id.employee_user_id)
                    
                    if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                        if ticket.get_raised_on_object().dept_manager.all():
                            manager = ticket.get_raised_on_object().dept_manager.all().first().manager
                            assignees.append(manager.employee_user_id)
                    
                    notify.send(
                        request.user.employee_get,
                        recipient=assignees,
                        verb=f"The status of the ticket has been changed to {ticket.get_status_display()}.",
                        verb_ar="تم تغيير حالة التذكرة.",
                        verb_de="Der Status des Tickets wurde geändert.",
                        verb_es="El estado del ticket ha sido cambiado.",
                        verb_fr="Le statut du ticket a été modifié.",
                        icon="infinite",
                        redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
                    )
                    
                    mail_thread = TicketSendThread(
                        request,
                        ticket,
                        type="status_change",
                    )
                    mail_thread.start()

                    return Response(response, status=200)
                except Exception as e:
                    return Response({"errors": str(e)}, status=500)
            else:
                response = {
                    "type": "danger",
                    "message": _("You don't have the permission."),
                }
                return Response(response, status=403)
        else:
            response = {
                "type": "info",
                "message": _("The Ticket status is already up to date."),
            }
        
        return Response(response, status=200)




from operator import itemgetter




# views.py

class TicketDetailAPIView(APIView):
    """
    API view for fetching ticket details, including comments, attachments, and history.
    """
    
    def get(self, request, ticket_id, **kwargs):
        ticket = get_object_or_404(Ticket, id=ticket_id)
        user = request.user
        
        if (
            user.has_perm("helpdesk.view_ticket")
            or ticket.employee_id.get_reporting_manager() == user.employee_get
            or is_department_manager(request, ticket)
            or user.employee_get == ticket.employee_id
            or user.employee_get in ticket.assigned_to.all()
        ):
            serializer = TicketSerializer(ticket)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "You don't have permission to view this ticket."},
                status=status.HTTP_403_FORBIDDEN,
            )






class ViewTicketClaimRequestView(APIView):
    """
    API view for viewing claim requests for a Ticket.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        """
        Handles GET requests to view claim requests for a Ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if request.user.has_perm("helpdesk.change_ticket") or is_department_manager(request, ticket):
            claim_requests = ticket.claimrequest_set.all()
            claim_requests_data = []
            for claim_request in claim_requests:
                claim_requests_data.append({
                    "id": claim_request.id,
                    "ticket_id": claim_request.ticket_id_id,
                    "employee_id": claim_request.employee_id_id,
                    "is_approved": claim_request.is_approved,
                    "is_rejected": claim_request.is_rejected,
                })
            return Response(claim_requests_data, status=200)
        else:
            messages.info(request, _("You don't have permission."))
            return Response({"message": _("You don't have permission.")}, status=403)





class TicketChangeRaisedOnView(APIView):
    """
    API view for changing the raised_on field of a Ticket.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        """
        Handles GET requests to return the current raised_on field of a Ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if (
            request.user.has_perm("helpdesk.view_ticket")
            or request.user.employee_get == ticket.employee_id
        ):
            form = TicketRaisedOnForm(instance=ticket)
            response = {
                "ticket_id": ticket.id,
                "raised_on": ticket.raised_on,
                "form_initial_data": form.initial,
            }
            return Response(response, status=200)
        else:
            return Response({"message": _("You don't have permission.")}, status=403)

    def post(self, request, ticket_id):
        """
        Handles POST requests to update the raised_on field of a Ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if (
            request.user.has_perm("helpdesk.view_ticket")
            or request.user.employee_get == ticket.employee_id
        ):
            form = TicketRaisedOnForm(request.POST, instance=ticket)
            if form.is_valid():
                form.save()
                messages.success(request, _("Responsibility updated for the Ticket"))
                response = {
                    "type": "success",
                    "message": _("Responsibility updated for the Ticket"),
                }
                return Response(response, status=200)
            else:
                return Response({"errors": form.errors}, status=400)
        else:
            return Response({"message": _("You don't have permission.")}, status=403)






class TicketChangeAssigneesView(APIView):
    """
    API view for changing the assignees of a Ticket.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        """
        Handles GET requests to return the current assignees of a Ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if request.user.has_perm("helpdesk.change_ticket") or is_department_manager(request, ticket):
            form = TicketAssigneesForm(instance=ticket)
            assignees = list(ticket.assigned_to.values("id", "name"))  # Adjust the fields as needed
            response = {
                "ticket_id": ticket.id,
                "assignees": assignees,
                "form_initial_data": form.initial,
            }
            return Response(response, status=200)
        else:
            return Response({"message": _("You don't have permission.")}, status=403)

    def post(self, request, ticket_id):
        """
        Handles POST requests to update the assignees of a Ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        if request.user.has_perm("helpdesk.change_ticket") or is_department_manager(request, ticket):
            if not request.data or 'assigned_to' not in request.data:
                return Response({"errors": _("No data provided or 'assigned_to' field missing.")}, status=400)

            prev_assignee_ids = list(ticket.assigned_to.values_list("id", flat=True))
            form = TicketAssigneesForm(request.POST, instance=ticket)
            if form.is_valid():
                form.save(commit=False)
                new_assignee_ids = list(form.cleaned_data["assigned_to"].values_list("id", flat=True))
                added_assignee_ids = set(new_assignee_ids) - set(prev_assignee_ids)
                removed_assignee_ids = set(prev_assignee_ids) - set(new_assignee_ids)
                added_assignees = Employee.objects.filter(id__in=added_assignee_ids)
                removed_assignees = Employee.objects.filter(id__in=removed_assignee_ids)

                form.save()

                mail_thread = AddAssigneeThread(request, ticket, added_assignees)
                mail_thread.start()
                mail_thread = RemoveAssigneeThread(request, ticket, removed_assignees)
                mail_thread.start()

                response = {
                    "type": "success",
                    "message": _("Assignees updated for the Ticket"),
                }
                return Response(response, status=200)
            else:
                return Response({"errors": form.errors}, status=400)
        else:
            return Response({"message": _("You don't have permission.")}, status=403)

 # Make sure you have this utility function
import os
import base64

class ViewTicketDocumentView(APIView):
    """
    API view for viewing the uploaded document in a modal.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        """
        Handles GET requests to view the uploaded document in the modal.
        """
        document_obj = get_object_or_404(Attachment, id=doc_id)
        response_data = {
            "document": {
                "id": document_obj.id,
                "name": document_obj.file.name,
                "file_url": document_obj.file.url,
            },
        }
        if document_obj.file:
            file_path = document_obj.file.path
            file_extension = os.path.splitext(file_path)[1][1:].lower()  # Get the lowercase file extension
            content_type = get_content_type(file_extension)
            try:
                with open(file_path, "rb") as file:
                    file_content = base64.b64encode(file.read()).decode('utf-8')  # Encode the binary content for display
            except Exception as e:
                file_content = None
                response_data["error"] = str(e)

            response_data["file_content"] = file_content
            response_data["file_extension"] = file_extension
            response_data["content_type"] = content_type

        return Response(response_data, status=200)




class GetRaisedOnView(APIView):
    """
    API view to return list for raised on field based on the assigning type.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return list for raised on field.
        """
        data = request.GET
        assigning_type = data.get("assigning_type")

        if assigning_type == "department":
            # Retrieve data from the Department model and format it as a list of dictionaries
            departments = Department.objects.values("id", "department")
            raised_on = [
                {"id": dept["id"], "name": dept["department"]} for dept in departments
            ]
        elif assigning_type == "job_position":
            jobpositions = JobPosition.objects.values("id", "job_position")
            raised_on = [
                {"id": job["id"], "name": job["job_position"]} for job in jobpositions
            ]
        elif assigning_type == "individual":
            employees = Employee.objects.values(
                "id", "employee_first_name", "employee_last_name"
            )
            raised_on = [
                {
                    "id": employee["id"],
                    "name": f"{employee['employee_first_name']} {employee['employee_last_name']}",
                }
                for employee in employees
            ]
        else:
            raised_on = []

        response = {"raised_on": raised_on}
        return Response(response, status=200)




from notifications.signals import notify
from distutils.util import strtobool
import logging

logger = logging.getLogger(__name__)

class ApproveClaimRequestView(APIView):
    """
    API view to approve or reject a claim request and send notifications.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, req_id):
        """
        Handles POST requests to approve or reject a claim request.
        """
        claim_request = get_object_or_404(ClaimRequest, id=req_id)
        approve = strtobool(request.GET.get("approve", "False"))  # Safely convert to boolean

        ticket = claim_request.ticket_id
        employee = claim_request.employee_id
        if approve:
            message = _("Claim request approved successfully.")
            if employee not in ticket.assigned_to.all():
                ticket.assigned_to.add(employee)  # Approve and assign to employee
                try:
                    # Send notification
                    notify.send(
                        request.user.employee_get,
                        recipient=employee.employee_user_id,
                        verb=f"You have been assigned to a new Ticket-{ticket}.",
                        icon="infinite",
                        redirect=reverse("ticket-detail", kwargs={"ticket_id": ticket.id}),
                    )
                except Exception as e:
                    logger.error(e)
        else:
            message = _("Claim request rejected successfully.")
            if employee in ticket.assigned_to.all():
                ticket.assigned_to.remove(employee)  # Reject and remove from assignment
                try:
                    # Send notification
                    notify.send(
                        request.user.employee_get,
                        recipient=employee.employee_user_id,
                        verb=f"Your claim request is rejected for Ticket-{ticket}",
                        icon="infinite",
                    )
                except Exception as e:
                    logger.error(e)
        ticket.save()
        claim_request.is_approved = approve
        claim_request.is_rejected = not approve
        claim_request.save()

        return Response({"message": message}, status=200 if approve else 400)




class TicketsSelectFilterView(APIView):
    """
    API view to return all the ids of the filtered tickets.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return all the ids of the filtered tickets.
        """
        page_number = request.GET.get("page")
        filtered = request.GET.get("filter")
        filters = json.loads(filtered) if filtered else {}
        table = request.GET.get("tableName")
        user = request.user.employee_get

        tickets_filter = TicketFilter(filters, queryset=Ticket.objects.filter(is_active=True))

        if page_number == "all":
            if table == "all":
                tickets_filter = TicketFilter(filters, queryset=Ticket.objects.all())
            elif table == "my":
                tickets_filter = TicketFilter(filters, queryset=Ticket.objects.filter(employee_id=user))
            else:
                allocated_tickets = get_allocated_tickets(request)
                tickets_filter = TicketFilter(filters, queryset=allocated_tickets)

        # Get the filtered queryset
        filtered_tickets = tickets_filter.qs

        ticket_ids = [str(ticket.id) for ticket in filtered_tickets]
        total_count = filtered_tickets.count()

        context = {"ticket_ids": ticket_ids, "total_count": total_count}

        return Response(context, status=200)




class TicketsBulkArchiveView(APIView):
    """
    API view to archive bulk of Ticket instances.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to archive bulk of Ticket instances.
        """
        ids = request.data.get("ids")
        if not ids:
            return Response({"error": _("No ticket IDs provided.")}, status=400)

        try:
            ids = json.loads(ids)
        except json.JSONDecodeError:
            return Response({"error": _("Invalid JSON format for ticket IDs.")}, status=400)

        is_active = request.GET.get("is_active") == "True"
        failed_ids = []

        for ticket_id in ids:
            try:
                ticket = Ticket.objects.get(id=ticket_id)
                ticket.is_active = is_active
                ticket.save()
            except Ticket.DoesNotExist:
                failed_ids.append(ticket_id)

        if failed_ids:
            return Response({
                "message": _("Some tickets could not be updated."),
                "failed_ids": failed_ids
            }, status=400)

        response = {
            "message": _("The Tickets updated successfully."),
            "is_active": is_active
        }
        return Response(response, status=200)




class ClaimTicketView(APIView):
    #permission_classes = [IsAuthenticated]

    def post(self, request, id):
        ticket = get_object_or_404(Ticket, id=id)
        if ticket.employee_id != request.user.employee_get:
            ticket.assigned_to.set([request.user.employee_get])
            ticket.save()
            return Response({"detail": "Ticket successfully claimed."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "You already own this ticket."}, status=status.HTTP_400_BAD_REQUEST)



class TicketsBulkDeleteView(APIView):

    #permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TicketBulkDeleteSerializer(data=request.data)
        if serializer.is_valid():
            ids = serializer.validated_data['ids']
            for ticket_id in ids:
                try:
                    ticket = Ticket.objects.get(id=ticket_id)
                    mail_thread = TicketSendThread(
                        request,
                        ticket,
                        type="delete",
                    )
                    mail_thread.start()
                    employees = ticket.assigned_to.all()
                    assignees = [employee.employee_user_id for employee in employees]
                    assignees.append(ticket.employee_id.employee_user_id)
                    if hasattr(ticket.get_raised_on_object(), "dept_manager"):
                        if ticket.get_raised_on_object().dept_manager.all():
                            manager = (
                                ticket.get_raised_on_object().dept_manager.all().first().manager
                            )
                            assignees.append(manager.employee_user_id)
                    notify.send(
                        request.user.employee_get,
                        recipient=assignees,
                        verb=f"The ticket has been deleted.",
                        verb_ar="تم حذف التذكرة.",
                        verb_de="Das Ticket wurde gelöscht",
                        verb_es="El billete ha sido eliminado.",
                        verb_fr="Le ticket a été supprimé.",
                        icon="infinite",
                        redirect=f"/helpdesk/ticket-view/",
                    )
                    ticket.delete()
                    messages.success(
                        request,
                        _('The Ticket "{}" has been deleted successfully.').format(ticket),
                    )
                except ProtectedError:
                    messages.error(request, _("You cannot delete this Ticket."))
            return Response({"detail": "Tickets successfully deleted."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class DepartmentManagerCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        form = DepartmentManagerCreateForm(request.data, request.FILES)
        if form.is_valid():
            department_manager = form.save()
            return JsonResponse({
                "message": _("The department manager created successfully."),
                "department_manager_id": department_manager.id,
            }, status=status.HTTP_201_CREATED)
        else:
            return JsonResponse({
                "error": _("Invalid data"),
                "details": form.errors,
            }, status=status.HTTP_400_BAD_REQUEST)




class UpdateDepartmentManagerView(APIView):
    """
    API view for updating a department manager.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, dep_id):
        """
        Handles POST requests to update a department manager.
        """
        department_manager = get_object_or_404(DepartmentManager, id=dep_id)
        form = DepartmentManagerCreateForm(request.POST, request.FILES, instance=department_manager)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, _("The department manager updated successfully."))
                return Response({"message": _("The department manager updated successfully.")}, status=200)
            except ValidationError as e:
                return Response({"errors": e.messages}, status=400)
        return Response({"errors": form.errors}, status=400)




class DeleteDepartmentManagerView(APIView):
    """
    API view for deleting a department manager.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, dep_id):
        """
        Handles DELETE requests to delete a department manager.
        """
        department_manager = get_object_or_404(DepartmentManager, id=dep_id)
        department_manager.delete()
        messages.success(request, _("The department manager has been deleted successfully."))
        return Response({"message": _("The department manager has been deleted successfully.")}, status=200)




class UpdatePriorityView(APIView):
    """
    API view for updating the priority of a ticket.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        """
        Handles POST requests to update the priority of a ticket.
        """
        ticket = get_object_or_404(Ticket, id=ticket_id)
        user_employee = request.user.employee_get

        if (
            request.user.has_perm("helpdesk.view_ticket")
            or ticket.employee_id.get_reporting_manager() == user_employee
            or is_department_manager(request, ticket)
            or user_employee == ticket.employee_id
            or user_employee in ticket.assigned_to.all()
        ):
            rating = request.data.get("rating")

            if rating == "1":
                ticket.priority = "low"
            elif rating == "2":
                ticket.priority = "medium"
            else:
                ticket.priority = "high"
            ticket.save()
            messages.success(request, _("Priority updated successfully."))
            return Response({"message": _("Priority updated successfully.")}, status=200)
        else:
            messages.info(request, _("You don't have permission."))
            return Response({"message": _("You don't have permission.")}, status=403)





class TicketTypeDeleteView(APIView):
    """
    API view for deleting a ticket type.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, t_type_id):
        """
        Handles DELETE requests to delete a ticket type.
        """
        ticket_type = get_object_or_404(TicketType, id=t_type_id)
        ticket_type.delete()
        messages.success(request, _("Ticket type has been deleted successfully!"))
        return Response({"message": _("Ticket type has been deleted successfully!")}, status=200)





class ViewDepartmentManagersView(APIView):
    """
    API view to return all department managers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return all department managers.
        """
        department_managers = DepartmentManager.objects.all().values(
            "id", 
            "manager__employee_first_name", 
            "manager__employee_last_name", 
            "department__department"
        )
        return Response({"department_managers": list(department_managers)}, status=200)


class GetDepartmentEmployeesView(APIView):
    """
    API view to return employees in the department.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to return employees in the department.
        """
        department_id = request.GET.get("dep_id")
        department = Department.objects.filter(id=department_id).first() if department_id else None
        if department:
            employees_queryset = department.employeeworkinformation_set.all().values_list(
                "employee_id__id", "employee_id__employee_first_name"
            )
            employees = list(employees_queryset)
        else:
            employees = []

        return Response({"employees": employees}, status=200)




class DeleteTicketDocumentView(APIView):
    """
    API view to delete an uploaded document.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, doc_id):
        """
        Handles DELETE requests to delete an uploaded document.
        """
        document = get_object_or_404(Attachment, id=doc_id)
        document.delete()
        messages.success(request, _("Document has been deleted."))
        return Response({"message": _("Document has been deleted.")}, status=200)
