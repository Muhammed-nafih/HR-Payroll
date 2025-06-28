from rest_framework import serializers
from asset.models import Asset,AssetReport, AssetDocuments,AssetCategory,AssetRequest,AssetAssignment, ReturnImages,AssetLot,Employee

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'



class AssetReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetReport
        fields = '__all__'

class AssetDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetDocuments
        fields = '__all__'




class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = '__all__'



class AssetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetRequest
        fields = '__all__'



class AssetAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAssignment
        fields = '__all__'




class AssetAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAssignment
        fields = '__all__'

class ReturnImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnImages
        fields = '__all__'




class AssetAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAssignment
        fields = '__all__'


class AssetLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetLot
        fields = '__all__'


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'

