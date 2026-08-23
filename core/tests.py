from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from core.forms import EmployeeProfileForm
from core.models import Company, EmployeeProfile


class CsrfConfigurationTests(TestCase):
    def test_csrf_trusted_origins_cover_local_and_render(self):
        origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])

        self.assertTrue(any(origin.endswith('.onrender.com') for origin in origins))
        self.assertTrue(any('localhost' in origin for origin in origins))

    def test_proxy_ssl_header_is_configured_for_https(self):
        self.assertEqual(
            getattr(settings, 'SECURE_PROXY_SSL_HEADER', None),
            ('HTTP_X_FORWARDED_PROTO', 'https'),
        )


class EmployeeProfileDepartmentTests(TestCase):
    def test_employee_profile_has_department_field_and_form_includes_it(self):
        self.assertIsNotNone(EmployeeProfile._meta.get_field('department'))
        self.assertIn('department', EmployeeProfileForm().fields)


class LeaveBalanceTests(TestCase):
    def test_employee_profile_has_live_leave_balance_field(self):
        self.assertIsNotNone(EmployeeProfile._meta.get_field('leave_days_balance'))


class EmployeeUserCreationTests(TestCase):
    def test_hr_can_create_employee_user_account_and_assign_role(self):
        company, _ = Company.objects.get_or_create(name='Intellego Investment Consultants')
        hr_group = Group.objects.get_or_create(name='HR')[0]
        management_group = Group.objects.get_or_create(name='Management')[0]

        hr_user = User.objects.create_user(username='hr.manager', password='StrongPass123!')
        hr_user.groups.add(hr_group)
        hr_user.is_staff = True
        hr_user.save()

        client = Client()
        client.force_login(hr_user)

        response = client.post(
            reverse('core:profile-create'),
            {
                'company': company.pk,
                'employee_number': 'INT-1001',
                'full_name': 'Ava Ncube',
                'department': 'Operations',
                'job_title': 'Operations Lead',
                'leave_days_balance': 20,
                'dependents_count': 0,
                'email': 'ava.ncube@intellego-ic.com',
                'phone': '+263123456',
                'address': 'Harare',
                'emergency_contact': 'Emergency Contact',
                'user': '',
                'new_username': 'ava.ncube',
                'new_password': 'SecurePass123!',
                'user_role': 'employee',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        created_user = User.objects.get(username='ava.ncube')
        self.assertTrue(created_user.check_password('SecurePass123!'))
        self.assertFalse(created_user.groups.filter(pk=hr_group.pk).exists())
        self.assertFalse(created_user.groups.filter(pk=management_group.pk).exists())
        self.assertTrue(EmployeeProfile.objects.filter(user=created_user, full_name='Ava Ncube').exists())

        response = client.post(
            reverse('core:profile-create'),
            {
                'company': company.pk,
                'employee_number': 'INT-1002',
                'full_name': 'Ben Moyo',
                'department': 'Finance',
                'job_title': 'Accountant',
                'leave_days_balance': 14,
                'dependents_count': 1,
                'email': 'ben.moyo@intellego-ic.com',
                'phone': '+263765432',
                'address': 'Bulawayo',
                'emergency_contact': 'Emergency Contact',
                'user': '',
                'new_username': 'ben.moyo',
                'new_password': 'SecurePass123!',
                'user_role': 'management',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        managed_user = User.objects.get(username='ben.moyo')
        self.assertTrue(managed_user.groups.filter(pk=management_group.pk).exists())
        self.assertFalse(managed_user.is_staff)
