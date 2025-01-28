from django.contrib.auth.models import User
from django.db import models



class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=100)
    position = models.CharField(max_length=255)
    pin = models.CharField(max_length=20)
    image = models.ImageField(null=True, blank=True, upload_to='3x4')
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    tabel_num = models.CharField(max_length=20, null=True, blank=True)
    seniority_railway = models.DateField(null=True, blank=True)
    seniority_position = models.DateField(null=True, blank=True)
    passport_pdf = models.FileField(upload_to=r"documents", null=True, blank=True)
    work_record_pdf = models.FileField(upload_to=r"documents", null=True, blank=True)
    med_card_pdf = models.FileField(upload_to=r"documents", null=True, blank=True)
    recommendation_pdf = models.FileField(upload_to=r"documents", null=True, blank=True)

    def __str__(self):
        return self.fullname + ' | ' + self.role.name


class CourseCategory(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Application(models.Model):
    status_choices = (
        ('docs_preparing', 'Hujjatlar tayyorlanmoqda'),
        ('ready_to_send', 'Taqdim qilishga tayyor'),
        ('under_review', "Ko'rib chiqishga yuborilgan"),
        ('ready_to_exam', 'Imtihonga ruxsat'),
        ('confirmation', 'Tasdiqlashda'),
        ('approved', 'Tasdiqlangan'),
        ('returned', 'Qayta ishlashga yuborilgan'),
    )

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    curse_category = models.ForeignKey(CourseCategory, on_delete=models.CASCADE)
    status = models.CharField(max_length=255, choices=status_choices, default='ready_to_send')

    def __str__(self):
        return self.profile.fullname

    def save(self, *args, **kwargs):
        profile = self.profile
        if not all([profile.passport_pdf, profile.work_record_pdf, profile.med_card_pdf, profile.recommendation_pdf]):
            self.status = 'docs_preparing'
        super().save(*args, **kwargs)


class Settings(models.Model):
    key = models.CharField(max_length=255)
    value = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.key
