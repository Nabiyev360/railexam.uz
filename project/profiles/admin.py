from django.contrib import admin

from .models import Company, Role, Profile, CourseCategory, Application, Settings


admin.site.register(Company)
admin.site.register(Role)
admin.site.register(Profile)
admin.site.register(CourseCategory)
admin.site.register(Application)
admin.site.register(Settings)