# HR User Portal (Django + Tailwind CSS)

Starter development environment for an individual HR portal with responsive UI.

## Stack
- Django 5
- Tailwind CSS (CDN)
- SQLite (default for development)

## Project Structure
- `config/` Django project config
- `core/` Main app for portal pages and modules
- `theme/` Tailwind integration app
- `templates/core/home.html` Starter responsive landing page

## Prerequisites
- Python 3.13+

## Setup (Windows PowerShell)
```powershell
Set-Location "c:\Users\USER\Documents\HR User Portal"
C:/Users/USER/AppData/Local/Programs/Python/Python313/python.exe -m pip install -r requirements.txt
C:/Users/USER/AppData/Local/Programs/Python/Python313/python.exe manage.py migrate
```

## Run Development Servers
Run Django server:
```powershell
Set-Location "c:\Users\USER\Documents\HR User Portal"
C:/Users/USER/AppData/Local/Programs/Python/Python313/python.exe manage.py runserver
```

## Authentication (Employee and HR)
- Login URL: `http://127.0.0.1:8000/login/`
- Users must sign in before accessing dashboards/modules.
- HR users are redirected to the HR dashboard.
- Employee users are redirected to the Employee dashboard.

### Create Users
```powershell
Set-Location "c:\Users\USER\Documents\HR User Portal"
C:/Users/USER/AppData/Local/Programs/Python/Python313/python.exe manage.py createsuperuser
```

Use Django Admin (`/admin/`) to:
- Create an `HR` group.
- Add HR users to the `HR` group (or mark them `staff`).
- Create employee user accounts.
- Link each employee user to their profile in `Employee Profiles` (`user` field).

Open: `http://127.0.0.1:8000/`

## Dashboard Routes
- Home: `http://127.0.0.1:8000/`
- Employee Dashboard: `http://127.0.0.1:8000/dashboard/employee/`
- HR Dashboard: `http://127.0.0.1:8000/dashboard/hr/`

Both dashboards use a left sidebar menu for navigation.

## Module Routes (CRUD)
- Profiles: `http://127.0.0.1:8000/profiles/`
- Leave Requests: `http://127.0.0.1:8000/leave/`
- Payroll: `http://127.0.0.1:8000/payroll/`
- Food Services (menu, orders, feedback): `http://127.0.0.1:8000/food/`
- Training: `http://127.0.0.1:8000/training/`
- Policy Hub: `http://127.0.0.1:8000/policies/`

## Employee Experience
- Profile: employee can view own profile details maintained by HR.
- Leave: employee can submit leave requests (status is controlled by HR).
- Payslips: employee can download payslip files uploaded by HR.
- Food Services: employee can view menu, place/edit weekday orders, and submit feedback from one page.
- Training: employee can view training programs posted by HR.
- Policy Hub: employee can view/download company policies posted by HR.

## HR Food Reports
- Download food orders report CSV: `http://127.0.0.1:8000/food/orders/report/`
- Download food feedback report CSV: `http://127.0.0.1:8000/food/feedback/report/`

## Suggested Next Implementation Apps
- `accounts` (authentication, profile)
- `leave` (requests, approvals, balances)
- `attendance` (clock-in/out, overtime)
- `payroll` (payslips, tax docs, deductions)
- `training` (courses, enrollments, certifications)
- `policies` (documents, announcements)
