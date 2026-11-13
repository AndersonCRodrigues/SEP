from .access import PatientOnly
from django.views.generic import TemplateView


class PatientProfileView(PatientOnly, TemplateView):
    template_name = "patient/profile.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nome']=self.request.user.first_name
        context['sobrenome']=self.request.user.last_name
        context['cpf']=self.request.user.cpf
        context['email']=self.request.user.email
        context['telefone']=self.request.user.telefone
        context['data_nascimento']=self.request.user.data_nascimento
        context['logradouro']=self.request.user.logradouro
        context['number']=self.request.user.number
        context['complement']=self.request.user.complement
        context['bairro']=self.request.user.bairro
        context['municipality']=self.request.user.municipality
        context['city']=self.request.user.city
        context['state']=self.request.user.state
        context['cep']=self.request.user.cep
        context['is_accompanied']=self.request.user.patient.is_accompanied
        context['guardian_first_name']=self.request.user.patient.guardian_first_name
        context['guardian_last_name']=self.request.user.patient.guardian_last_name
        context['guardian_relationship']=self.request.user.patient.guardian_relationship
        return context