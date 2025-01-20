from django.urls import path

from .views import start_exam_view, end_exam_view, exam_result_pdf_view, get_exam_deadline, examination_view


app_name = 'exams'

urlpatterns = [
    path('start-exam/<int:exam_id>', start_exam_view, name='start_exam'),
    path('cont-exam/<int:exam_id>', examination_view, name='cont_exam'),
    path('end-exam/<int:exam_id>', end_exam_view, name='end_exam'),

    path('get-deadline/<int:exam_id>/', get_exam_deadline, name='get_exam_deadline'),

    path('qr-result/<str:unique_id>', exam_result_pdf_view, name='exam_result_pdf'),
]
