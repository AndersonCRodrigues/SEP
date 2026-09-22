from django.views.generic import TemplateView

from .access import StudentOnly


class StudentFeedbacksView(StudentOnly, TemplateView):
    template_name = "student/feedbacks.html"
