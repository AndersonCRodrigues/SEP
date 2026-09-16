from django.contrib.auth.decorators import login_required


@login_required
def enviar_email(request):
    if request.method == "POST":
        pass
