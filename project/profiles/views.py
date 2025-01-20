import os
import random
import secrets
import string

import face_recognition
import requests as req
from PIL import Image
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models import Count, Q, F, Case, When, Value, BooleanField
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from exams.models import Category, Test, Exam, ExamResult
from .models import Role, Profile, CourseCategory, Company, Application
from .services import check_employee


class DashboardView(View):
    def get(self, request):
        user_role = request.user.profile.role.name
        if user_role in ['overseer', 'root']:
            return render(request, 'profiles/operator-dashboard.html')
        elif user_role == 'employee':
            return redirect('/profiles/employee/')
        elif user_role == 'kadr':
            return redirect('/profiles/kadr/main/')


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
        for application in employee_applications:
            application.status = 'ready_to_send'
            application.save()
        employee.save()
    return redirect('/profiles/kadr/students-list/')


# @login_required
# def kadr_students_list_view(request):
#     kadr_company = request.user.profile.company
#
#     students = (
#         Profile.objects.filter(role__name='employee', company=kadr_company)
#         .annotate(
#             docs_completed=Case(
#                 When(
#                     passport_pdf='',
#                     work_record_pdf='',
#                     med_card_pdf='',
#                     recommendation_pdf='',
#                     then=Value(False),
#                 ),
#                 default=Value(True),
#                 output_field=BooleanField(),
#             )
#         )
#     )
#
#     return render(request, 'profiles/kadr/students.html', {'students': students})


@login_required
def kadr_students_list_view(request):
    applications = Application.objects.all()
    return render(request, 'profiles/kadr/students.html', {'applications': applications})


# Auths
class LoginView(View):
    def get(self, request):
        return render(request, 'profiles/operator-login.html')

    def post(self, request):
        username = request.POST.get('login')
        password = request.POST.get('password')

        is_exist = User.objects.filter(username=username)
        is_checked = False
        if is_exist:
            is_checked = is_exist.first().check_password(password)

        if is_exist and is_checked:
            authenticated_user = authenticate(request, username=username, password=password)
            login(request, authenticated_user)
            return redirect('/profiles/')
        else:
            messages.error(request, message="Login yoki parol xato kiritildi!")
            return redirect('/profiles/login/operator/')


def compare_faces(image1_path, image2_path, tolerance=0.6):
    image1 = face_recognition.load_image_file(image1_path)
    image2 = face_recognition.load_image_file(image2_path)
    try:
        encoding1 = face_recognition.face_encodings(image1)[0]
        encoding2 = face_recognition.face_encodings(image2)[0]
    except IndexError:
        return False
    results = face_recognition.compare_faces([encoding1], encoding2, tolerance=tolerance)
    return results[0]


def logout_view(request):
    if request.user.is_authenticated:
        user_role = request.user.profile.role.name
        logout(request)
        if user_role in ['overseer', 'root']:
            return redirect('/profiles/login/operator/')
    return redirect('/profiles/login/employee/')


# === OPERATOR ===
@login_required
def operator_main_view(request):
    return redirect('/profiles/operator/exams')


@login_required
def operator_exams_view(request):
    if request.method == 'GET':
        exams = Exam.objects.all().order_by('-id')
        return render(request, 'profiles/operator-exams.html', {'exams': exams})


