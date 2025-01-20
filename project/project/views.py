from django.shortcuts import redirect
from django.views import View


class HomePageView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/profiles/')
        else:
            return redirect('/profiles/login/employee/')
