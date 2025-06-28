from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from asset.models import Asset, AssetCategory,AssetReport, AssetDocuments, AssetAssignment,AssetCategory,AssetRequest,AssetLot,Employee, Company
from asset.forms import AssetForm,AssetReportForm,AssetBatchForm
from .serializers import AssetSerializer,AssetDocumentsSerializer,AssetReportSerializer,AssetCategorySerializer,AssetRequestSerializer,AssetAllocationSerializer,ReturnImagesSerializer,AssetAssignmentSerializer,AssetLotSerializer
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
import json
from asset.filters import AssetFilter,AssetHistoryFilter,AssetHistoryReGroup, AssetExportFilter

from base.methods import closest_numbers,get_pagination,get_key_instances, sortby,filtersubordinates
from base.views import paginator_qry
from django.core.paginator import Paginator
from urllib.parse import parse_qs
from django.contrib import messages
from django.http import HttpResponse 
from django.urls import reverse
from django.utils.translation import gettext as _
from horilla import settings
from rest_framework.response import Response
from django.http import JsonResponse
from employee.authentication import JWTAuthentication
from asset.views import filter_pagination_asset_category,filter_pagination_asset_request_allocation,csv_asset_import,spreadsheetml_asset_import
from horilla.horilla_settings import HORILLA_DATE_FORMATS
from employee.models import EmployeeWorkInformation
from datetime import datetime, date



