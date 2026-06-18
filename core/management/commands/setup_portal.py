"""
Management command: setup_portal

Idempotent bootstrap command that:
  1. Creates the admin superuser (username: admin, password from ADMIN_PASSWORD
     env var or defaults to "admin123").
  2. Creates HR, Employee, and Management auth groups.
  3. Creates three demo companies.
  4. Creates demo EmployeeProfile records (one HR user + several employees per
     company) with linked Django User accounts.
  5. Creates demo LeaveRequest records.
  6. Creates demo TrainingProgram records.
  7. Creates demo PolicyDocument records.
  8. Creates demo WeeklyMenuItem records.
  9. Creates demo FoodOrder records.

Run with:
    python manage.py setup_portal
"""

import os
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Company,
    EmployeeProfile,
    FoodOrder,
    LeaveRequest,
    PolicyDocument,
    TrainingProgram,
    WeeklyMenuItem,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_user(username, password, email, is_staff=False, is_superuser=False):
    """Return (user, created).  Always syncs password / flags on existing users."""
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_active": True,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
        },
    )
    if not created:
        # Keep flags and email in sync on re-runs
        user.email = email
        user.is_staff = is_staff
        user.is_superuser = is_superuser
    user.set_password(password)
    user.save()
    return user, created


def _get_or_create_profile(user, employee_number, full_name, job_title, email, company, approver=None):
    """Return (profile, created).  Always syncs mutable fields on re-runs."""
    profile, created = EmployeeProfile.objects.get_or_create(
        employee_number=employee_number,
        defaults={
            "user": user,
            "full_name": full_name,
            "job_title": job_title,
            "email": email,
            "company": company,
            "management_approver": approver,
        },
    )
    if not created:
        profile.user = user
        profile.full_name = full_name
        profile.job_title = job_title
        profile.email = email
        profile.company = company
        if approver is not None:
            profile.management_approver = approver
        profile.save()
    return profile, created


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Bootstrap the HR Portal: create admin user, groups, demo companies, "
        "employees, leave requests, training programmes, policies, and food data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-demo-data",
            action="store_true",
            help="Create admin / groups only; skip all demo records.",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== HR Portal Setup ==="))

        self._create_superuser()
        groups = self._create_groups()
        companies = self._create_companies()

        if not options["skip_demo_data"]:
            users_by_company = self._create_employees(companies, groups)
            self._create_leave_requests(users_by_company)
            self._create_training_programs()
            self._create_policy_documents(companies)
            self._create_weekly_menu_items(companies)
            self._create_food_orders(companies, users_by_company)

        self.stdout.write(self.style.SUCCESS("\n✔  Setup complete."))

    # ------------------------------------------------------------------
    # Step 1 – Superuser
    # ------------------------------------------------------------------

    def _create_superuser(self):
        password = os.environ.get("ADMIN_PASSWORD", "admin123")
        user, created = _get_or_create_user(
            username="admin",
            password=password,
            email="admin@hrportal.local",
            is_staff=True,
            is_superuser=True,
        )
        label = "Created" if created else "Updated"
        self.stdout.write(f"  {label} superuser: admin")

    # ------------------------------------------------------------------
    # Step 2 – Groups
    # ------------------------------------------------------------------

    def _create_groups(self):
        groups = {}
        for name in ("HR", "Employee", "Management"):
            group, created = Group.objects.get_or_create(name=name)
            label = "Created" if created else "Found"
            self.stdout.write(f"  {label} group: {name}")
            groups[name] = group
        return groups

    # ------------------------------------------------------------------
    # Step 3 – Companies
    # ------------------------------------------------------------------

    def _create_companies(self):
        company_names = [
            "Intellego Investment Consultants",
            "HEW Corporate Lawyers",
            "MMC Capital",
        ]
        companies = {}
        for name in company_names:
            company, created = Company.objects.get_or_create(name=name)
            label = "Created" if created else "Found"
            self.stdout.write(f"  {label} company: {name}")
            companies[name] = company
        return companies

    # ------------------------------------------------------------------
    # Step 4 – Employees
    # ------------------------------------------------------------------

    def _create_employees(self, companies, groups):
        """
        Returns a dict keyed by company name whose values are lists of
        (user, profile) tuples for all non-HR employees in that company.
        """
        hr_group = groups["HR"]
        employee_group = groups["Employee"]
        management_group = groups["Management"]

        # Seed data: (username, password, full_name, emp_no, job_title, email, role)
        # role: "hr" | "management" | "employee"
        seed = {
            "Intellego Investment Consultants": [
                ("eustina.nyasha",    "Eustina@2026!",    "Eustina Nyasha",         "INT-HR-001",  "HR Officer",        "eustina.nyasha@intellego-ic.com",    "hr"),
                ("isaac.isaki",       "Isaac@2026!",      "Isaac Isaki",            "INT-MAN-001", "Managing Director", "isaac.isaki@intellego-ic.com",       "management"),
                ("welcome.mavingire", "Welcome@2026!",    "Welcome Mavingire",      "INT-MAN-002", "Operations Manager","welcome.mavingire@intellego-ic.com", "management"),
                ("tatenda.mashonganyika", "Tatenda@2026!", "Tatenda Mashonganyika", "INT-EMP-001", "Analyst",           "tatenda.mashonganyika@intellego-ic.com", "employee"),
                ("tapiwa.muchengadare",   "Tapiwa@2026!",  "Tapiwa Muchengadare",  "INT-EMP-002", "Analyst",           "tapiwa.muchengadare@intellego-ic.com",   "employee"),
                ("tariro.baramasimbe",    "Tariro@2026!",  "Tariro Baramasimbe",   "INT-EMP-003", "Consultant",        "tariro.baramasimbe@intellego-ic.com",    "employee"),
                ("tinotenda.gakanje",     "Tinotenda@2026!", "Tinotenda Gakanje",  "INT-EMP-004", "Consultant",        "tinotenda.gakanje@intellego-ic.com",     "employee"),
                ("edwin.tome",            "Edwin@2026!",   "Edwin Tome",           "INT-EMP-005", "Accountant",        "edwin.tome@intellego-ic.com",            "employee"),
            ],
            "HEW Corporate Lawyers": [
                ("chipo.hew",    "Chipo@2026!",   "Chipo Moyo",       "HEW-HR-001",  "HR Officer",  "chipo@hew.local",    "hr"),
                ("munashe.gutu", "Munashe@2026!", "Munashe Gutu",     "HEW-EMP-001", "Paralegal",   "munashe@hew.local",  "employee"),
                ("rudo.hew",     "Rudo@2026!",    "Rudo Chikwanda",   "HEW-EMP-002", "Associate",   "rudo@hew.local",     "employee"),
                ("tafara.hew",   "Tafara@2026!",  "Tafara Mupfumi",   "HEW-EMP-003", "Receptionist","tafara@hew.local",   "employee"),
            ],
            "MMC Capital": [
                ("tamara.mmc",  "Tamara@2026!", "Tamara Tawuyanago", "MMC-HR-001",  "HR Officer",  "tamara@mmc.local",  "hr"),
                ("zenzie.mmc",  "Zenzie@2026!", "Zenzie Muronzie",   "MMC-EMP-001", "Trader",      "zenzie@mmc.local",  "employee"),
                ("farai.mmc",   "Farai@2026!",  "Farai Choto",       "MMC-EMP-002", "Analyst",     "farai@mmc.local",   "employee"),
                ("simba.mmc",   "Simba@2026!",  "Simba Dube",        "MMC-EMP-003", "Risk Officer","simba@mmc.local",   "employee"),
            ],
        }

        # We need a management approver per company; collect them first.
        approvers = {}  # company_name -> User (first management user, or HR user)

        users_by_company = {}  # company_name -> [(user, profile), ...]

        for company_name, entries in seed.items():
            company = companies[company_name]
            company_users = []

            # First pass: create users
            user_map = {}
            for username, password, full_name, emp_no, job_title, email, role in entries:
                is_staff = role == "hr"
                user, created = _get_or_create_user(username, password, email, is_staff=is_staff)
                label = "Created" if created else "Updated"
                self.stdout.write(f"    {label} user: {username} ({role})")

                # Group membership
                if role == "hr":
                    hr_group.user_set.add(user)
                elif role == "management":
                    management_group.user_set.add(user)
                    if company_name not in approvers:
                        approvers[company_name] = user
                else:
                    employee_group.user_set.add(user)

                user_map[username] = (user, full_name, emp_no, job_title, email, role)

            # Fallback approver: use HR user if no management user exists
            if company_name not in approvers:
                for username, _, _, _, _, role in entries:
                    if role == "hr":
                        approvers[company_name] = user_map[username][0]
                        break

            # Second pass: create profiles (approver now known)
            approver = approvers.get(company_name)
            for username, (user, full_name, emp_no, job_title, email, role) in user_map.items():
                profile, created = _get_or_create_profile(
                    user=user,
                    employee_number=emp_no,
                    full_name=full_name,
                    job_title=job_title,
                    email=email,
                    company=company,
                    approver=approver if role == "employee" else None,
                )
                label = "Created" if created else "Updated"
                self.stdout.write(f"    {label} profile: {full_name} ({emp_no})")

                if role == "employee":
                    company_users.append((user, profile))

            users_by_company[company_name] = company_users

        return users_by_company

    # ------------------------------------------------------------------
    # Step 5 – Leave Requests
    # ------------------------------------------------------------------

    def _create_leave_requests(self, users_by_company):
        today = date.today()

        leave_templates = [
            {
                "leave_type": LeaveRequest.LeaveType.VACATION,
                "start_offset": -30,
                "end_offset": -21,
                "reason": "Annual family vacation.",
                "status": LeaveRequest.Status.APPROVED,
                "requested_days": 10,
                "total_leave_days_accrued": 20,
                "total_leave_days_taken": 10,
                "leave_days_balance": 10,
            },
            {
                "leave_type": LeaveRequest.LeaveType.SICK,
                "start_offset": -10,
                "end_offset": -8,
                "reason": "Medical appointment and recovery.",
                "status": LeaveRequest.Status.APPROVED,
                "requested_days": 3,
                "total_leave_days_accrued": 10,
                "total_leave_days_taken": 3,
                "leave_days_balance": 7,
            },
            {
                "leave_type": LeaveRequest.LeaveType.STUDY,
                "start_offset": 7,
                "end_offset": 11,
                "reason": "Professional certification exam preparation.",
                "status": LeaveRequest.Status.PENDING,
                "requested_days": 5,
                "total_leave_days_accrued": 5,
                "total_leave_days_taken": 0,
                "leave_days_balance": 5,
            },
            {
                "leave_type": LeaveRequest.LeaveType.COMPASSIONATE,
                "start_offset": -5,
                "end_offset": -3,
                "reason": "Bereavement – immediate family.",
                "status": LeaveRequest.Status.APPROVED,
                "requested_days": 3,
                "total_leave_days_accrued": 3,
                "total_leave_days_taken": 3,
                "leave_days_balance": 0,
            },
            {
                "leave_type": LeaveRequest.LeaveType.AWAY_ON_BUSINESS,
                "start_offset": 14,
                "end_offset": 16,
                "reason": "Client site visit.",
                "status": LeaveRequest.Status.FORWARDED,
                "requested_days": 3,
                "total_leave_days_accrued": 0,
                "total_leave_days_taken": 0,
                "leave_days_balance": 0,
            },
        ]

        created_count = 0
        for company_name, employee_list in users_by_company.items():
            for idx, (user, profile) in enumerate(employee_list):
                template = leave_templates[idx % len(leave_templates)]
                start = today + timedelta(days=template["start_offset"])
                end = today + timedelta(days=template["end_offset"])

                # Idempotency: skip if a request of this type already exists for the profile
                if LeaveRequest.objects.filter(
                    employee=profile, leave_type=template["leave_type"]
                ).exists():
                    continue

                LeaveRequest.objects.create(
                    employee=profile,
                    leave_type=template["leave_type"],
                    start_date=start,
                    end_date=end,
                    reason=template["reason"],
                    status=template["status"],
                    requested_days=template["requested_days"],
                    total_leave_days_accrued=template["total_leave_days_accrued"],
                    total_leave_days_taken=template["total_leave_days_taken"],
                    leave_days_balance=template["leave_days_balance"],
                    qualifies_for_leave="yes",
                )
                created_count += 1

        self.stdout.write(f"  Created {created_count} leave request(s).")

    # ------------------------------------------------------------------
    # Step 6 – Training Programs
    # ------------------------------------------------------------------

    def _create_training_programs(self):
        today = date.today()
        programs = [
            {
                "title": "Workplace Health & Safety Induction",
                "description": (
                    "Covers emergency procedures, fire safety, first-aid basics, "
                    "and ergonomic best practices for all staff."
                ),
                "start_date": today - timedelta(days=60),
                "end_date": today - timedelta(days=59),
            },
            {
                "title": "Anti-Money Laundering (AML) Compliance",
                "description": (
                    "Mandatory annual refresher on AML regulations, red-flag "
                    "indicators, and internal reporting obligations."
                ),
                "start_date": today - timedelta(days=30),
                "end_date": today - timedelta(days=29),
            },
            {
                "title": "Leadership & People Management",
                "description": (
                    "Practical workshop for team leads covering performance "
                    "conversations, delegation, and conflict resolution."
                ),
                "start_date": today + timedelta(days=14),
                "end_date": today + timedelta(days=15),
            },
            {
                "title": "Data Privacy & GDPR Awareness",
                "description": (
                    "Overview of data-protection obligations, employee rights, "
                    "and secure data-handling procedures."
                ),
                "start_date": today + timedelta(days=30),
                "end_date": today + timedelta(days=30),
            },
            {
                "title": "Microsoft Excel – Advanced Analytics",
                "description": (
                    "Hands-on training covering pivot tables, Power Query, "
                    "and dashboard creation for business reporting."
                ),
                "start_date": today + timedelta(days=45),
                "end_date": today + timedelta(days=46),
            },
        ]

        created_count = 0
        for prog in programs:
            _, created = TrainingProgram.objects.get_or_create(
                title=prog["title"],
                defaults={
                    "description": prog["description"],
                    "start_date": prog["start_date"],
                    "end_date": prog["end_date"],
                },
            )
            if created:
                created_count += 1

        self.stdout.write(f"  Created {created_count} training programme(s).")

    # ------------------------------------------------------------------
    # Step 7 – Policy Documents
    # ------------------------------------------------------------------

    def _create_policy_documents(self, companies):
        policies = [
            {
                "title": "Employee Code of Conduct",
                "category": PolicyDocument.PolicyCategory.HR,
                "description": (
                    "Sets out the standards of behaviour expected of all employees, "
                    "including professional conduct, confidentiality, and disciplinary procedures."
                ),
                "company": None,  # global
            },
            {
                "title": "Leave & Absence Policy",
                "category": PolicyDocument.PolicyCategory.HR,
                "description": (
                    "Defines entitlements, application procedures, and approval workflows "
                    "for all categories of leave."
                ),
                "company": None,
            },
            {
                "title": "Anti-Bribery & Corruption Policy",
                "category": PolicyDocument.PolicyCategory.COMPLIANCE,
                "description": (
                    "Outlines the organisation's zero-tolerance stance on bribery, "
                    "gifts policy, and whistleblower protections."
                ),
                "company": None,
            },
            {
                "title": "IT Acceptable Use Policy",
                "category": PolicyDocument.PolicyCategory.COMPLIANCE,
                "description": (
                    "Governs the use of company IT assets, internet access, email, "
                    "and data storage."
                ),
                "company": None,
            },
            {
                "title": "Performance Appraisal Framework",
                "category": PolicyDocument.PolicyCategory.HR,
                "description": (
                    "Describes the annual appraisal cycle, rating scales, and "
                    "development-plan requirements."
                ),
                "company": None,
            },
        ]

        created_count = 0
        for pol in policies:
            _, created = PolicyDocument.objects.get_or_create(
                title=pol["title"],
                defaults={
                    "category": pol["category"],
                    "description": pol["description"],
                    "company": pol["company"],
                },
            )
            if created:
                created_count += 1

        self.stdout.write(f"  Created {created_count} policy document(s).")

    # ------------------------------------------------------------------
    # Step 8 – Weekly Menu Items
    # ------------------------------------------------------------------

    def _create_weekly_menu_items(self, companies):
        # Build the Monday of the current week
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)

        menu_items = [
            ("Grilled Chicken & Rice",       "Tender grilled chicken breast served with steamed white rice and seasonal vegetables."),
            ("Beef Stew & Sadza",             "Slow-cooked beef stew with traditional sadza and mixed greens."),
            ("Vegetable Stir-Fry & Noodles", "Fresh seasonal vegetables wok-fried with egg noodles in a light soy glaze."),
            ("Fish & Chips",                  "Crispy battered hake fillet with golden chips and tartare sauce."),
            ("Pasta Bolognese",               "Classic beef bolognese on al-dente spaghetti, topped with parmesan."),
        ]

        created_count = 0
        for company in companies.values():
            for item_name, description in menu_items:
                _, created = WeeklyMenuItem.objects.get_or_create(
                    company=company,
                    week_start=monday,
                    item_name=item_name,
                    defaults={
                        "week_end": friday,
                        "description": description,
                        "is_available": True,
                    },
                )
                if created:
                    created_count += 1

        self.stdout.write(f"  Created {created_count} weekly menu item(s).")

    # ------------------------------------------------------------------
    # Step 9 – Food Orders
    # ------------------------------------------------------------------

    def _create_food_orders(self, companies, users_by_company):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)

        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]

        created_count = 0
        for company_name, employee_list in users_by_company.items():
            company = companies[company_name]
            menu_items = list(
                WeeklyMenuItem.objects.filter(company=company, week_start=monday)
            )
            if not menu_items:
                continue

            for idx, (user, profile) in enumerate(employee_list):
                menu_item = menu_items[idx % len(menu_items)]
                order_day = weekdays[idx % len(weekdays)]

                # Idempotency: one order per user per week
                if FoodOrder.objects.filter(
                    ordered_by=user, week_start=monday
                ).exists():
                    continue

                FoodOrder.objects.create(
                    company=company,
                    menu_item=menu_item,
                    week_start=monday,
                    week_end=friday,
                    order_day=order_day,
                    requested_item=menu_item.item_name,
                    ordered_by=user,
                    employee=profile,
                    quantity=1,
                    notes="",
                )
                created_count += 1

        self.stdout.write(f"  Created {created_count} food order(s).")
