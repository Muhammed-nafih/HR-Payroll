from rest_framework import serializers
import django_filters
from helpdesk.models import TicketType,FAQCategory,FAQ,Ticket,Attachment,Comment,ClaimRequest

class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = '__all__'




class FAQCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQCategory
        fields = '__all__'



class FAQCategoryFilter(django_filters.FilterSet):
    class Meta:
        model = FAQCategory
        fields = '__all__'


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'




class FAQFilter(django_filters.FilterSet):
    class Meta:
        model = FAQ
        fields = '__all__'



class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'



class TicketFilter(django_filters.FilterSet):
    class Meta:
        model = Ticket
        fields = '__all__'



class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'


class ClaimRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimRequest
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'
        extra_kwargs = {
            'employee_id': {'write_only': True},
            'ticket': {'write_only': True},
        }

class CommentEditSerializer(serializers.ModelSerializer):
   

    class Meta:
        model = Comment
        fields = '__all__'



class ClaimRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimRequest
        fields = '__all__'



class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'


class TicketBulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField()
    )
