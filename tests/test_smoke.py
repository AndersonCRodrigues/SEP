from django.test import SimpleTestCase
from django.urls import reverse


class SmokeTest(SimpleTestCase):
    def test_admin_url_resolves(self):
        url = reverse("admin:index")

        self.assertEqual(url, "/admin/")
