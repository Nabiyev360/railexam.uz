import os
import subprocess
import pypandoc

from io import BytesIO
from datetime import timedelta

import qrcode
from django.utils import timezone
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Cm
from docx2pdf import convert
# import pythoncom

from django.db.models import Count, Q, F
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import Exam, Test, ExamResult, Profile


def start_exam_view(request, exam_id):
    exam = Exam.objects.get(id=exam_id)
    now = timezone.now()
    if not exam.started:
        exam.started = now
        deadline = now + timedelta(minutes=exam.time_limit)
        exam.deadline = deadline
        exam.save()
    return redirect(f'/exams/cont-exam/{exam.id}')


def examination_view(request, exam_id):
    exam = Exam.objects.get(id=exam_id)
    exam_results = exam.results.all().order_by('id')
    context = {"exam": exam, "exam_results": exam_results}
    return render(request, 'exams/exam-page.html', context=context)


def select_option_view(request):
    pass


def end_exam_view(request, exam_id):
    exam = Exam.objects.get(id=exam_id)
    if request.method == "POST":
        for key, item in request.POST.items():
            if 'question_' in key:
                test_id = key.replace('question_', '')
                if test_id.isdigit():
                    test_id = int(test_id)
                    test = Test.objects.get(id=test_id)
                    result = ExamResult.objects.get(test=test, exam=exam)

                    selected_option_index = int(item[0])
                    result.selected_option_index = selected_option_index

                    selected_option_text = item[1:]
                    if test.correct_option == selected_option_text:
                        result.option_result = 'correct'
                    else:
                        result.option_result = 'incorrect'
                    result.save()
        exam.ended = timezone.now()
        exam.save()

    exam_results = exam.results.all().order_by('id')
    context = {"exam": exam, "exam_results": exam_results}
    # return render(request, 'exams/emp-results-page.html', context=context)
    return redirect(f'/exams/qr-result/{exam.unique_id}')


@login_required
def exam_result_pdf_view(request, unique_id):
    exam = get_object_or_404(Exam, unique_id=unique_id)
    if not exam.pdf_short_path:
        blank_path = 'files/result_list.docx'
        path = os.path.join(settings.BASE_DIR, blank_path)
        doc = DocxTemplate(path)
        exam = Exam.objects.filter(unique_id=unique_id).annotate(
            count_corrects=Count('results', filter=Q(results__option_result='correct')),
            count_incorrect=Count('results', filter=Q(results__option_result='incorrect'))
        ).first()
        count_tests = exam.results.count()
        percent_correct = int(exam.count_corrects / count_tests * 100) if count_tests > 0 else 0
        url = f"https://railexam.uz/exams/qr-result/{exam.unique_id}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        qr_image = BytesIO()
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img.save(qr_image, format="PNG")
        qr_image.seek(0)

        context = {
            "exam_id": exam.id,
            "fullname": exam.employee.fullname,
            "position": exam.employee.position,
            "category": exam.category.name,
            "time_limit": exam.time_limit,
            "started": exam.started.strftime("%d.%m.%Y %H:%M"),
            "ended": exam.ended.strftime("%d.%m.%Y %H:%M"),
            "overseer": exam.overseer.fullname,
            "count_tests": count_tests,
            "count_corrects": exam.count_corrects,
            "percent": percent_correct,
            'qr_code': InlineImage(doc, qr_image, width=Cm(4)),
            'photo': InlineImage(doc, exam.employee.image, width=Cm(3))
        }
        doc.render(context)

        word_path = os.path.join(settings.BASE_DIR, f"files/results/word/EXAM RESULT № {exam.id}.docx")
        pdf_short_path = f"files/results/pdf/EXAM RESULT № {exam.id}.pdf"
        pdf_path = os.path.join(settings.BASE_DIR, pdf_short_path)

        doc.save(word_path)

        # pythoncom.CoInitializeEx(0)
        # convert(word_path, pdf_path)

        try:
            pypandoc.convert_file(word_path, 'pdf', outputfile=pdf_path)
            exam.pdf_short_path = pdf_short_path
        except Exception as e:
            with open(word_path, 'rb') as file:
                response = HttpResponse(file.read(),
                                        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                response['Content-Disposition'] = f'attachment; filename="{exam.employee.fullname} {os.path.basename(word_path)}"'
                return response
        exam.save()
    else:
        pdf_path = os.path.join(settings.BASE_DIR, exam.pdf_short_path)
    try:
        with open(pdf_path, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="EXAM RESULT № {exam.id}.pdf"'
            return response
    except FileNotFoundError:
        return HttpResponseNotFound('PDF file not found')


def get_exam_deadline(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    try:
        print(timezone.now(), exam.deadline)
        return JsonResponse({
            "exam_id": exam_id,
            "server_now": timezone.now(),
            "deadline": exam.deadline,
        }, status=200)
    except Exception as e:
        return JsonResponse({
            "error": "An error occurred while fetching the deadline.",
            "details": str(e),
        }, status=500)
