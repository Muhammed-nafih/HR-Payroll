from django.urls import path
from . import views  




urlpatterns = [
    path('contract-tab/<int:obj_id>/', views.ContractTabView.as_view(), name='contract-tab-api'),
    path('employee-view/', views.EmployeeViewAPI.as_view(), name='employee-view-api'),
    path('shift-tab/<int:emp_id>/', views.ShiftTabAPIView.as_view(), name='shift-tab-api'),
    path('document-requests/<int:request_id>/', views.DocumentRequestAPIView.as_view(), name='document-request-detail'),  
    path('document-requests/', views.DocumentRequestAPIView.as_view(), name='document-request-create'),
    path('documents/update-title/<int:id>/', views.UpdateDocumentTitleAPIView.as_view(), name='update_document_title'),
    path('document/delete/<int:id>/', views.DocumentDeleteAPIView.as_view(), name='document-delete'),
    path('document-upload/<int:id>/', views.DocumentUploadAPIView.as_view(), name='document-upload'),
    path('documents/<int:id>/', views.DocumentUploadAPIView.as_view(), name='document-detail'),
    path('content-type/<str:file_extension>/', views.FileContentTypeView.as_view(), name='file-content-type'),
      
]
