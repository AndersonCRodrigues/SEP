from django import forms
from .models import AreaActing


class AreaAtuacaoForm(forms.ModelForm):
    class Meta:
        model = AreaActing
        fields = ["nome"]