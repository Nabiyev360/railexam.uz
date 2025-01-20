from django.contrib import admin

from .models import Test, Category, Exam, ExamResult


admin.site.register(Test)
admin.site.register(Category)
admin.site.register(Exam)
admin.site.register(ExamResult)