@login_required
def operator_add_test_view(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        return render(request, 'profiles/operator-add-test.html', {'categories': categories})
    elif request.method == 'POST':
        category_id = request.POST.get('category_id')
        question = request.POST.get('question')
        correct_option = request.POST.get('correct_option')
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        category = Category.objects.get(id=category_id)

        new_test = Test.objects.create(category=category, question=question, correct_option=correct_option,
                                       option1=option1, option2=option2, option3=option3)

        messages.success(request, message=f"Test № {new_test.id} muvaffaqqiyatli saqlandi!")

        return redirect('/profiles/operator/add-test/')


@login_required
def operator_add_exam_view(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        profiles = Profile.objects.all()
        return render(request, 'profiles/operator-add-exam.html',
                      {'categories': categories, 'profiles': profiles}
                      )

    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        profile_ids = request.POST.getlist('profile_ids')
        time_limit = request.POST.get('time_limit')
        question_limit = int(request.POST.get('question_limit'))
        category = get_object_or_404(Category, id=category_id)
        for employee_id in profile_ids:
            employee = get_object_or_404(Profile, id=employee_id)
            new_exam = Exam.objects.create(
                category=category,
                employee=employee,
                overseer=request.user.profile,
                time_limit=time_limit
            )
            # Ensure the question limit does not exceed available tests
            category_test_count = Test.objects.filter(category=category).count()
            if category_test_count == 0:
                messages.error(request, "Ushbu kategoriya bo'yicha testlar mavjud emas.")
                return redirect('/profiles/operator/add-exam/')
            question_limit = min(question_limit, category_test_count)
            question_id_list = random.sample(
                list(Test.objects.filter(category=category).values_list('id', flat=True)),
                question_limit
            )
            for test_id in question_id_list:
                test = Test.objects.get(id=test_id)
                ExamResult.objects.create(test=test, exam=new_exam)
            messages.success(request, message=f"Muvaffaqqiyatli saqlandi!")
            return redirect('/profiles/operator/exams/')


@login_required
def operator_add_category_view(request):
    if request.method == 'POST':
        new_category_name = request.POST.get('new_category_name')
        Category.objects.create(name=new_category_name)
        messages.success(request, message=f"{new_category_name} kategoriyasi muvaffaqqiyatli saqlandi!")
        return redirect('/profiles/operator/add-test/')


@login_required
def operator_tests_view(request):
    tests = Test.objects.all()
    return render(request, 'profiles/operator-tests.html', {'tests': tests})


# === SIMPLE EMPLOYEE ===

@method_decorator(csrf_exempt, name='dispatch')
class LoginEmployeeView(View):
    def get(self, request):
        return render(request, 'profiles/login-employee.html')

    def post(self, request):
        pin = request.POST.get('pin')
        password = 'Pass2025'

        # Attempt to get user by pin
        user = User.objects.filter(username=pin).first()

        if user and user.check_password(password):
            authenticated_user = authenticate(request, username=pin, password=password)
            if authenticated_user.profile.image:
                image_3x4 = authenticated_user.profile.image
            else:
                return JsonResponse({"status": "error", "message": "Foydalanuvchi 3x4 rasmi bazada mavjud emas!"})
        else:
            try:
                res = check_employee(pin=pin)

                if res.status_code == 200:
                    data = res.json().get('worker')

                    # Ensure all required data is present
                    if not all([data.get('last_name'), data.get('first_name'), data.get('middle_name'),
                                data.get('position', {}).get('organization'), data.get('position', {}).get('name'),
                                data.get('job_date')]):
                        return JsonResponse(
                            {"status": "error", "message": "E-xodimda xodim ma'lumotlari to'liq emas!"})

                    fullname = f"{data.get('last_name')} {data.get('first_name')} {data.get('middle_name')}"
                    company_name = data.get('position').get('organization')
                    position = data.get('position').get('name')
                    seniority_railway = data.get('job_date')

                    # Create user and profile
                    new_user = User.objects.create_user(username=pin, password=password, first_name=fullname)
                    user_role = Role.objects.get(name='employee')
                    company = Company.objects.get(name=company_name)

                    new_profile = Profile.objects.create(
                        user=new_user, company=company, role=user_role,
                        fullname=fullname, pin=pin, position=position, seniority_railway=seniority_railway,
                    )

                    # Handle image saving
                    image_url = data.get('photo')
                    response = req.get(image_url)
                    response.raise_for_status()
                    filename = image_url.split('/')[-1]
                    image_content = ContentFile(response.content)
                    new_profile.image.save(filename, image_content, save=True)

                    authenticated_user = authenticate(request, username=pin, password=password)
                    image_3x4 = authenticated_user.profile.image

                else:
                    return JsonResponse(
                        {"status": "error", "message": "JShShIR xato kiritildi, tekshirib qaytadan tering!"})

            except req.RequestException:
                return JsonResponse({"status": "error", "message": "API bilan aloqa qilishda xatolik yuz berdi"})

        # Handle captured image for facial recognition
        captured_image = request.FILES.get('frame')
        if captured_image:
            try:
                img = Image.open(captured_image)
                characters = string.ascii_letters + string.digits
                image_name = ''.join(secrets.choice(characters) for _ in range(20))
                screen_path = f"media/log/{image_name}.jpg"
                img.save(screen_path)

                # Compare faces (assuming compare_faces is defined elsewhere)
                is_match = compare_faces(image_3x4, screen_path)
                os.remove(screen_path)

                if is_match:
                    login(request, authenticated_user)
                    return JsonResponse(
                        {"status": "success", "message": "Login successful", "redirect_url": "/profiles/employee/"})
                else:
                    return JsonResponse({"status": "error", "message": "Shaxs tasdiqdan o'tmadi"})
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"Xato yuz berdi: {str(e)}"})

        return JsonResponse({"status": "error", "message": "Shaxsiy rasm yuborilmagan."})

    # def post(self, request):
    #     pin = request.POST.get('pin')
    #     password = 'Pass2025'
    #
    #     user = User.objects.filter(username=pin).first()
    #     if user and user.check_password(password):
    #         authenticated_user = authenticate(request, username=pin, password=password)
    #         if authenticated_user.profile.image:
    #             image_3x4 = authenticated_user.profile.image
    #         else:
    #             return JsonResponse({"status": "error", "message": "Foydalanuvchi 3x4 rasmi bazada mavjud emas!"})
    #     else:
    #         try:
    #             res = check_employee(pin=pin)
    #             if res.status_code == 200:
    #                 data = res.json().get('worker')
    #                 if data is not None:
    #                     fullname = f"{data.get('last_name')} {data.get('first_name')} {data.get('middle_name')}"
    #                     company_name = data.get('position').get('organization')
    #                     position = data.get('position').get('name')
    #                     seniority_railway = data.get('job_date'),
    #                     if None in [fullname, company_name, position, seniority_railway]:
    #                         return JsonResponse(
    #                             {"status": "error", "message": "E-xodimda xodim ma'lumotlari to'liq emas!"}
    #                         )
    #                     new_user = User.objects.create_user(username=pin, password=password, first_name=fullname)
    #
    #                     user_role = Role.objects.get(name='employee')
    #                     company = Company.objects.get(name=company_name)
    #
    #                     new_profile = Profile.objects.create(user=new_user, company=company, role=user_role,
    #                                                          fullname=fullname, pin=pin, position=position,
    #                                                          seniority_railway=seniority_railway,
    #                                                          )
    #                     image_url = data.get('photo')
    #                     response = req.get(image_url)
    #                     response.raise_for_status()
    #                     filename = image_url.split('/')[-1]
    #                     image_content = ContentFile(response.content)
    #                     new_profile.image.save(filename, image_content, save=True)
    #
    #                     authenticated_user = authenticate(request, username=pin, password=password)
    #                     image_3x4 = authenticated_user.profile.image
    #
    #                 else:
    #                     return JsonResponse(
    #                         {"status": "error", "message": "JShShIR xato kiritildi, tekshirib qaytadan tering!"}
    #                     )
    #
    #         except req.RequestException:
    #             return JsonResponse(
    #                 {"status": "error", "message": "API bilan aloqa qilishda xatolik yuz berdi"}
    #             )
    #
    #     captured_image = request.FILES.get('frame')
    #     if captured_image:
    #         img = Image.open(captured_image)
    #         characters = string.ascii_letters + string.digits
    #         image_name = ''.join(secrets.choice(characters) for _ in range(20))
    #         screen_path = f"media/log/{image_name}.jpg"
    #         img.save(screen_path)
    #
    #         is_match = compare_faces(image_3x4, screen_path)
    #         os.remove(screen_path)
    #
    #         if is_match:
    #             login(request, authenticated_user)
    #             return JsonResponse({"status": "success", "message": "Login successful",
    #                                  "redirect_url": "/profiles/employee/"})
    #         else:
    #             return JsonResponse({"status": "error", "message": "Shaxs tasdiqdan o'tmadi"})


def employee_home_view(request):
    return redirect('/profiles/employee/exams/')


def employee_exams_view(request):
    employee_exams = Exam.objects.filter(employee=request.user.profile).annotate(
        count_corrects=Count('results', filter=Q(results__option_result='correct')),
        count_incorrect=Count('results', filter=Q(results__option_result='incorrect')),
        count_selected=F('count_corrects') + F('count_incorrect')
    ).order_by('-id')

    employee_active_exams = employee_exams.filter(ended__isnull=True)
    employee_ended_exams = employee_exams.filter(ended__isnull=False)

    return render(request, 'profiles/employee-exams.html', {
        "employee_all_exams": employee_exams,
        "employee_active_exams": employee_active_exams,
        "employee_ended_exams": employee_ended_exams,
    })
