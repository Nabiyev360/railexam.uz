import secrets
import string

from django.db import models
from profiles.models import Profile


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Test(models.Model):
    LEVELS = [
        ('easy', 'Oson'),
        ('middle', "O'rta"),
        ('hard', 'Qiyin'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    question = models.TextField()
    option1 = models.TextField()
    option2 = models.TextField()
    option3 = models.TextField()
    correct_option = models.TextField()
    difficulty = models.TextField(choices=LEVELS, default='middle')

    def __str__(self):
        return self.question


def generate_unique_id():
    """Generate a unique 20-character ID."""
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(secrets.choice(characters) for _ in range(15))


class Exam(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    employee = models.ForeignKey(Profile, on_delete=models.CASCADE)
    overseer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='overseer')
    time_limit = models.PositiveIntegerField(default=20)
    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(blank=True, null=True)
    deadline = models.DateTimeField(blank=True, null=True)
    ended = models.DateTimeField(blank=True, null=True)
    unique_id = models.CharField(max_length=255)
    pdf_short_path = models.CharField(max_length=255, blank=True, null=True)


    def __str__(self):
        return f"№ {self.id}"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            while True:
                new_id = generate_unique_id()
                if not Exam.objects.filter(unique_id=new_id).exists():
                    self.unique_id = new_id
                    break
        super().save(*args, **kwargs)


class ExamResult(models.Model):
    RESULT_CHOICES = [
        ('not_selected', "Tanlanmagan"),
        ('correct', "To'g'ri"),
        ('incorrect', "Noto'g'ri"),
    ]
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    option_result = models.CharField(choices=RESULT_CHOICES, default='not_selected', max_length=25)
    selected_option_index = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('exam', 'test')

    def __str__(self):
        return f"Result {self.id} | {self.test.question[:50]}... | {self.get_option_result_display()}"
