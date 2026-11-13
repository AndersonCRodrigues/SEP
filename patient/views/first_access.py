from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from patient.forms import FirstAccessPasswordForm
from patient.services import set_first_access_password, validate_first_access_invitation


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("password", "password_confirmation"), name="dispatch")
class PatientFirstAccessView(View):
    template_name = "patient/first_access.html"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Referrer-Policy"] = "strict-origin"
        return response

    def get(self, request, token):
        try:
            validate_first_access_invitation(token)
        except ValidationError as error:
            return render(request, self.template_name, {"link_errors": error.messages}, status=400)

        return render(request, self.template_name, {"form": FirstAccessPasswordForm()})

    def post(self, request, token):
        form = FirstAccessPasswordForm(request.POST)

        if form.is_valid():
            try:
                set_first_access_password(token=token,password=form.cleaned_data["password"],password_confirmation=form.cleaned_data["password_confirmation"])
                messages.success(request, "Senha criada com sucesso! Faça login para acessar.")
                return redirect("login")  
            except ValidationError as error:
                form.add_error(None, error)

        return render(request, self.template_name, {"form": form}, status=400)