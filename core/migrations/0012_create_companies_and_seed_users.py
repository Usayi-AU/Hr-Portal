from django.db import migrations, models
import django.db.models.deletion


def create_companies_and_users(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    EmployeeProfile = apps.get_model('core', 'EmployeeProfile')
    User = apps.get_model('auth', 'User')
    Group = apps.get_model('auth', 'Group')

    from django.contrib.auth.hashers import make_password

    # Create companies
    intellego, _ = Company.objects.get_or_create(name='Intellego Investment Consultants')
    hew, _ = Company.objects.get_or_create(name='HEW Corporate Lawyers')
    mmc, _ = Company.objects.get_or_create(name='MMC Capital')

    # Ensure HR group exists
    hr_group, _ = Group.objects.get_or_create(name='HR')

    # Helper to create a user and profile
    def create_user_with_profile(username, password, full_name, employee_number, company, is_hr=False, email=None, job_title='Employee'):
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
        else:
            user = User.objects.create(
                username=username,
                password=make_password(password),
                email=email or f"{username}@example.com",
                is_active=True,
            )
        if is_hr:
            hr_group.user_set.add(user)
        # Create or update profile
        profile, created = EmployeeProfile.objects.get_or_create(user_id=user.id, defaults={
            'employee_number': employee_number,
            'full_name': full_name,
            'job_title': job_title,
            'email': email or f"{username}@example.com",
        })
        if not created:
            profile.employee_number = employee_number
            profile.full_name = full_name
            profile.job_title = job_title
            profile.email = email or f"{username}@example.com"
        profile.company = company
        profile.save()
        return user, profile

    # Intellego employee
    create_user_with_profile('Runyararo', 'Madzivire', 'Runyararo', 'INT-001', intellego, is_hr=False, email='runyararo@intellego.local')
    # Intellego HR
    create_user_with_profile('Eustina', 'Nyasha', 'Eustina', 'INT-HR-001', intellego, is_hr=True, email='eustina@intellego.local', job_title='HR')

    # MMC employee
    create_user_with_profile('Zenzie', 'Muronzie', 'Zenzie', 'MMC-001', mmc, is_hr=False, email='zenzie@mmc.local')
    # MMC HR
    create_user_with_profile('Tamara', 'Tawuyanago', 'Tamara', 'MMC-HR-001', mmc, is_hr=True, email='tamara@mmc.local', job_title='HR')

    # HEW HR
    create_user_with_profile('Chipo', 'Chipo', 'Chipo', 'HEW-HR-001', hew, is_hr=True, email='chipo@hew.local', job_title='HR')


def reverse_func(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    User = apps.get_model('auth', 'User')
    # Do not delete users in reverse to avoid accidental removal; no-op
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_appraisaldocument'),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='employeeprofile',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.company'),
        ),
        migrations.RunPython(create_companies_and_users, reverse_func),
    ]