class AssetCreation(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, asset_category_id):
        try:
            initial_data = {"asset_category_id": asset_category_id}
            category = get_object_or_404(AssetCategory, id=asset_category_id)
            data = request.data.copy()
            data.update(initial_data)
            
            serializer = AssetSerializer(data=data)
            if serializer.is_valid():
                asset = serializer.save()
                response_data = {
                    "detail": "Asset created successfully",
                    "asset": AssetSerializer(asset).data
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AddAssetReport(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, asset_id=None):
        try:
            initial_data = {"asset_id": asset_id}
            if asset_id:
                asset = get_object_or_404(Asset, id=asset_id)
                form = AssetReportForm(request.POST, request.FILES, initial=initial_data)
                
                # Check permissions
                if not request.GET.get("asset_list"):
                    asset_assignment = AssetAssignment.objects.get(
                        asset_id=asset_id, return_date__isnull=True
                    )
                    if request.user.employee_get != asset_assignment.assigned_to_employee_id and not request.user.has_perm("asset.change_asset"):
                        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

                if form.is_valid():
                    asset_report = form.save()
                    if request.FILES:
                        for file in request.FILES.getlist("file"):
                            AssetDocuments.objects.create(asset_report=asset_report, file=file)
                    response_data = {
                        "detail": "Report added successfully.",
                        "asset_report": AssetReportSerializer(asset_report).data,
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": "Asset ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AssetUpdate(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, asset_id):
        try:
            instance = get_object_or_404(Asset, id=asset_id)

            # Check if any data is passed
            if not request.data:
                return Response({"error": "No data provided."}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = AssetSerializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                asset = serializer.save()
                response_data = {
                    "detail": "Asset updated successfully",
                    "asset": AssetSerializer(asset).data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class AssetInformation(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, asset_id):
        try:
            asset = get_object_or_404(Asset, id=asset_id)
            serializer = AssetSerializer(asset)
            response_data = {
                "asset": serializer.data
            }
            requests_ids_json = request.GET.get("requests_ids")
            if requests_ids_json:
                requests_ids = json.loads(requests_ids_json)
                previous_id, next_id = closest_numbers(requests_ids, asset_id)
                response_data["requests_ids"] = requests_ids
                response_data["previous"] = previous_id
                response_data["next"] = next_id
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssetDelete(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def delete(self, request, asset_id):
        try:
            asset = get_object_or_404(Asset, id=asset_id)
            asset_status = asset.asset_status
            asset_allocation = AssetAssignment.objects.filter(asset_id=asset).first()

            if asset_status == "In use":
                return Response({"error": "Asset is in use"}, status=status.HTTP_400_BAD_REQUEST)
            elif asset_allocation:
                return Response({"error": "Asset is used in allocation"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                asset.delete()
                return Response({"detail": "Asset deleted successfully"}, status=status.HTTP_200_OK)
        except Asset.DoesNotExist:
            return Response({"error": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssetList(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, cat_id):
        try:
            asset_filtered = AssetFilter(request.GET, queryset=Asset.objects.filter(asset_category_id=cat_id))
            asset_list = asset_filtered.qs

            paginator = Paginator(asset_list, 10)  # Assuming 10 items per page
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)

            requests_ids = [instance.id for instance in page_obj.object_list]
            previous_data = request.GET.urlencode()
            data_dict = parse_qs(previous_data)

            response_data = {
                "assets": AssetSerializer(page_obj.object_list, many=True).data,
                "pg": previous_data,
                "asset_category_id": cat_id,
                "asset_under": "",
                "asset_count": len(asset_list),
                "filter_dict": data_dict,
                "requests_ids": requests_ids,
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssetCategoryCreation(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            serializer = AssetCategorySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                response_data = {
                    "detail": "Asset category created successfully",
                    "asset_category": serializer.data
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssetCategoryUpdate(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, cat_id):
        try:
            asset_category = get_object_or_404(AssetCategory, id=cat_id)

            # Check if any data is passed
            if not request.data:
                return Response({"error": "No data provided."}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = AssetCategorySerializer(asset_category, data=request.data, partial=True)
            if serializer.is_valid():
                asset_category = serializer.save()
                response_data = {
                    "detail": "Asset category updated successfully",
                    "asset_category": AssetCategorySerializer(asset_category).data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DeleteAssetCategory(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def delete(self, request, cat_id):
        try:
            asset_category = get_object_or_404(AssetCategory, id=cat_id)
            
            # Check if there are any assets associated with this category
            if Asset.objects.filter(asset_category_id=asset_category).exists():
                return Response({"error": "Assets are located within this category."}, status=status.HTTP_400_BAD_REQUEST)
            
            asset_category.delete()
            return Response({"detail": "Asset category deleted successfully"}, status=status.HTTP_200_OK)
        except AssetCategory.DoesNotExist:
            return Response({"error": "Asset category not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AssetCategoryView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        queryset = AssetCategory.objects.all()
        page_number = request.GET.get("page", 1)
        paginator = Paginator(queryset, 10)  # Assuming 10 items per page
        page_obj = paginator.get_page(page_number)

        serializer = AssetCategorySerializer(page_obj.object_list, many=True)
        response_data = {
            "asset_categories": serializer.data,
            "page": page_number,
            "num_pages": paginator.num_pages,
            "total_assets": paginator.count,
        }
        return Response(response_data, status=status.HTTP_200_OK)



class AssetRequestCreation(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            serializer = AssetRequestSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"detail": "Asset request created successfully"}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AssetRequestApprove(APIView):
    permission_classes = [IsAuthenticated, ]
    authentication_classes = [JWTAuthentication]

    def post(self, request, req_id):
        try:
            asset_request = get_object_or_404(AssetRequest, id=req_id)
            asset_category = asset_request.asset_category_id
            assets = asset_category.asset_set.filter(asset_status="Available")
            
            if not assets.exists():
                return Response({"error": "No available assets in this category."}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data.copy()
            data["assigned_to_employee_id"] = asset_request.requested_employee_id.id
            data["assigned_by_employee_id"] = request.user.employee_get.id

            serializer = AssetAllocationSerializer(data=data)
            if serializer.is_valid():
                asset = assets.first()
                asset.asset_status = "In use"
                asset.save()
                
                asset_allocation = serializer.save()
                asset_request.asset_request_status = "Approved"
                asset_request.save()

                # Send notification
                # notify.send(request.user.employee_get, recipient=asset_allocation.assigned_to_employee_id.employee_user_id, verb="Your asset request approved!.", verb_ar="تم الموافقة على طلب الأصول الخاص بك!", verb_de="Ihr Antragsantrag wurde genehmigt!", verb_es="¡Su solicitud de activo ha sido aprobada!", verb_fr="Votre demande d'actif a été approuvée !", redirect=reverse("asset-request-allocation-view") + f"?asset_request_date={asset_request.asset_request_date}&asset_request_status={asset_request.asset_request_status}", icon="bag-check")

                return Response({"detail": "Asset request approved successfully"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except AssetRequest.DoesNotExist:
            return Response({"error": "Asset request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AssetRequestReject(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request, req_id):
        try:
            asset_request = get_object_or_404(AssetRequest, id=req_id)
            asset_request.asset_request_status = "Rejected"
            asset_request.save()
            
            # Send notification
            # notify.send(request.user.employee_get, recipient=asset_request.requested_employee_id.employee_user_id, verb="Your asset request rejected!.", verb_ar="تم رفض طلب الأصول الخاص بك!", verb_de="Ihr Antragsantrag wurde abgelehnt!", verb_es="¡Se ha rechazado su solicitud de activo!", verb_fr="Votre demande d'actif a été rejetée !", redirect=reverse("asset-request-allocation-view") + f"?asset_request_date={asset_request.asset_request_date}&asset_request_status={asset_request.asset_request_status}", icon="bag-check")
            
            return Response({"detail": "Asset request rejected successfully"}, status=status.HTTP_200_OK)
        except AssetRequest.DoesNotExist:
            return Response({"error": "Asset request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AssetAllocateCreation(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            serializer = AssetAllocationSerializer(data=request.data)
            if serializer.is_valid():
                asset_id = serializer.validated_data['asset_id'].id
                asset = Asset.objects.get(id=asset_id)
                asset.asset_status = "In use"
                asset.save()
                
                allocation_instance = serializer.save()
                
                return Response({"detail": "Asset allocated successfully"}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssetAllocateReturnRequest(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, asset_id):
        try:
            asset_assign = get_object_or_404(AssetAssignment, id=asset_id)
            asset_assign.return_request = True
            asset_assign.save()

            # Send notification
            # permed_users = horilla_users_with_perms("asset.change_assetassignment")
            # notify.send(
            #     request.user.employee_get,
            #     recipient=permed_users,
            #     verb=f"Return request for {asset_assign.asset_id} initiated from {asset_assign.assigned_to_employee_id}",
            #     verb_ar=f"تم بدء طلب الإرجاع للمورد {asset_assign.asset_id} من الموظف {asset_assign.assigned_to_employee_id}",
            #     verb_de=f"Rückgabewunsch für {asset_assign.asset_id} vom Mitarbeiter {asset_assign.assigned_to_employee_id} initiiert",
            #     verb_es=f"Solicitud de devolución para {asset_assign.asset_id} iniciada por el empleado {asset_assign.assigned_to_employee_id}",
            #     verb_fr=f"Demande de retour pour {asset_assign.asset_id} initiée par l'employé {asset_assign.assigned_to_employee_id}",
            #     redirect=reverse("asset-request-allocation-view") + f"?assigned_to_employee_id={asset_assign.assigned_to_employee_id}&asset_id={asset_assign.asset_id}&assigned_date={asset_assign.assigned_date}",
            #     icon="bag-check",
            # )

            return Response({"detail": "Return request initiated successfully"}, status=status.HTTP_200_OK)
        except AssetAssignment.DoesNotExist:
            return Response({"error": "Asset assignment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class AssetAllocateReturn(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, asset_id):
        try:
            asset_allocation = AssetAssignment.objects.filter(asset_id=asset_id, return_status__isnull=True).first()
            if not asset_allocation:
                return Response({"error": "Asset allocation not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if any data is passed
            if not request.data:
                return Response({"error": "No data provided."}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = AssetAssignmentSerializer(asset_allocation, data=request.data, partial=True)
            if serializer.is_valid():
                asset = Asset.objects.get(id=asset_id)
                asset_return_status = request.data.get("return_status")
                asset_return_date = request.data.get("return_date")
                asset_return_condition = request.data.get("return_condition")
                files = request.FILES.getlist("return_images")
                attachments = []

                if asset_return_status == "Healthy":
                    asset_allocation.return_date = asset_return_date
                    asset_allocation.return_status = asset_return_status
                    asset_allocation.return_condition = asset_return_condition
                    asset_allocation.return_request = False
                    asset_allocation.save()

                    for file in files:
                        image_data = {"image": file}
                        image_serializer = ReturnImagesSerializer(data=image_data)
                        if image_serializer.is_valid():
                            attachment = image_serializer.save()
                            attachments.append(attachment)
                    asset_allocation.return_images.add(*attachments)
                    
                    asset.asset_status = "Available"
                    asset.save()
                else:
                    asset.asset_status = "Not-Available"
                    asset.save()
                    
                    asset_allocation.return_date = asset_return_date
                    asset_allocation.return_status = asset_return_status
                    asset_allocation.return_condition = asset_return_condition
                    asset_allocation.save()
                    
                    for file in files:
                        image_data = {"image": file}
                        image_serializer = ReturnImagesSerializer(data=image_data)
                        if image_serializer.is_valid():
                            attachment = image_serializer.save()
                            attachments.append(attachment)
                    asset_allocation.return_images.add(*attachments)
                
                return Response({"detail": "Asset return successful"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






class OwnAssetIndividualAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, asset_id, *args, **kwargs):
        try:
            asset_assignment = AssetAssignment.objects.get(id=asset_id)
        except AssetAssignment.DoesNotExist:
            return Response({'detail': 'Asset Assignment not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssetAssignmentSerializer(asset_assignment)
        data = serializer.data

        requests_ids_json = request.GET.get("assets_ids")
        if requests_ids_json:
            requests_ids = json.loads(requests_ids_json)
            previous_id, next_id = closest_numbers(requests_ids, asset_id)
            data["assets_ids"] = requests_ids_json
            data["previous"] = previous_id
            data["next"] = next_id

        return Response(data, status=status.HTTP_200_OK)



class AssetRequestIndividualAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, asset_request_id, *args, **kwargs):
        try:
            asset_request = AssetRequest.objects.get(id=asset_request_id)
        except AssetRequest.DoesNotExist:
            return Response({'detail': 'Asset Request not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssetRequestSerializer(asset_request)
        data = serializer.data

        requests_ids_json = request.GET.get("requests_ids")
        if requests_ids_json:
            requests_ids = json.loads(requests_ids_json)
            previous_id, next_id = closest_numbers(requests_ids, asset_request_id)
            data["requests_ids"] = requests_ids_json
            data["previous"] = previous_id
            data["next"] = next_id

        return Response(data, status=status.HTTP_200_OK)



class AssetAllocationIndividualAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, asset_allocation_id, *args, **kwargs):
        try:
            asset_allocation = AssetAssignment.objects.get(id=asset_allocation_id)
        except AssetAssignment.DoesNotExist:
            return Response({'detail': 'Asset Allocation not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssetAssignmentSerializer(asset_allocation)
        data = serializer.data

        allocation_ids_json = request.GET.get("allocations_ids")
        if allocation_ids_json:
            allocation_ids = json.loads(allocation_ids_json)
            previous_id, next_id = closest_numbers(allocation_ids, asset_allocation_id)
            data["allocations_ids"] = allocation_ids_json
            data["previous"] = previous_id
            data["next"] = next_id

        return Response(data, status=status.HTTP_200_OK)





class AssetBatchNumberCreationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def post(self, request, *args, **kwargs):
        try:
            asset_batch_form = AssetBatchForm(request.data)
            if asset_batch_form.is_valid():
                asset_batch_form.save()
                messages.success(request, _("Batch number created successfully."))

                hx_vals = request.GET.get("data") if request.GET.get("data") else request.GET.urlencode()

                if AssetLot.objects.filter().count() == 1 and not hx_vals:
                    return HttpResponse("<script>location.reload();</script>")
                if hx_vals:
                    category_id = request.GET.get("asset_category_id")
                    url = reverse("asset-creation", args=[category_id])
                    instance = AssetLot.objects.all().order_by("-id").first()
                    mutable_get = request.GET.copy()
                    mutable_get["asset_lot_number_id"] = str(instance.id)
                    hx_get = f"{url}?{mutable_get.urlencode()}"
                    hx_target = "#objectCreateModalTarget"

                    data = {
                        "hx_get": hx_get,
                        "hx_target": hx_target
                    }

                    return Response(data, status=status.HTTP_201_CREATED)
                
                return Response({"detail": "Batch number created successfully."}, status=status.HTTP_201_CREATED)

            return Response(asset_batch_form.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)







class AssetBatchViewAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            asset_batches = AssetLot.objects.all()
        except AssetLot.DoesNotExist:
            return Response({'detail': 'Asset lots not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        previous_data = request.GET.urlencode()
        page_number = request.GET.get("page")

        try:
            paginator = Paginator(asset_batches, get_pagination())
            asset_batch_numbers = paginator.get_page(page_number)
        except Exception as e:
            return Response({'detail': 'Pagination error: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            asset_batch_form = AssetBatchForm()
        except Exception as e:
            return Response({'detail': 'Form rendering error: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = {
            "batch_numbers": AssetLotSerializer(asset_batch_numbers, many=True).data,
            "asset_batch_form": asset_batch_form.as_p(),  # Render the form as HTML
            "pg": previous_data,
        }

        return Response(data, status=status.HTTP_200_OK)




class AssetBatchUpdateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, batch_id, *args, **kwargs):
        try:
            asset_batch = AssetLot.objects.get(id=batch_id)
        except AssetLot.DoesNotExist:
            return Response({'detail': 'Asset batch not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        asset_batch_form = AssetBatchForm(instance=asset_batch)
        assigned_batch_number = Asset.objects.filter(asset_lot_number_id=asset_batch.id)
        context = {
            "asset_batch_update_form": asset_batch_form.as_p(),  # Render the form as HTML
            "in_use_message": _("This batch number is already in-use") if assigned_batch_number else None
        }

        return Response(context, status=status.HTTP_200_OK)

    def post(self, request, batch_id, *args, **kwargs):
        try:
            asset_batch_number = get_object_or_404(AssetLot, id=batch_id)
            asset_batch_form = AssetBatchForm(request.data, instance=asset_batch_number)
            if asset_batch_form.is_valid():
                asset_batch_form.save()
                messages.info(request, _("Batch updated successfully."))
                return Response({"detail": "Batch updated successfully."}, status=status.HTTP_200_OK)
            return Response(asset_batch_form.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except AssetLot.DoesNotExist:
            return Response({'detail': 'Asset batch not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.db.models import ProtectedError


class AssetBatchNumberDeleteAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def delete(self, request, batch_id, *args, **kwargs):
        previous_data = request.GET.urlencode()
        try:
            asset_batch_number = get_object_or_404(AssetLot, id=batch_id)
            assigned_batch_number = Asset.objects.filter(asset_lot_number_id=asset_batch_number)
            
            if assigned_batch_number.exists():
                return Response({'detail': _('Batch number in-use')}, status=status.HTTP_400_BAD_REQUEST)
            
            asset_batch_number.delete()
            messages.success(request, _("Batch number deleted"))
            
            if not AssetLot.objects.filter().exists():
                return HttpResponse("<script>location.reload();</script>")
            
            return Response({'detail': 'Batch number deleted successfully.'}, status=status.HTTP_200_OK)

        except AssetLot.DoesNotExist:
            return Response({'detail': _('Batch number not found')}, status=status.HTTP_404_NOT_FOUND)
        except ProtectedError:
            return Response({'detail': _('You cannot delete this Batch number.')}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






class AssetBatchNumberSearchAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        search_query = request.GET.get("search", "")
        
        try:
            asset_batches = AssetLot.objects.all().filter(lot_number__icontains=search_query)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        previous_data = request.GET.urlencode()
        page_number = request.GET.get("page")
        
        try:
            paginator = Paginator(asset_batches, get_pagination())
            asset_batch_numbers = paginator.get_page(page_number)
        except Exception as e:
            return Response({'detail': 'Pagination error: ' + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = {
            "batch_numbers": AssetLotSerializer(asset_batch_numbers, many=True).data,
            "pg": previous_data,
        }

        return Response(data, status=status.HTTP_200_OK)





class AssetCountUpdateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def post(self, request, *args, **kwargs):
        try:
            category_id = request.data.get("asset_category_id")
            if category_id is not None:
                category = get_object_or_404(AssetCategory, id=category_id)
                asset_count = category.asset_set.count()
                return Response({"asset_count": asset_count}, status=status.HTTP_200_OK)
            return Response({"detail": "asset_category_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        except AssetCategory.DoesNotExist:
            return Response({"detail": "Asset category not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AssetDashboardAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            assets = Asset.objects.all()
            asset_in_use = Asset.objects.filter(asset_status="In use")
            asset_requests = AssetRequest.objects.filter(
                asset_request_status="Requested", requested_employee_id__is_active=True
            )
            requests_ids = [instance.id for instance in asset_requests]
            asset_allocations = AssetAssignment.objects.filter(
                asset_id__asset_status="In use", assigned_to_employee_id__is_active=True
            )
            
            data = {
                "assets": AssetSerializer(assets, many=True).data,
                "asset_requests": AssetRequestSerializer(asset_requests, many=True).data,
                "requests_ids": json.dumps(requests_ids),
                "asset_in_use": AssetSerializer(asset_in_use, many=True).data,
                "asset_allocations": AssetAssignmentSerializer(asset_allocations, many=True).data,
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from rest_framework.response import Response
from django.http import JsonResponse

class AssetAvailableChartAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            asset_available = Asset.objects.filter(asset_status="Available")
            asset_unavailable = Asset.objects.filter(asset_status="Not-Available")
            asset_in_use = Asset.objects.filter(asset_status="In use")

            labels = ["In use", "Available", "Not-Available"]
            dataset = [
                {
                    "label": _("asset"),
                    "data": [len(asset_in_use), len(asset_available), len(asset_unavailable)],
                },
            ]

            response = {
                "labels": labels,
                "dataset": dataset,
                "message": _("Oops!! No Asset found..."),
                "emptyImageSrc": f"/{settings.STATIC_URL}images/ui/asset.png",
            }

            return JsonResponse(response)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AssetCategoryChartAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            asset_categories = AssetCategory.objects.all()
            data = []
            for asset_category in asset_categories:
                category_count = 0
                category_count = len(asset_category.asset_set.filter(asset_status="In use"))
                data.append(category_count)

            labels = [category.asset_category_name for category in asset_categories]
            dataset = [
                {
                    "label": _("assets in use"),
                    "data": data,
                },
            ]

            response = {
                "labels": labels,
                "dataset": dataset,
                "message": _("Oops!! No Asset found..."),
                "emptyImageSrc": f"/{settings.STATIC_URL}images/ui/asset.png",
            }

            return JsonResponse(response)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AssetHistoryAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            previous_data = request.GET.urlencode() + "&returned_assets=True"
            asset_assignments = AssetHistoryFilter({"returned_assets": "True"}).qs.order_by("-id")
            data_dict = parse_qs(previous_data)
            get_key_instances(AssetAssignment, data_dict)
            asset_assignments = paginator_qry(asset_assignments, request.GET.get("page"))
            requests_ids = [instance.id for instance in asset_assignments.object_list]
            
            data = {
                "asset_assignments": AssetAssignmentSerializer(asset_assignments, many=True).data,
                "filter_dict": data_dict,
                "gp_fields": AssetHistoryReGroup().fields,
                "pd": previous_data,
                "requests_ids": json.dumps(requests_ids),
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class AssetHistorySingleAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, asset_id, *args, **kwargs):
        try:
            asset_assignment = get_object_or_404(AssetAssignment, id=asset_id)
        except AssetAssignment.DoesNotExist:
            return Response({'detail': 'Asset assignment not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        data = AssetAssignmentSerializer(asset_assignment).data
        requests_ids_json = request.GET.get("requests_ids")
        if requests_ids_json:
            requests_ids = json.loads(requests_ids_json)
            previous_id, next_id = closest_numbers(requests_ids, asset_id)
            data["requests_ids"] = requests_ids_json
            data["previous"] = previous_id
            data["next"] = next_id

        return Response(data, status=status.HTTP_200_OK)


from horilla.group_by import group_by_queryset
class AssetHistorySearchAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            previous_data = request.GET.urlencode()
            asset_assignments = AssetHistoryFilter(request.GET).qs.order_by("-id")
            asset_assignments = sortby(request, asset_assignments, "sortby")
            template = "asset_history/asset_history_list.html"
            field = request.GET.get("field")

            if field:
                asset_assignments = group_by_queryset(
                    asset_assignments, field, request.GET.get("page"), "page"
                )
                template = "asset_history/group_by.html"
                list_values = [entry["list"] for entry in asset_assignments]
                id_list = [instance.id for value in list_values for instance in value.object_list]
                requests_ids = json.dumps(list(id_list))
            else:
                asset_assignments = paginator_qry(asset_assignments, request.GET.get("page"))
                requests_ids = json.dumps([instance.id for instance in asset_assignments.object_list])

            data_dict = parse_qs(previous_data)
            get_key_instances(AssetAssignment, data_dict)

            data = {
                "asset_assignments": AssetAssignmentSerializer(asset_assignments, many=True).data,
                "filter_dict": data_dict,
                "field": field,
                "pd": previous_data,
                "requests_ids": requests_ids,
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class AssetTabAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, emp_id, *args, **kwargs):
        try:
            employee = Employee.objects.get(id=emp_id)
        except Employee.DoesNotExist:
            return Response({'detail': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        assets_requests = employee.requested_employee.all()
        assets = employee.allocated_employee.all()
        assets_ids = [instance.id for instance in assets] if assets else []

        data = {
            "assets": AssetAssignmentSerializer(assets, many=True).data,
            "requests": AssetRequestSerializer(assets_requests, many=True).data,
            "assets_ids": json.dumps(assets_ids),
            "employee": emp_id,
        }

        return Response(data, status=status.HTTP_200_OK)




class ProfileAssetTabAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, emp_id, *args, **kwargs):
        try:
            employee = Employee.objects.get(id=emp_id)
        except Employee.DoesNotExist:
            return Response({'detail': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        assets = employee.allocated_employee.all()
        assets_ids = [instance.id for instance in assets]

        data = {
            "assets": AssetAssignmentSerializer(assets, many=True).data,
            "assets_ids": json.dumps(assets_ids),
        }

        return Response(data, status=status.HTTP_200_OK)




class DashboardAssetRequestApproveAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            asset_requests = AssetRequest.objects.filter(
                asset_request_status="Requested", requested_employee_id__is_active=True
            )
            asset_requests = filtersubordinates(
                request,
                asset_requests,
                "asset.change_assetrequest",
                field="requested_employee_id",
            )
            requests_ids = [instance.id for instance in asset_requests]

            data = {
                "asset_requests": AssetRequestSerializer(asset_requests, many=True).data,
                "requests_ids": json.dumps(requests_ids),
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django import forms



from django.core.serializers.json import DjangoJSONEncoder


class ObjectDuplicateView(APIView):
    """
    API view to handle the duplication of an object instance in the database.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, obj_id, *args, **kwargs):
        """
        Handles GET requests to render the duplication form.
        """
        try:
            model = kwargs["model"]
            form_class = kwargs["form"]
            template = kwargs["template"]
            original_object = get_object_or_404(model, id=obj_id)
            form = form_class(instance=original_object)

            for field_name, field in form.fields.items():
                if isinstance(field, forms.CharField):
                    initial_value = field.initial or f"{form.initial.get(field_name, '')} (copy)"
                    form.initial[field_name] = initial_value
                    form.fields[field_name].initial = initial_value
            if hasattr(form.instance, "id"):
                form.instance.id = None

            form_data = {
                field_name: form[field_name].value() for field_name in form.fields
            }
            context = {
                kwargs.get("form_name", "form"): form_data,
                "obj_id": obj_id,
                "duplicate": True,
            }

            return Response(context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)

    def post(self, request, obj_id, *args, **kwargs):
        """
        Handles POST requests to save the duplicated object.
        """
        try:
            model = kwargs["model"]
            form_class = kwargs["form"]
            form = form_class(request.POST)

            if form.is_valid():
                new_object = form.save(commit=False)
                new_object.id = None
                new_object.save()
                return HttpResponse("<script>window.location.reload()</script>")
            else:
                return Response({"error": form.errors}, status=400)
        except Exception as error:
            return Response({"error": str(error)}, status=500)





class AssetCategorySearchFilterAPIView(APIView):
    """
    API View for handling search and filter operations for asset categories.
    """

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for asset category search and filter.
        Args:
            request (HttpRequest): Contains query parameters for filtering and pagination.
        Returns:
            Response: JSON response with paginated and filtered asset category data.
        """
        context = filter_pagination_asset_category(request)
        asset_categories = context.get('asset_categories')  # Adjust according to your function's return structure
        serialized_data = AssetCategorySerializer(asset_categories, many=True).data

        response_data = {
            "pagination": context.get('pagination_info', {}),
            "asset_categories": serialized_data,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class AssetRequestAllocationView(APIView):
    """
    API view for displaying a paginated list of asset allocation requests.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to display the paginated list of asset allocation requests.
        """
        try:
            context = filter_pagination_asset_request_allocation(request)

            # Convert context to a JSON-serializable format
            json_context = {
                key: (value if isinstance(value, dict) else str(value))
                for key, value in context.items()
            }

            return Response(json_context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest_framework.exceptions import ParseError

class OwnAssetIndividualAPIView(APIView):
    """
    API view to retrieve details of an individual own asset assignment with error handling.
    """

    def get(self, request, asset_id):
        try:
            # Fetch asset assignment object
            asset_assignment = AssetAssignment.objects.get(id=asset_id)
        except ObjectDoesNotExist:
            return Response(
                {"error": "Asset assignment with the provided ID does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError:
            return Response(
                {"error": "Invalid ID provided. ID must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            serializer = AssetAssignmentSerializer(asset_assignment)
            response_data = serializer.data

            requests_ids_json = request.GET.get("assets_ids")
            if requests_ids_json:
                try:
                    requests_ids = json.loads(requests_ids_json)
                    previous_id, next_id = closest_numbers(requests_ids, asset_id)
                    response_data.update({
                        "assets_ids": requests_ids,
                        "previous": previous_id,
                        "next": next_id,
                    })
                except json.JSONDecodeError:
                    raise ParseError("Invalid JSON format for 'assets_ids'.")
                except TypeError:
                    return Response(
                        {"error": "Invalid data type for 'assets_ids'. Expected a list of integers."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": "Validation error", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "An error occurred while processing the request.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class AssetRequestAllocationViewSearchFilter(APIView):
    """
    API view for handling search and filter functionality for the asset request allocation list.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to display the filtered and paginated asset request allocation list.
        """
        try:
            context = filter_pagination_asset_request_allocation(request)
            template = "request_allocation/asset_request_allocation_list.html"
            if (
                request.GET.get("request_field") != ""
                and request.GET.get("request_field") is not None
                or request.GET.get("allocation_field") != ""
                and request.GET.get("allocation_field") is not None
            ):
                template = "request_allocation/group_by.html"

            context["template"] = template

            # Convert context to a JSON-serializable format
            json_context = {
                key: (value if isinstance(value, dict) else str(value))
                for key, value in context.items()
            }

            return Response(json_context, status=200)
        except Exception as error:
            return Response({"error": str(error)}, status=500)



import pandas as pd



class AssetImportView(APIView):
    """
    API view for importing asset data from an uploaded Excel file.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles POST requests to import asset data from an uploaded Excel file.
        """
        try:
            file = request.FILES.get("asset_import")
            if file is None:
                return Response({"error": "No file provided"}, status=400)

            if file.content_type == "text/csv":
                try:
                    csv_asset_import(file)
                    return Response({"message": "Successfully imported Assets"}, status=200)
                except Exception as exception:
                    return Response({"error": f"CSV import error: {str(exception)}"}, status=500)
            elif file.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                try:
                    dataframe = pd.read_excel(file)
                    spreadsheetml_asset_import(dataframe)
                    return Response({"message": "Successfully imported Assets"}, status=200)
                except KeyError as exception:
                    return Response({"error": f"Excel import error: {str(exception)}"}, status=500)
            else:
                return Response({"error": "Invalid file type. Please upload a CSV or Excel file."}, status=400)
        except Exception as exception:
            return Response({"error": str(exception)}, status=500)

    def get(self, request):
        """
        Handles GET requests to render the asset import page.
        """
        try:
            return Response({"message": "Asset import page rendered."}, status=200)
        except Exception as exception:
            return Response({"error": str(exception)}, status=500)



from datetime import datetime, date
from io import BytesIO

import pandas as pd

class AssetExportExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        queryset_all = Asset.objects.all()
        if not queryset_all.exists():
            return Response(
                {"detail": "There are no assets to export."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = AssetExportFilter(request.data, queryset=queryset_all).qs

        data = {
            "asset_name": [],
            "asset_description": [],
            "asset_tracking_id": [],
            "asset_purchase_date": [],
            "asset_purchase_cost": [],
            "asset_category_id": [],
            "asset_status": [],
            "asset_lot_number_id": [],
        }
        fields_to_check = list(data.keys())

        for asset in queryset:
            for field in fields_to_check:
                value = getattr(asset, field)

                if isinstance(value, date):
                    emp = request.user.employee_get
                    info = EmployeeWorkInformation.objects.filter(employee_id=emp)
                    if info.exists():
                        employee_company = info.first().company_id
                        emp_company = Company.objects.filter(company=employee_company).first()
                        date_format = emp_company.date_format if emp_company else "MMM. D, YYYY"
                    else:
                        date_format = "MMM. D, YYYY"

                    start_date = datetime.strptime(str(value), "%Y-%m-%d").date()
                    for format_name, format_string in HORILLA_DATE_FORMATS.items():
                        if format_name == date_format:
                            value = start_date.strftime(format_string)
                            break

                data[field].append(value if value is not None else None)

        for key in data:
            data[key] = data[key] + [None] * (len(queryset) - len(data[key]))

        dataframe = pd.DataFrame(data)
        dataframe = dataframe.rename(
            columns={
                "asset_name": "Asset name",
                "asset_description": "Description",
                "asset_tracking_id": "Tracking id",
                "asset_purchase_date": "Purchase date",
                "asset_purchase_cost": "Purchase cost",
                "asset_category_id": "Category",
                "asset_status": "Status",
                "asset_lot_number_id": "Batch number",
            }
        )

        excel_buffer = BytesIO()
        dataframe.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        response = HttpResponse(
            excel_buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="assets.xlsx"'
        return response

    def get(self, request, format=None):
        return Response(
            {"detail": "Please use POST to export assets."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class AssetRequestTabAPIView(APIView):
    """
    API view to fetch asset request tab data for an employee.
    """

    def get(self, request, emp_id):
        try:
            # Fetch the employee by ID
            employee = Employee.objects.get(id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": "Employee with the provided ID does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid employee ID. ID must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # Fetch all asset requests for the employee
            assets_requests = employee.requested_employee.all()  # Assuming related_name is 'requested_employee'
            serializer = AssetRequestSerializer(assets_requests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"error": "Error retrieving asset requests for the employee."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred while fetching asset requests.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
