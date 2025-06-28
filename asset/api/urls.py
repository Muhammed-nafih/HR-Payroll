from django.urls import path
from . import views
from asset.models import Asset,AssetCategory
from asset.forms import AssetForm,AssetCategoryForm

urlpatterns = [
 
    path('asset-create-api/<int:asset_category_id>/', views.AssetCreation.as_view(), name='asset-create-api'),
    path('asset-report-add-api/<int:asset_id>/', views.AddAssetReport.as_view(), name='asset-report-add-api'),
    path('asset-update-api/<int:asset_id>/', views.AssetUpdate.as_view(), name='asset_update'), 
    path('asset-information-api/<int:asset_id>/', views.AssetInformation.as_view(), name='asset-information-api'),
    path('asset-delete-api/<int:asset_id>/', views.AssetDelete.as_view(), name='asset-delete-api'),
    path('asset-list-api/<int:cat_id>/', views.AssetList.as_view(), name='asset-list-api'),
    path('asset-category-create-api/', views.AssetCategoryCreation.as_view(), name='asset-category-create-api'),
    path('asset-category-update-api/<int:cat_id>/', views.AssetCategoryUpdate.as_view(), name='asset-category-update-api'),
    path('asset-category-delete-api/<int:cat_id>/', views.DeleteAssetCategory.as_view(), name='asset-category-delete-api'),
    path('asset-category-view-api/', views.AssetCategoryView.as_view(), name='asset-category-view-api'), 
    path('asset-request-create-api/', views.AssetRequestCreation.as_view(), name='asset-request-create-api'),
    path('asset-request-approve-api/<int:req_id>/', views.AssetRequestApprove.as_view(), name='asset-request-approve-api'),
    path('asset-request-reject-api/<int:req_id>/', views.AssetRequestReject.as_view(), name='asset-request-reject-api'),
    path('asset-allocate-create-api/', views.AssetAllocateCreation.as_view(), name='asset-allocate-create-api'),
    path('asset-allocate-return-request-api/<int:asset_id>/', views.AssetAllocateReturnRequest.as_view(), name='asset-allocate-return-request-api'),
    path('asset-allocate-return-api/<int:asset_id>/', views.AssetAllocateReturn.as_view(), name='asset-allocate-return-api'),
    path('asset-assignment-own-view-api/<int:asset_id>/', views.OwnAssetIndividualAPIView.as_view(), name='asset-assignment-own-view-api'),
    path('asset-request-individual-view-api/<int:asset_request_id>/', views.AssetRequestIndividualAPIView.as_view(), name='asset-request-individual-view-api'),
    path('asset-allocation-individual-view-api/<int:asset_allocation_id>/', views.AssetAllocationIndividualAPIView.as_view(), name='asset-allocation-individual-view-api'),
    path('asset-batch-number-create-api/', views.AssetBatchNumberCreationAPIView.as_view(), name='asset-batch-number-create-api'),
    path('asset-batch-view-api/', views.AssetBatchViewAPIView.as_view(), name='asset-batch-view-api'),
    path('asset-batch-update-api/<int:batch_id>/', views.AssetBatchUpdateAPIView.as_view(), name='asset-batch-update-api'),
    path('asset-batch-delete-api/<int:batch_id>/', views.AssetBatchNumberDeleteAPIView.as_view(), name='asset-batch-delete-api'),
    path('asset-batch-search-api/', views.AssetBatchNumberSearchAPIView.as_view(), name='asset-batch-search-api'),
    path('asset-count-update-api/', views.AssetCountUpdateAPIView.as_view(), name='asset-count-update-api'),
    path('asset-dashboard-api/', views.AssetDashboardAPIView.as_view(), name='asset-dashboard-api'),
    path('asset-available-chart-api/', views.AssetAvailableChartAPIView.as_view(), name='asset-available-chart-api'),
    path('asset-category-chart-api/', views.AssetCategoryChartAPIView.as_view(), name='asset-category-chart-api'),
    path('asset-history-api/', views.AssetHistoryAPIView.as_view(), name='asset-history-api'),
    path('asset-history-single-api/<int:asset_id>/', views.AssetHistorySingleAPIView.as_view(), name='asset-history-single-api'),
    path('asset-history-search-api/', views.AssetHistorySearchAPIView.as_view(), name='asset-history-search-api'),
    path('asset-tab-api/<int:emp_id>/', views.AssetTabAPIView.as_view(), name='asset-tab-api'),
    path('profile-asset-tab-api/<int:emp_id>/', views.ProfileAssetTabAPIView.as_view(), name='profile-asset-tab-api'),
    path('dashboard-asset-request-approve-api/', views.DashboardAssetRequestApproveAPIView.as_view(), name='dashboard-asset-request-approve-api'),
    path('duplicate-asset-api/<int:obj_id>/', views.ObjectDuplicateView.as_view(), name='duplicate-asset', kwargs={ 'model': Asset, 'form': AssetForm, 'form_name': 'asset_creation_form', 'template': 'asset/asset_creation.html' } ),
    path('asset-category-view-search-filter-api/', views. AssetCategorySearchFilterAPIView.as_view(), name='asset-category-view-search-filter-api'),
    path(
        "asset-category-duplicate-api/<int:obj_id>/",
        views.ObjectDuplicateView.as_view(),
        name="asset-category-duplicate-api",
        kwargs={
            "model": AssetCategory,
            "form": AssetCategoryForm,
            "form_name": "asset_category_form",
            "template": "category/asset_category_creation.html",
        },
    ),
    path('asset-request-allocation-view-api/', views.AssetRequestAllocationView.as_view(), name='asset-request-allocation-view-api'),
    path('individual-own-asset-api/<int:asset_id>/', views. OwnAssetIndividualAPIView.as_view(), name='individual-own-asset-api'),
    path('asset-request-allocation-view-search-filter-api/', views.AssetRequestAllocationViewSearchFilter.as_view(), name='asset-request-allocation-view-search-filter-api'),
    path('asset-import-api/', views.AssetImportView.as_view(), name='asset-import-api'),
    path('asset-export-excel-api/', views.AssetExportExcelView.as_view(), name='asset_export_excel'),
    path('asset-request-tab-api/<int:emp_id>/', views.AssetRequestTabAPIView.as_view(), name='asset-request-tab-api'),




]




