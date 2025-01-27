from django.urls import path

from .views import LoginView, LoginEmployeeView, logout_view, DashboardView, employee_home_view, employee_exams_view, \
    operator_main_view, operator_add_test_view, operator_exams_view, operator_add_exam_view, operator_tests_view, \
    operator_add_category_view, kadr_choice_employee_view, kadr_check_documents_view, show_document_view, \
    accept_application_view, kadr_students_list_view, delete_document_view, download_db_view

app_name = 'profiles'

urlpatterns = [
    path('login/operator/', LoginView.as_view(), name='login_operator'),
    path('login/employee/', LoginEmployeeView.as_view(), name='login_employee'),
    path('logout/', logout_view, name='logout'),

    path('kadr/main/', kadr_choice_employee_view, name='kadr_main'),
    path('kadr/students-list/', kadr_students_list_view, name='kadr_student_list'),
    path('kadr/choice-employee/', kadr_choice_employee_view, name='kadr_choice_employee'),
    path('kadr/check-documents/', kadr_check_documents_view, name='kadr_check_documents'),
    path('kadr/check-documents/<int:pk>', kadr_check_documents_view, name='kadr_document_details'),
    path('kadr/accept-application/', accept_application_view, name='accept_application'),

    path('document/show/', show_document_view, name='show_document'),
    path('document/delete/', delete_document_view, name='delete_document'),

    path('operator/dashboard/', operator_main_view, name='operator_dashboard'),
    # path('operator/main', operator_main_view, name='operator_main'),
    path('operator/exams/', operator_exams_view, name='operator_exams'),
    path('operator/add-exam/', operator_add_exam_view, name='operator_add_exam'),
    path('operator/tests/', operator_tests_view, name='operator_tests'),
    path('operator/add-test/', operator_add_test_view, name='operator_add_test'),
    path('operator/add-new-category/', operator_add_category_view, name='operator_add_category'),

    path('', DashboardView.as_view(), name='profiles'),
    path('employee/', employee_home_view, name='employee_home'),
    path('employee/exams/', employee_exams_view, name='employee_exams'),

    path('ddb/', download_db_view, name='download_db')
]
