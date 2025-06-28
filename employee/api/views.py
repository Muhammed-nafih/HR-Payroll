from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from employee.models import Employee
from payroll.models.models import Contract
from leave.models import AvailableLeave  
from .serializers import EmployeeSerializer, ContractSerializer, AvailableLeaveSerializer, DocumentRequestSerializer, DocumentDeleteSerializer, DocumentSerializer, FileContentTypeSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate




class ContractTabView(APIView):
    permission_classes = [IsAuthenticated]  

    def get(self, request, obj_id, *args, **kwargs):
        
        try:
           
            employee = Employee.objects.get(id=obj_id)
        except Employee.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
       
        employee_leaves = AvailableLeave.objects.filter(employee_id=obj_id)

       
        contracts = Contract.objects.filter(employee_id=obj_id)

        
        employee_serializer = EmployeeSerializer(employee)
        leave_serializer = AvailableLeaveSerializer(employee_leaves, many=True)
        contract_serializer = ContractSerializer(contracts, many=True)

        
        response_data = {
            "employee": employee_serializer.data,
            "employee_leaves": leave_serializer.data,
            "contracts": contract_serializer.data,
        }

        
        return Response(response_data, status=status.HTTP_200_OK)
    


from rest_framework.decorators import api_view
from django.core.paginator import Paginator
from django.http import JsonResponse
from employee.filters import EmployeeFilter 


class EmployeeViewAPI(APIView):
    """
    This API returns filtered employee data based on query parameters.
    Optionally accepts an `obj_id` parameter to filter by specific employee.
    """

    def get(self, request, obj_id=None, *args, **kwargs):
        """
        Handle GET requests to filter and return employee data.
        Optionally filter by obj_id (employee ID).
        """
        
        view_type = request.GET.get("view")
        page_number = request.GET.get("page", 1)
        previous_data = request.GET.urlencode()

        
        if obj_id:
            queryset = Employee.objects.filter(id=obj_id, is_active=True)
        else:
            queryset = Employee.objects.filter(is_active=True)

        filter_obj = EmployeeFilter(request.GET, queryset=queryset)

       
        paginator = Paginator(filter_obj.qs, 10)
        page = paginator.get_page(page_number)

        
        serializer = EmployeeSerializer(page.object_list, many=True)

        
        response_data = {
            "data": serializer.data,
            "total_pages": paginator.num_pages,
            "current_page": page.number,
            "previous_data": previous_data,
            "view_type": view_type,
            "filter_dict": request.GET.dict(),
        }

        return Response(response_data, status=status.HTTP_200_OK)
    


from base.models import WorkTypeRequest, RotatingShiftAssign, RotatingWorkTypeAssign, ShiftRequest
from .serializers import (EmployeeSerializer, WorkTypeRequestSerializer, 
                          RotatingShiftAssignSerializer, RotatingWorkTypeAssignSerializer, 
                          ShiftRequestSerializer)


