import base64
from rest_framework import serializers
from employee.models import Employee
from payroll.models.models import Contract
from leave.models import AvailableLeave
from base.models import WorkTypeRequest, RotatingShiftAssign, RotatingWorkTypeAssign, ShiftRequest

class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = ['contract_name', 'employee_id']


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer for Employee model.
    """
    class Meta:
        model = Employee
        fields = '__all__'
        
        extra_kwargs = {
            'badge_id': {'required': True},
            'employee_first_name': {'required': True},
            'employee_last_name': {'required': True},  
            'email': {'required': True},
            'phone': {'required': True},
        }


class AvailableLeaveSerializer(serializers.ModelSerializer):
    contract_name = serializers.SerializerMethodField()

    class Meta:
        model = AvailableLeave
        fields = ['employee_id', 'contract_name', 'leave_type_id']  

    def get_contract_name(self, obj):
        return obj.contract.contract_name if obj.contract else None        
    

from rest_framework import serializers
from employee.models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__' 




class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__' 

class WorkTypeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkTypeRequest
        fields = '__all__'  

class RotatingShiftAssignSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotatingShiftAssign
        fields = '__all__'  

class RotatingWorkTypeAssignSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotatingWorkTypeAssign
        fields = '__all__'  

class ShiftRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftRequest
        fields = '__all__'  


from horilla_documents.models import DocumentRequest

from .serializers import EmployeeSerializer
from .serializers import DocumentRequest

class DocumentRequestSerializer(serializers.ModelSerializer):
    
    employee_id = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), many=True)

    class Meta:
        model = DocumentRequest
        fields = ['id', 'title', 'employee_id', 'format', 'max_size', 'description']



from horilla_documents.models import Document

class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer to handle document data for API endpoints.
    """
    class Meta:
        model = Document
        fields = ['id', 'title', 'employee_id', 'document_request_id', 'document', 'status', 'reject_reason', 'expiry_date', 'notify_before', 'is_digital_asset']

    def update(self, instance, validated_data):
        """
        Override the update method to customize how the document title is updated.
        """
        title = validated_data.get('title', instance.title)
        instance.title = title
        instance.save()
        return instance
    


class DocumentDeleteSerializer(serializers.Serializer):
   
    id = serializers.IntegerField()

    def validate_id(self, value):
        
        try:
            document = Document.objects.get(id=value)
        except Document.DoesNotExist:
            raise serializers.ValidationError("Document not found.")
        
        
        return value    
    

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'employee_id', 'document_request_id', 'document', 'status', 'reject_reason', 'expiry_date', 'notify_before', 'is_digital_asset']    





class DocumentSerializer(serializers.ModelSerializer):
    file_content = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = '__all__'

    def get_file_content(self, obj):
        """Encode the document file content in base64 format, if available."""
        if obj.document:
            try:
                with open(obj.document.path, "rb") as file:
                    return base64.b64encode(file.read()).decode('utf-8')
            except FileNotFoundError:
                return None
        return None

    def get_content_type(self, obj):
        """Retrieve MIME type based on file extension."""
        extension = self.get_file_extension(obj)
        content_types = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "txt": "text/plain",
            # Add more as needed
        }
        return content_types.get(extension, "application/octet-stream")

    def get_file_extension(self, obj):
        """Retrieve file extension if document exists."""
        if obj.document:
            return obj.document.path.split('.')[-1].lower()
        return None
    




class FileContentTypeSerializer(serializers.Serializer):
    file_extension = serializers.CharField(max_length=10)
    content_type = serializers.CharField(max_length=100)    