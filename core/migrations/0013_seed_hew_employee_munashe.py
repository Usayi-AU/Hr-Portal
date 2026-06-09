from django.db import migrations


def seed_hew_employee(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    EmployeeProfile = apps.get_model('core', 'EmployeeProfile')
    User = apps.get_model('auth', 'User')

    from django.contrib.auth.hashers import make_password

    hew = Company.objects.filter(name='HEW Corporate Lawyers').first()
    if not hew:
        return

    username = 'Munashe'
    password = 'Gutu'
    employee_number = 'HEW-EMP-002'
    email = 'munashe@hew.local'

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_active': True,
            'password': make_password(password),
        },
    )
    if not created:
        user.email = email
        user.password = make_password(password)
        user.save(update_fields=['email', 'password'])

    profile, created = EmployeeProfile.objects.get_or_create(
        user=user,
        defaults={
            'employee_number': employee_number,
            'full_name': 'Munashe',
            'job_title': 'Employee',
            'email': email,
            'company': hew,
        },
    )
    if not created:
        profile.employee_number = employee_number
        profile.full_name = 'Munashe'
        profile.job_title = 'Employee'
        profile.email = email
        profile.company = hew
        profile.save()


def reverse_seed(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_create_companies_and_seed_users'),
    ]

    operations = [
        migrations.RunPython(seed_hew_employee, reverse_seed),
    ]
