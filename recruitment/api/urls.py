from django.urls import path
from . import views
from recruitment.models import Stage, RecruitmentSurvey
from recruitment.forms import StageCreationForm,QuestionForm

urlpatterns = [


   
    path('recruitment-create-api/', views.RecruitmentcreateView.as_view(), name='recruitment-create-api'),
    path('recruitment-remove_manager-api/<int:mid>/<int:rid>/', views.RemoveRecruitmentManagerAPIView.as_view(), name='recruitment-remove_manager-api'),
    path('recruitment-view-api/', views.RecruitmentViewAPIView.as_view(), name='recruitment-view-api'),
    path('recruitment-search-api/', views.RecruitmentSearchAPIView.as_view(), name='recruitment-search-api'),
    path('recruitment-update-api/<int:rec_id>/', views.RecruitmentUpdateAPIView.as_view(), name='recruitment-update-api'),
  
    path('recruitment-delete-api/<int:rec_id>/', views.RecruitmentDeleteAPIView.as_view(), name='recruitment-delete-api'),
    path('recruitment-close-pipeline-api/<int:rec_id>/', views.RecruitmentClosePipelineView.as_view(), name='recruitment-close-pipeline-api'),
    path('recruitment-reopen-pipeline-api/<int:rec_id>/', views.RecruitmentReopenPipelineView.as_view(), name='recruitment-reopen-pipeline-api'),
    path('recruitment-pipeline-view-api/', views.RecruitmentPipelineView.as_view(), name='recruitment-pipeline-view-api'),
    path('filter-pipeline-api/', views.FilterPipelineView.as_view(), name='filter-pipeline-api'),
    path('stage-component-api/', views.StageComponentView.as_view(), name='stage-component-api'),
    path('update-candidate-stage-and-sequence-api/', views.UpdateCandidateStageAndSequenceAPI.as_view(), name='update-candidate-stage-and-sequence-api'),
    path('update-candidate-sequence-api/', views.UpdateCandidateSequenceAPI.as_view(), name='update-candidate-sequence-api'),
    path('recruitment-archive-api/<int:rec_id>/', views.RecruitmentArchiveView.as_view(), name='recruitment-archive-api'),
    path('change-candidate-stage-api/', views.ChangeCandidateStageAPI.as_view(), name='change-candidate-stage-api'),
    path('candidate-schedule-date-update-api/', views.CandidateScheduleDateUpdateView.as_view(), name='candidate-schedule-date-update-api'),
    path('stage-data-api/<int:rec_id>/', views.StageDataView.as_view(), name='stage_data'),
    path('add-candidate-api/', views.AddCandidateAPIView.as_view(), name='add-candidate-api'),
    path('stage-update-pipeline-api/<int:stage_id>/', views.StageUpdatePipelineView.as_view(), name='stage-update-pipeline-api'),
    path('stage-title-update-api/<int:stage_id>/', views.StageTitleUpdateView.as_view(), name='stage-title-update-api'),
    path('stage-delete-api/<int:stage_id>/', views.StageDeleteView.as_view(), name='stage-delete-api'),
    path('remove-stage-manager-api/<int:mid>/<int:sid>/', views.RemoveStageManagerAPIView.as_view(), name='remove-stage-manager-api'),
    path('candidate-create-api/', views.CandidateCreateView.as_view(), name='candidate-create-api'),
    path('recruitment-stages-api/<int:rec_id>/', views.RecruitmentStageAPIView.as_view(), name='recruitment-stages-api'),
    path('recruitment-candidate-stage-update-api/<int:cand_id>/', views.CandidateStageUpdateAPIView.as_view(), name='recruitment-candidate-stage-update-api'),
    path('note-update-individual-api/<int:note_id>/', views.NoteUpdateIndividualAPI.as_view(), name="note-update-individual-api"),
    path('note-delete-individual-api/<int:note_id>/', views.NoteDeleteIndividualAPI.as_view(), name='note-delete-individual-api'),
    path('send-mail-form-api/<int:cand_id>/', views.SendMailFormAPIView.as_view(), name='send-mail-form-api'),

    path('edit-interview-api/<int:interview_id>/', views.EditInterviewAPIView.as_view(), name='edit-interview-api'),
    path('schedule-interview-api/<int:cand_id>/', views.ScheduleInterviewAPIView.as_view(), name='schedule-interview-api'),
    path('delete-interview-api/<int:interview_id>/', views.DeleteInterviewAPIView.as_view(), name='delete-interview-api'),
    path('get-managers-api/', views.GetManagersAPIView.as_view(), name='get-managers-api'),
    path('interview-view-api/', views.InterviewViewAPIView.as_view(), name='interview-view-api'),
    path('interview-filter-api/', views.InterviewFilterAPIView.as_view(), name='interview-filter-api'),
    path('remove-interview-employee-api/<int:interview_id>/<int:employee_id>/', views.RemoveInterviewEmployeeAPIView.as_view(), name='remove-interview-employee-api'),
    path('candidate-export-api/', views.CandidateExportAPIView.as_view(), name='candidate-export-api'),
    path('candidate-conversion-api/<int:cand_id>/', views.CandidateConversionAPIView.as_view(), name='candidate-conversion-api'),
    path('delete-profile-image-api/<int:obj_id>/', views.DeleteProfileImageView.as_view(), name='delete-profile-image-api'),
    path('send-acknowledgement-api/', views.SendAcknowledgementAPI.as_view(), name='send-acknowledgement-api'),
    path('dashboard-hiring-api/', views.DashboardHiringAPIView.as_view(), name='dashboard-hiring-api'),
    path('dashboard-vacancy-api/', views.DashboardVacancyAPIView.as_view(), name='dashboard-vacancy-api'),
    path('candidate-status-api/', views.CandidateStatusAPIView.as_view(), name='candidate-status-api'),
    path('survey-preview-api/<str:title>/', views.SurveyPreviewAPIView.as_view(), name='survey-preview-api'),
    path('question-order-update-api/', views.QuestionOrderUpdateAPIView.as_view(), name='question-order-update-api'),
    path('survey-form-api/', views.SurveyFormAPIView.as_view(), name='survey-form-api'),
    #path('view-question-template-api/', views.ViewQuestionTemplateAPI.as_view(), name='view-question-template-api'),
    path('view-question-template-api/', views.ViewQuestionTemplateAPIView.as_view(), name='view-question-template-api'),
    path('skill-zone-api/', views.SkillZoneAPIView.as_view(), name='skill-zone-api'),

    path('update-question-template-api/<int:survey_id>/', views.UpdateQuestionTemplateAPI.as_view(), name='update-question-template-api'),
    path('create-question-template-api/', views.CreateQuestionTemplateAPI.as_view(), name='create-question-template-api'),
    path('delete-survey-question-api/<int:survey_id>/', views.DeleteSurveyQuestionAPIView.as_view(), name='delete-survey-question-api'),
    path('filter-survey-api/', views.FilterSurveyAPIView.as_view(), name='filter-survey-api'),
    path('single-survey-api/<int:survey_id>/', views.SingleSurveyAPI.as_view(), name='single-survey-api'),
    path('create-template-api/', views.CreateTemplateAPIView.as_view(), name='create-template-api'),
    path('delete-template-api/', views.DeleteTemplateAPIView.as_view(), name='delete-template-api'),
    path('question-add-api/', views.QuestionAddAPI.as_view(), name='question-add-api'),
    path('candidate-select-api/', views.CandidateSelectAPI.as_view(), name='candidate-select-api'),
    path('candidate-select-filter-api/', views.CandidateSelectFilterAPI.as_view(), name='candidate-select-filter-api'),
    #path('skill-zone-view-api/', views.SkillZoneAPIView.as_view(), name='skill-zone-view-api'),
    path('skill-zone-create-api/', views.SkillZoneCreateAPIView.as_view(), name='skill-zone-create-api'),
    path('skill-zone-update-api/<int:sz_id>/', views.SkillZoneUpdateAPIView.as_view(), name='skill-zone-update-api'),
    path('skill-zone-delete-api/<int:sz_id>/', views.SkillZoneDeleteAPIView.as_view(), name='skill-zone-delete-api'),
    path('skill-zone-archive-api/<int:sz_id>/', views.SkillZoneArchiveAPIView.as_view(), name='skill-zone-archive-api'),
    path('skill-zone-archive-api/<int:sz_id>/', views.SkillZoneArchiveAPIView.as_view(), name='skill-zone-archive-api'),
    path('skill-zone-filter-api/', views.SkillZoneFilterAPIView.as_view(), name='skill-zone-filter-api'),
    path('skill-zone-candidate-create-api/<int:sz_id>/', views.SkillZoneCandidateCreateAPIView.as_view(), name='skill-zone-candidate-create-api'),
    path('skill-zone-cand-edit-api/<int:sz_cand_id>/', views.SkillZoneCandEditAPIView.as_view(), name='skill-zone-cand-edit-api'),
    path('skill-zone-cand-filter-api/', views.SkillZoneCandFilterAPIView.as_view(), name='skill-zone-cand-filter-api'),
    path('skill-zone-cand-archive-api/<int:sz_cand_id>/', views.SkillZoneCandArchiveAPIView.as_view(), name='skill-zone-cand-archive-api'),
    path('skill-zone-cand-delete-api/<int:sz_cand_id>/', views.SkillZoneCandDeleteAPIView.as_view(), name='skill-zone-cand-delete-api'),
    path('get-template-api/<int:obj_id>/', views.GetTemplateAPIView.as_view(), name='get-template-api'),
    path('get-template-hint/', views.GetTemplateAPIView.as_view(), name='get-template-hint'),  
    path('create-candidate-rating-api/<int:cand_id>/', views.CreateCandidateRatingAPIView.as_view(), name='create-candidate-rating-api'),
    path('open-recruitments-api/', views.OpenRecruitmentsAPIView.as_view(), name='open-recruitments-api'),
    path('recruitment-details-api/<int:id>/', views.RecruitmentDetailsAPIView.as_view(), name='recruitment-details-api'),
    path('add-more-files-api/<int:id>/', views.AddMoreFilesAPIView.as_view(), name='add-more-files-api'),







    path('recruitment-pipeline-card-api/', views.RecruitmentPipelineCardView.as_view(), name='recruitment-pipeline-card-api'),
    path('recruitment-stage-update-api<int:stage_id>/', views.StageUpdatePipelineView.as_view(), name='recruitment-stage-update-api'),
    path('recruitments-update-pipeline-api/<int:rec_id>/', views.RecruitmentUpdatePipelineAPIView.as_view(), name='recruitments-update-pipeline-api'),
    path('recruitment-delete-api/<int:rec_id>/', views.RecruitmentDeletePipelineView.as_view(), name='recruitment-delete-api'),
    path('create-note-api/<int:cand_id>/', views.CreateNoteAPI.as_view(), name='add_note'),
    path('recruitment-add_note-api/<int:cand_id>/', views.AddNoteAPIView.as_view(), name='recruitment-add_note-api'),
    path('recruitment-view_note-api/<int:cand_id>/', views.ViewNoteAPIView.as_view(), name="recruitment-view_note-api"),
    path('recruitment-update-note-api/<int:note_id>/', views.UpdateNoteAPI.as_view(), name="recruitment-update-note-api"),
    path('recruitment-delete-note-api/<int:note_id>/', views.NoteDeleteAPIView.as_view(), name="recruitment-delete-note-api"),
    path('candidate-remark-delete-api/<int:note_id>/', views.CandidateRemarkDeleteAPIView.as_view(), name="candidate-remark-delete-api"),
    #path('candidate-schedule-date-update-api/', views.CandidateScheduleDateUpdateAPIView.as_view(), name="candidate-schedule-date-update-api"),
    path('stage-create-api/', views.CreateStageAPIView.as_view(), name='stage-create-api'),
    path('stage-view-api/', views.StageViewAPIView.as_view(), name='stage-view-api'),
    path('stage-search-api/', views.StageSearchAPIView.as_view(), name='stage-search-api'),
    path('stage-remove-manager-api/<int:mid>/<int:sid>/', views.RemoveStageManagerAPI.as_view(), name='remove-stage-manager-api'),
    path('stage-update-api/<int:stage_id>/', views.StageUpdateView.as_view(), name='stage-update-api'),
    path('stage-update-name-api/<int:stage_id>/', views.StageNameUpdateAPI.as_view(), name='stage-name-update-api'),
    path('stage-delete-api/<int:stage_id>/', views.StageDeleteAPIView.as_view(), name='stage-delete-api'),
    #path('candidate-create-api/', views.CandidateCreateAPIView.as_view(), name='candidate-create-api'),
    #path('recruitment-stages-api/<int:rec_id>/', views.RecruitmentStageAPIView.as_view(), name='recruitment-stages-api'),
    path('candidates-view-api/', views.CandidateViewAPIView.as_view(), name='candidates-view-api'),
    path('candidates-filter-api/', views.CandidateFilterAPIView.as_view(), name='candidates-filter-api'),
    path('candidates-search-api/', views.CandidateSearchAPIView.as_view(), name='candidates-search-api'),
    #path('candidates-card-api/', views.CandidateCardAPIView.as_view(), name='candidates-card-api'),
    path('candidates-view-individual-api/<int:cand_id>/', views.CandidateViewIndividualAPIView.as_view(), name='candidates-view-individual-api'),
    path('candidates-update-api/<int:cand_id>/', views.CandidateUpdateAPIView.as_view(), name='candidates-update-api'),
    path('candidates-delete-api/<int:cand_id>/', views.CandidateDeleteAPIView.as_view(), name='candidates-delete-api'),
    path('candidates-archive-api/<int:cand_id>/', views.CandidateArchiveAPIView.as_view(), name='candidates-archive-api'),
    path('candidates-bulk-delete-api/', views.CandidateBulkDeleteAPIView.as_view(), name='candidates-bulk-delete-api'),
    path('candidates-bulk-archive-api/', views.CandidateBulkArchiveAPIView.as_view(), name='candidates-bulk-archive-api'),
    path('candidates-history-api/<int:cand_id>/', views.CandidateHistoryAPIView.as_view(), name='candidate_history_api'),
    path('candidates-application-api/', views.ApplicationFormAPIView.as_view(), name='candidates-application-api'),
    path('candidates-send_mail-api/<int:cand_id>/', views.FormSendMailAPIView.as_view(), name='candidates-send_mail-api'),
    path('recruitment-dashboard-api/', views.DashboardView.as_view(), name='recruitment-dashboard-api'),
    path('dashboard-pipeline-api/', views.DashboardPipelineView.as_view(), name='dashboard-pipeline-api'),
    path('get-open-position-api/', views.GetOpenPositionAPIView.as_view(), name='get-open-position-api'),
    path('candidate-sequence-update-api/', views.CandidateSequenceUpdateAPIView.as_view(), name="candidate-sequence-update-api"),
    path('stage-sequence-update-api/', views.StageSequenceUpdateAPIView.as_view(), name="stage-sequence-update-api"),
    path(
        'rec-stage-duplicate-api/<int:obj_id>/',
        views.ObjectDuplicateAPIView.as_view(),
        name='rec-stage-duplicate-api',
        kwargs={
            "model": Stage,
            "form": StageCreationForm,
            "template": "stage/stage_form.html",
        }),
    path(
        "recruitment-survey-question-template-duplicate-api/<int:obj_id>/",
        views.ObjectDuplicateAPIView.as_view(),
        name="recruitment-survey-question-template-duplicate-api",
        kwargs={
            "model": RecruitmentSurvey,
            "form": QuestionForm,
            "template": "survey/template_form.html",
        },
    ),





]





