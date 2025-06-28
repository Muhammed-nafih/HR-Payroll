from django.urls import path
from . import views




urlpatterns = [
    path('ticket-type-create-api/', views.TicketTypeCreate.as_view(), name='ticket-type-create-api'),
    path('ticket-type-update-api/<int:t_type_id>/', views.TicketTypeUpdate.as_view(), name='ticket-type-update-api'),
    path('ticket-type-views-api/', views.TicketTypeView.as_view(), name='ticket-type-views-api'),
    path('faq-category-api/', views.FAQCategoryView.as_view(), name='faq-category-api'),
    path('faq-category-create-api/', views.FAQCategoryCreate.as_view(), name='faq-category-create-api'),
    path('faq-category-update-api/<int:id>/', views.FAQCategoryUpdate.as_view(), name='faq-category-update-api'),
    path('faq-category-delete-api/<int:id>/', views.FAQCategoryDelete.as_view(), name='faq-category-delete-api'),
    path('faq-category-search-api/', views.FAQCategorySearch.as_view(), name='faq-category-search-api'),
    path('faq-view-api/<int:cat_id>/', views.FAQView.as_view(), name='aq-view-api'),
    path('faq-create-api/<int:cat_id>/', views.FAQCreate.as_view(), name='faq-create-api'),
    path('faq-update-api/<int:id>/', views.FAQUpdate.as_view(), name='faq_update'),
    path('faq-search-api/', views.FAQSearch.as_view(), name='faq-search-api'),
    path('faq-filter-api/<int:id>/', views.FAQFilterView.as_view(), name='faq-filter-api'),
    path('faq-delete-api/<int:id>/', views.FAQDelete.as_view(), name='faq-delete-api'),
    path('ticket-delete-api/<int:ticket_id>/', views.TicketDelete.as_view(), name='ticket-delete-api'),
    path('ticket-filter-api/', views.TicketFilterView.as_view(), name='ticket-filter-api'),
    path('tickets-individual-view-api/<int:ticket_id>/', views.TicketIndividualView.as_view(), name='tickets-individual-view-api'),
    path('tickets-update-tag-api/', views.TicketUpdateTagAPI.as_view(), name='tickets-update-tag-api'),
    path('create-tag-api/', views.CreateTagAPIView.as_view(), name='create-tag-api'),
    path('remove-tag-api/', views.RemoveTagAPIView.as_view(), name='remove-tag-api'),
    path('tickets-comment-create-api/<int:ticket_id>/', views.CommentCreateAPIView.as_view(), name='tickets-comment-create-api'),
    path('comment-edit-api/', views.CommentEditAPIView.as_view(), name='comment-edit-api'),
    path('comment-delete-api/<int:comment_id>/', views.CommentDeleteAPIView.as_view(), name='comment-delete-api'),
   
   
    path('faq-suggestion-api/', views.FAQSuggestionView.as_view(), name='faq-suggestion-api'),
    path('ticket-view-api/', views.TicketView.as_view(), name='ticket-view-api'),
    path('ticket-create-api/', views.TicketCreateView.as_view(), name='ticket-create-api'),
    path('ticket-update-api/<int:ticket_id>/', views.TicketUpdateView.as_view(), name='ticket-update-api'),
    path('ticket-archive-api/<int:ticket_id>/', views.TicketArchiveView.as_view(), name='ticket-archive-api'),
    path('change-ticket-status-api/<int:ticket_id>/', views.ChangeTicketStatusView.as_view(), name='change-ticket-status-api'),
    path('ticket-detail-api/<int:ticket_id>/', views.TicketDetailAPIView.as_view(), name='ticket-detail-api'),
    path('view-ticket-claim-request-api/<int:ticket_id>/', views.ViewTicketClaimRequestView.as_view(), name='view-ticket-claim-request-api'),
    path('ticket-change-raised-on-api/<int:ticket_id>/', views.TicketChangeRaisedOnView.as_view(), name='ticket-change-raised-on-api'),
    path('ticket-change-assignees-api/<int:ticket_id>/', views.TicketChangeAssigneesView.as_view(), name='ticket-change-assignees-api'),
    path('view-ticket-document-api/<int:doc_id>/', views.ViewTicketDocumentView.as_view(), name='view-ticket-document-api'),
    path('get-raised-on-api/', views.GetRaisedOnView.as_view(), name='get-raised-on-api'),
    #path('claim-ticket-api/<int:id>/', views.ClaimTicketView.as_view(), name='claim-ticket-api'),

    path('approve-claim-request-api/<int:req_id>/', views.ApproveClaimRequestView.as_view(), name='approve-claim-request-api'),
    path('tickets-select-filter-api/', views.TicketsSelectFilterView.as_view(), name='tickets-select-filter-api'),
    path('tickets-bulk-archive-api/', views.TicketsBulkArchiveView.as_view(), name='tickets_bulk_archive'),
    #path('tickets-bulk-delete-api/', views.TicketsBulkDeleteView.as_view(), name='tickets-bulk-delete-api'),
    path('create-department-manager-api/', views.DepartmentManagerCreateAPIView.as_view(), name='create-department-manager-api'),
    path('update-department-manager-api/<int:dep_id>/', views.UpdateDepartmentManagerView.as_view(), name='update-department-manager-api'),
    path('delete-department-manager-api/<int:dep_id>/', views.DeleteDepartmentManagerView.as_view(), name='delete-department-manager-api'),
    path('update-priority-api/<int:ticket_id>/', views.UpdatePriorityView.as_view(), name='update-priority-api'),
    path('ticket-type-delete-api/<int:t_type_id>/', views.TicketTypeDeleteView.as_view(), name='ticket-type-delete-api'),
    path('view-department-managers-api/', views.ViewDepartmentManagersView.as_view(), name='view-department-managers-api'),
    path('get-department-employees-api/', views.GetDepartmentEmployeesView.as_view(), name='get-department-employees-api'),
    path('delete-ticket-document-api/<int:doc_id>/', views.DeleteTicketDocumentView.as_view(), name='delete-ticket-document-api'),




    path('claim-ticket-api/<int:id>/', views.ClaimTicketView.as_view(), name='claim-ticket-api'),
    path('tickets-bulk-delete-api/', views.TicketsBulkDeleteView.as_view(), name='tickets-bulk-delete-api'),
    

]
