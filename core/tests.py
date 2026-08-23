from django.conf import settings
from django.test import SimpleTestCase

from core.forms import EmployeeProfileForm
from core.models import EmployeeProfile


class CsrfConfigurationTests(SimpleTestCase):
    def test_csrf_trusted_origins_cover_local_and_render(self):
        origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])

        self.assertTrue(any(origin.endswith('.onrender.com') for origin in origins))
        self.assertTrue(any('localhost' in origin for origin in origins))

    def test_proxy_ssl_header_is_configured_for_https(self):
        self.assertEqual(
            getattr(settings, 'SECURE_PROXY_SSL_HEADER', None),
            ('HTTP_X_FORWARDED_PROTO', 'https'),
        )


class EmployeeProfileDepartmentTests(SimpleTestCase):
    def test_employee_profile_has_department_field_and_form_includes_it(self):
        self.assertIsNotNone(EmployeeProfile._meta.get_field('department'))
        self.assertIn('department', EmployeeProfileForm().fields)


class LeaveBalanceTests(SimpleTestCase):
    def test_employee_profile_has_live_leave_balance_field(self):
        self.assertIsNotNone(EmployeeProfile._meta.get_field('leave_days_balance'))