class ShiftTabAPIView(APIView):
    """
    API endpoint to view the shift tab data of an employee.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id, *args, **kwargs):
        """
        Handle GET requests to retrieve shift tab data.

        Parameters:
        emp_id (int): The ID of the employee.

        Returns:
        Response (JSON): JSON response with shift-tab data.
        """
       
        try:
            employee = Employee.objects.get(id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)

        work_type_requests = WorkTypeRequest.objects.filter(employee_id=emp_id)
        rshift_assign = RotatingShiftAssign.objects.filter(employee_id=emp_id)
        rwork_type_assign = RotatingWorkTypeAssign.objects.filter(employee_id=emp_id)
        shift_requests = ShiftRequest.objects.filter(employee_id=emp_id)

        
        employee_data = EmployeeSerializer(employee).data
        work_type_requests_data = WorkTypeRequestSerializer(work_type_requests, many=True).data
        rshift_assign_data = RotatingShiftAssignSerializer(rshift_assign, many=True).data
        rwork_type_assign_data = RotatingWorkTypeAssignSerializer(rwork_type_assign, many=True).data
        shift_requests_data = ShiftRequestSerializer(shift_requests, many=True).data

        
        response_data = {
            "employee": employee_data,
            "work_type_requests": work_type_requests_data,
            "rshift_assign": rshift_assign_data,
            "rwork_type_assign": rwork_type_assign_data,
            "shift_requests": shift_requests_data,
        }

        return Response(response_data)
    
from horilla_documents.models import DocumentRequest
class DocumentRequestAPIView(APIView):
    """
    API endpoint to create and retrieve document request data.
    """
    permission_classes = [IsAuthenticated]  

    def get(self, request, *args, **kwargs):
        """
        Handle GET request to retrieve document request data by ID.
        """
        document_request_id = kwargs.get('request_id')
        try:
            document_request = DocumentRequest.objects.get(id=document_request_id)
        except DocumentRequest.DoesNotExist:
            return Response({"error": "Document request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        document_request_data = DocumentRequestSerializer(document_request).data
        return Response(document_request_data)

    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create a new document request.
        """
        serializer = DocumentRequestSerializer(data=request.data)
        if serializer.is_valid():
            document_request = serializer.save()

            return Response({
                "message": "Document request created successfully.",
                "data": DocumentRequestSerializer(document_request).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    
    



from django.shortcuts import get_object_or_404
from horilla_documents.models import Document

class UpdateDocumentTitleAPIView(APIView):
    """
    API endpoint to update the document title.
    """
    def put(self, request, id, *args, **kwargs):
        """
        Handle PUT requests to update the title of a document.

        Parameters:
        id (int): The ID of the document.

        Returns:
        Response: JSON response indicating success or failure.
        """
        document = get_object_or_404(Document, id=id)

        
        new_title = request.data.get("title")

        if new_title:
            
            document.title = new_title
            document.save()

            return Response(
                {"success": True, "message": "Document title updated successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": "Title is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )


from django.db.models.deletion import ProtectedError


class DocumentDeleteAPIView(APIView):
   
    permission_classes = [IsAuthenticated]  

    def delete(self, request, id, *args, **kwargs):
        
        print(f"Received ID: {id}")  
        try:
            
            document = Document.objects.filter(id=id)

            
            if not request.user.has_perm("horilla_documents.delete_document"):
                document = document.filter(employee_id__employee_user_id=request.user)

            if document.exists():
                
                document.delete()
                return Response(
                    {"success": True, "message": "Document deleted successfully"},
                    status=status.HTTP_204_NO_CONTENT,
                )
            else:
                return Response(
                    {"success": False, "message": "Document not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except ProtectedError:
            return Response(
                {"success": False, "message": "You cannot delete this document."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
from rest_framework.parsers import MultiPartParser, FormParser
from django.urls import reverse
from notifications import notify  

class DocumentUploadAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, id):
        document_item = get_object_or_404(Document, id=id)
        serializer = DocumentSerializer(document_item)
        return Response(serializer.data)

    def post(self, request, id):
        document_item = get_object_or_404(Document, id=id)
        serializer = DocumentSerializer(document_item, data=request.data, partial=True)

        if serializer.is_valid():
            document_item = serializer.save()
            
            try:
              
                notify.send(
                    request.user.employee_get,
                    recipient=request.user.employee_get.get_reporting_manager().employee_user_id,
                    verb=f"{request.user.employee_get} uploaded a document",
                    verb_ar=f"قام {request.user.employee_get} بتحميل مستند",
                    verb_de=f"{request.user.employee_get} hat ein Dokument hochgeladen",
                    verb_es=f"{request.user.employee_get} subió un documento",
                    verb_fr=f"{request.user.employee_get} a téléchargé un document",
                    redirect=reverse(
                        "employee-view-individual",
                        kwargs={"obj_id": request.user.employee_get.id},
                    ),
                    icon="chatbox-ellipses",
                )
            except Exception as e:
                return Response({"success": False, "message": "Notification failed", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"success": True, "message": "Document uploaded successfully", "document": serializer.data}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DocumentDetailView(APIView):
    """
    API endpoint to retrieve details of a specific document.
    """

    def get(self, request, id, format=None):
        
        document_obj = get_object_or_404(Document, id=id)

        serializer = DocumentSerializer(document_obj)

        return Response(serializer.data, status=status.HTTP_200_OK)
    



class FileContentTypeView(APIView):
    """
    API view to return the content type based on the file extension.
    """

    def get(self, request, file_extension, *args, **kwargs):
        content_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "jpg": "image/jpeg",
            "png": "image/png",
            "jpeg": "image/jpeg",
        }
        
        content_type = content_types.get(file_extension.lower(), "application/octet-stream")
        
    
        data = {
            "file_extension": file_extension,
            "content_type": content_type,
        }
        
        
        serializer = FileContentTypeSerializer(data)
        
        return Response(serializer.data, status=status.HTTP_200_OK) 



        
    