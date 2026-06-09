from django.contrib.auth.hashers import make_password
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_intellego_management_and_employees(apps, schema_editor):
    Company = apps.get_model('core', 'Company')
    EmployeeProfile = apps.get_model('core', 'EmployeeProfile')
    User = apps.get_model('auth', 'User')
    Group = apps.get_model('auth', 'Group')

    intellego = Company.objects.filter(name='Intellego Investment Consultants').first()
    if not intellego:
        return

    management_group, _ = Group.objects.get_or_create(name='Management')
    hr_group, _ = Group.objects.get_or_create(name='HR')

    employee_seed_data = [
        {
            'username': 'isaac.isaki',
            'password': 'Isaac@2026!',
            'full_name': 'Isaac Isaki',
            'employee_number': 'INT-MAN-001',
            'email': 'isaac.isaki@intellego-ic.com',
            'job_title': 'Management Team',
            'approver_username': 'welcome.mavingire',
            'is_management': True,
        },
        {
            'username': 'welcome.mavingire',
            'password': 'Welcome@2026!',
            'full_name': 'Welcome Mavingire',
            'employee_number': 'INT-MAN-002',
            'email': 'welcome.mavingire@intellego-ic.com',
            'job_title': 'Management Team',
            'approver_username': 'isaac.isaki',
            'is_management': True,
        },
        {
            'username': 'tatenda.mashonganyika',
            'password': 'Tatenda@2026!',
            'full_name': 'Tatenda Mashonganyika',
            'employee_number': 'INT-EMP-001',
            'email': 'tatenda.mashonganyika@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'tapiwa.muchengadare',
            'password': 'Tapiwa@2026!',
            'full_name': 'Tapiwa Muchengadare',
            'employee_number': 'INT-EMP-002',
            'email': 'tapiwa.muchengadare@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'tariro.baramasimbe',
            'password': 'Tariro@2026!',
            'full_name': 'Tariro Baramasimbe',
            'employee_number': 'INT-EMP-003',
            'email': 'tariro.baramasimbe@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'tinotenda.gakanje',
            'password': 'Tinotenda@2026!',
            'full_name': 'Tinotenda Gakanje',
            'employee_number': 'INT-EMP-004',
            'email': 'tinotenda.gakanje@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'edwin.tome',
            'password': 'Edwin@2026!',
            'full_name': 'Edwin Tome',
            'employee_number': 'INT-EMP-005',
            'email': 'edwin.tome@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'godfrey.mawere',
            'password': 'Godfrey@2026!',
            'full_name': 'Godfrey Mawere',
            'employee_number': 'INT-EMP-006',
            'email': 'godfrey.mawere@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'arnold.chuma',
            'password': 'Arnold@2026!',
            'full_name': 'Arnold Chuma',
            'employee_number': 'INT-EMP-007',
            'email': 'arnold.chuma@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'elvis.farirwi',
            'password': 'Elvis@2026!',
            'full_name': 'Elvis Farirwi',
            'employee_number': 'INT-EMP-008',
            'email': 'elvis.farirwi@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'isaac.isaki',
        },
        {
            'username': 'lazarus.masunungure',
            'password': 'Lazarus@2026!',
            'full_name': 'Lazarus Masunungure',
            'employee_number': 'INT-EMP-009',
            'email': 'lazarus.masunungure@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'welcome.mavingire',
        },
        {
            'username': 'runyararo.madzivire',
            'password': 'Runyararo@2026!',
            'full_name': 'Runyararo Madzivire',
            'employee_number': 'INT-001',
            'email': 'runyararo.madzivire@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'welcome.mavingire',
        },
        {
            'username': 'owen.namusi',
            'password': 'Owen@2026!',
            'full_name': 'Owen Namusi',
            'employee_number': 'INT-EMP-011',
            'email': 'owen.namusi@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'welcome.mavingire',
        },
        {
            'username': 'william.mavudzi',
            'password': 'William@2026!',
            'full_name': 'William Mavudzi',
            'employee_number': 'INT-EMP-012',
            'email': 'william.mavudzi@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'welcome.mavingire',
        },
        {
            'username': 'letwin.mutingwende',
            'password': 'Letwin@2026!',
            'full_name': 'Letwin Mutingwende',
            'employee_number': 'INT-EMP-013',
            'email': 'letwin.mutingwende@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'welcome.mavingire',
        },
        {
            'username': 'elizabeth.karombo',
            'password': 'Elizabeth@2026!',
            'full_name': 'Elizabeth Karombo',
            'employee_number': 'INT-EMP-014',
            'email': 'elizabeth.karombo@intellego-ic.com',
            'job_title': 'Employee',
            'approver_username': 'welcome.mavingire',
        },
        {
            'username': 'eustina.nyasha',
            'password': 'Eustina@2026!',
            'full_name': 'Eustina Nyasha',
            'employee_number': 'INT-HR-001',
            'email': 'eustina.nyasha@intellego-ic.com',
            'job_title': 'HR',
            'approver_username': 'welcome.mavingire',
            'is_hr': True,
        },
    ]

    for entry in employee_seed_data:
        profile = EmployeeProfile.objects.filter(employee_number=entry['employee_number']).select_related('user').first()
        if profile and profile.user:
            user = profile.user
        else:
            user = User.objects.filter(username=entry['username']).first()
            if user is None:
                user = User(username=entry['username'])

        user.username = entry['username']
        user.email = entry['email']
        user.password = make_password(entry['password'])
        user.is_active = True
        user.save()

        if entry.get('is_management'):
            management_group.user_set.add(user)
        if entry.get('is_hr'):
            hr_group.user_set.add(user)

    for entry in employee_seed_data:
        approver = User.objects.filter(username=entry.get('approver_username')).first()
        user = User.objects.filter(username=entry['username']).first()
        if not user:
            continue
        profile, _ = EmployeeProfile.objects.get_or_create(employee_number=entry['employee_number'], defaults={
            'user': user,
            'company': intellego,
            'full_name': entry['full_name'],
            'job_title': entry['job_title'],
            'email': entry['email'],
            'management_approver': approver,
        })
        profile.user = user
        profile.company = intellego
        profile.full_name = entry['full_name']
        profile.job_title = entry['job_title']
        profile.email = entry['email']
        profile.management_approver = approver
        profile.save()


def reverse_seed(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_seed_hew_employee_munashe'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='employeeprofile',
            name='management_approver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_employee_profiles', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='management_comment',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_leave_requests', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(seed_intellego_management_and_employees, reverse_seed),
    ]
