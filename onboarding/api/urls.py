from django.urls import path
from . import views

urlpatterns = [

    path('stage-creation-api/<int:obj_id>/', views.StageCreationAPIView.as_view(), name='stage-creation-api'),
    path('stage-update-api/<int:stage_id>/<int:recruitment_id>/', views.StageUpdateAPIView.as_view(), name='stage-update-api'),
    path('stage-delete-api/<int:stage_id>/', views.StageDeleteAPIView.as_view(), name='stage-delete-api'),
    path('task-create-api/', views.TaskCreationAPIView.as_view(), name='task-create-api'),
    path('task-update-api/<int:task_id>/', views.TaskUpdateAPIView.as_view(), name='task-update-api'),
    path('task-delete-api/<int:task_id>/', views.TaskDeleteAPIView.as_view(), name='task-delete-api'),
    path('candidate-create-api/', views.CandidateCreationAPIView.as_view(), name='candidate-create-api'),
    path('candidate-update-api/<int:obj_id>/', views.CandidateUpdateAPIView.as_view(), name='candidate-update-api'),
    path('candidates-view-api/', views.CandidatesViewAPIView.as_view(), name='candidates-view-api'),
    path('candidate-single-view-api/<int:id>/', views.CandidateSingleViewAPIView.as_view(), name='candidate-single-view-api'),
    path('candidate-delete-api/<int:obj_id>/', views.CandidateDeleteAPIView.as_view(), name='candidate_delete_api'),
    path('hired-candidates-view-api/', views.HiredCandidateAPIView.as_view(), name='hired-candidates-view-api'),
    path('candidate-filter-api/', views.CandidateFilterAPIView.as_view(), name='candidate-filter-api'),
    path('onboarding-view-api/', views.OnboardingView.as_view(), name='onboarding-view-api'),
    path('candidate-task-update-api/<int:taskId>/', views.CandidateTaskUpdateView.as_view(), name='candidate-task-update-api'),
    path('get-status-api/<int:task_id>/', views.GetStatusView.as_view(), name='get-status-api'),
    path('assign-task-api/<int:task_id>/', views.AssignTaskView.as_view(), name='assign-task-api'),
    path('candidate-stage-update-api/<int:candidate_id>/<int:recruitment_id>/', views.CandidateStageUpdateView.as_view(), name='candidate-stage-update-api'),
    path('candidate-stage-bulk-update-api/', views.CandidateStageBulkUpdateView.as_view(), name='candidate-stage-bulk-update-api'),
    path('candidate-task-bulk-update-api/', views.CandidateTaskBulkUpdateView.as_view(), name='candidate-task-bulk-update-api'),
    path('onboard-candidate-chart-api/', views.OnboardCandidateChartView.as_view(), name='onboard-candidate-chart-api'),
    path('update-joining-api/', views.UpdateJoiningView.as_view(), name='update-joining-api'),
    path('view_dashboard-api/', views.ViewDashboardView.as_view(), name='view_dashboard-api'),
    path('dashboard-stage-chart-api/', views.DashboardStageChartView.as_view(), name='dashboard-stage-chart-api'),
    path('candidate-sequence-update-api/', views.CandidateSequenceUpdateView.as_view(), name='candidate-sequence-update-api'),
    path('stage-sequence-update-api/', views.StageSequenceUpdateView.as_view(), name='stage-sequence-update-api'),
    path('stage-name-update-api/<int:stage_id>/', views.StageNameUpdateView.as_view(), name='stage-name-update-api'),
    path('task-report-api/', views.TaskReportView.as_view(), name='task-report-api'),
    path('candidate-tasks-status-api/', views.CandidateTasksStatusView.as_view(), name='candidate-tasks-status-api'),
    path('change-task-status-api/', views.ChangeTaskStatusView.as_view(), name='change-task-status-api'),
    path('candidate-select-api/', views.CandidateSelectView.as_view(), name='candidate-select-api'),
    path('candidate-select-filter-api/', views.CandidateSelectFilterView.as_view(), name='candidate-select-filter-api'),




]
