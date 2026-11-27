from django.shortcuts import redirect

from .views import CustomLogoutView, ForcePasswordChangeView


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        if not request.user.must_change_password:
            return None

        view_class = getattr(view_func, "view_class", None)

        if view_class in (ForcePasswordChangeView, CustomLogoutView):
            return None

        return redirect("force_password_change")