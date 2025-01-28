import os
import random

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect

from .models import Profile, CourseCategory, Application
from exams.models import Category, Exam, ExamResult, Test


@login_required
def kadr_choice_employee_view(request):
    if request.method == "GET":
        profiles = Profile.objects.filter(role__name="employee")
        course_categories = CourseCategory.objects.filter(is_active=True)
        return render(request, 'profiles/kadr/choice-employee.html',
                      {
                          "loc_categories": course_categories,
                          "profiles": profiles,
                      })
    elif request.method == "POST":
        loc_category = request.POST.get("loc_category_id")
        employee_id = request.POST.get("employee_id")
        employee = Profile.objects.get(id=employee_id)
        category = CourseCategory.objects.get(id=loc_category)
        Application.objects.create(profile=employee, curse_category=category)

    return render(request, 'profiles/kadr/check-completeness.html',
                  {"employee": employee, "loc_category": category})


@login_required
def kadr_check_documents_view(request, pk=None):
    if request.method == "GET":
        # loc_category = request.POST.get("loc_category_id")
        # employee_id = request.POST.get("employee_id")

        employee = Profile.objects.get(id=pk)
        category = CourseCategory.objects.get(id=1)

        return render(request, 'profiles/kadr/student-document-details.html',
                      {"employee": employee, "loc_category": category})


@login_required
def send_to_uel(request, pk):
    application = Application.objects.get(id=pk)
    application.status = 'under_review'
    application.save()
    return redirect('/profiles/kadr/students-list/')


@login_required
def show_document_view(request):
    doc_type = request.GET.get('doc_type')
    employee_id = request.GET.get('employee_id')

    employee = get_object_or_404(Profile, id=employee_id)

    doc_field_mapping = {
        'passport': employee.passport_pdf,
        'work_record': employee.work_record_pdf,
        'med_card': employee.med_card_pdf,
        'recommendation': employee.recommendation_pdf,
    }

    file_path = doc_field_mapping.get(doc_type)
    if file_path:
        try:
            return FileResponse(open(file_path.path, "rb"), content_type="application/pdf")
        except FileNotFoundError:
            raise Http404("File not found.")
    raise Http404("Invalid document type or file missing.")


@login_required
def delete_document_view(request):
    doc_type = request.GET.get('doc_type')
    employee_id = request.GET.get('employee_id')

    employee = get_object_or_404(Profile, id=employee_id)

    field_mapping = {
        "passport": "passport_pdf",
        "work_record": "work_record_pdf",
        "med_card": "med_card_pdf",
        "recommendation": "recommendation_pdf",
    }
    field = field_mapping.get(doc_type)
    if field:
        file_path = getattr(employee, field)
        setattr(employee, field, '')

        employee.save()
        os.remove(file_path.path)

        employee_applications = Application.objects.filter(status='ready_to_send', profile=employee)
        for application in employee_applications:
            application.status = 'docs_preparing'
            application.save()

    return redirect(f'/profiles/kadr/check-documents/{employee_id}')


@login_required
def accept_application_view(request):
    if request.method == 'POST':
        employee_id = request.POST.get("employee_id")
        employee = get_object_or_404(Profile, id=employee_id)
        file_field_mapping = {
            "passport": "passport_pdf",
            "work_record": "work_record_pdf",
            "med_card": "med_card_pdf",
            "recommendation": "recommendation_pdf",
        }
        for key, uploaded_file in request.FILES.items():
            model_field = file_field_mapping.get(key)
            if model_field:
                setattr(employee, model_field, uploaded_file)

        employee_applications = Application.objects.filter(status='docs_preparing', profile=employee)
        employee.save()

        for application in employee_applications:
            application.status = 'ready_to_send'
            application.save()

    return redirect('/profiles/kadr/students-list/')


class UelMainView(View):
    def get(self, request):
        statuses = ["under_review", "ready_to_exam", "confirmation", "approved", "returned"]
        applications = Application.objects.filter(status__in=statuses)
        return render(request, 'profiles/uel/students.html', {'applications': applications})


class UelStudentDocsView(View):
    def get(self, request, pk):
        application = Application.objects.get(id=pk)
        category = CourseCategory.objects.get(id=1)

        return render(request, 'profiles/uel/student-document-details.html',
                      {"employee": application.profile, "loc_category": category, "application": application})


class UelAllowExamView(View):
    def get(self, request, pk):
        application = Application.objects.get(id=pk)
        application.status = 'ready_to_exam'
        application.save()

        # category_id = request.POST.get('category_id')
        # profile_ids = request.POST.getlist('profile_ids')
        category_id = 3
        time_limit = 30
        question_limit = 30
        category = get_object_or_404(Category, id=category_id)
        employee = application.profile
        new_exam = Exam.objects.create(
            category=category,
            employee=employee,
            overseer=request.user.profile,
            time_limit=time_limit
        )
        # Ensure the question limit does not exceed available tests
        category_test_count = Test.objects.filter(category=category).count()
        if category_test_count == 0:
            # messages.error(request, "Ushbu kategoriya bo'yicha testlar mavjud emas.")
            return redirect('/profiles/operator/add-exam/')
        question_limit = min(question_limit, category_test_count)
        question_id_list = random.sample(
            list(Test.objects.filter(category=category).values_list('id', flat=True)),
            question_limit
        )
        for test_id in question_id_list:
            test = Test.objects.get(id=test_id)
            ExamResult.objects.create(test=test, exam=new_exam)
        # messages.success(request, message=f"Muvaffaqqiyatli saqlandi!")


        return redirect('/profiles/uel/students-list/')
