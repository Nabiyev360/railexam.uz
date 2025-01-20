from django.utils import timezone
from .models import Exam


def finish_unfinished_exams(request):
    now = timezone.now()
    unfinished_exams = Exam.objects.filter(deadline__isnull=False, ended__isnull=True)

    for uf_exam in unfinished_exams:
        if uf_exam.deadline <= now:
            uf_exam.ended = uf_exam.deadline
            uf_exam.save()
    return {}
