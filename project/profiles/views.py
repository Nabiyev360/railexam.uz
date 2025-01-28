import os
import random
import secrets
import string

import face_recognition
import requests as req
from PIL import Image
from django.conf import settings
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
from .models import Role, Profile, Company, Application
from .services import check_employee


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        user_role = request.user.profile.role.name
        if user_role in ['overseer']:
            return redirect('/profiles/operator/dashboard/')
            # return render(request, 'profiles/operator-dashboard.html')
        elif user_role == 'employee':
            return redirect('/profiles/employee/')
        elif user_role == 'kadr':
            return redirect('/profiles/kadr/students-list/')
        elif user_role == 'uel_con':
            return redirect('/profiles/uel/students-list/')


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
    total_exams = Exam.objects.count()
    successful_exams = 0
    failed_exams = 0
    total_percentage = 0

    exams = Exam.objects.annotate(
        total_results=Count('results'),
        correct_results=Count('results', filter=Q(results__option_result='correct'))
    )

    for exam in exams:
        if exam.total_results > 0:
            correct_percentage = (exam.correct_results / exam.total_results) * 100
            total_percentage += correct_percentage
            if correct_percentage > 55:
                successful_exams += 1
            else:
                failed_exams += 1
        else:
            failed_exams += 1  # Exams with no results are considered failed

    average_percentage = total_percentage / total_exams if total_exams > 0 else 0

    last_five_exams = Exam.objects.filter(ended__isnull=False).order_by('-created')[:5]

    divider = total_exams
    if divider == 0:
        divider = 1

    context = {
        "total_exams": total_exams,
        "successful_exams": successful_exams,
        "failed_exams": failed_exams,
        "average_percentage": round(average_percentage, 2),
        "successful_percent": round(successful_exams/total_exams*100),
        "failed_percent": round(failed_exams/total_exams*100),
        "last_five_exams": last_five_exams
    }


    return render(request, 'profiles/operator/dashboard.html', context)


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
        return render(request, 'profiles/worker/login.html')

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
                    is_available = Company.objects.filter(name=company_name)
                    if is_available:
                        user_company = Company.objects.get(name=company_name)
                    else:
                        user_company = Company.objects.create(name=company_name)

                    new_profile = Profile.objects.create(
                        user=new_user, company=user_company, role=user_role,
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

                if True: # is_match
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

    return render(request, 'profiles/worker/exams.html', {
        "employee_all_exams": employee_exams,
        "employee_active_exams": employee_active_exams,
        "employee_ended_exams": employee_ended_exams,
    })


@login_required
def download_db_view(request):
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')

    if not os.path.exists(db_path):
        raise Http404("Database file not found.")
    elif not request.user.is_superuser:
        return JsonResponse({"message": "not allowed"})

    response = FileResponse(open(db_path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = 'attachment; filename="db.sqlite3"'
    return response
