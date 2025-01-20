from django.contrib import admin
from django.urls import path, include
from .views import HomePageView

from django.conf import settings
from django.conf.urls.static import static


app_name = 'project'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('admin/', admin.site.urls),
    path('profiles/', include('profiles.urls')),
    path('exams/', include('exams.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

