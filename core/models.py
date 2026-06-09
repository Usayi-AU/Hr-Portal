from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
	name = models.CharField(max_length=200, unique=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class EmployeeProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
	management_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_employee_profiles')
	company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
	employee_number = models.CharField(max_length=20, unique=True)
	full_name = models.CharField(max_length=150)
	job_title = models.CharField(max_length=120)
	date_of_birth = models.DateField(null=True, blank=True)
	date_joined = models.DateField(null=True, blank=True)
	dependents_count = models.PositiveIntegerField(default=0)
	email = models.EmailField()
	phone = models.CharField(max_length=30, blank=True)
	address = models.TextField(blank=True)
	emergency_contact = models.CharField(max_length=150, blank=True)
	pension_provider = models.CharField(max_length=150, blank=True)
	pension_policy_number = models.CharField(max_length=80, blank=True)
	pension_contribution_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
	employment_history = models.TextField(blank=True)

	def __str__(self):
		return f"{self.employee_number} - {self.full_name}"


class LeaveRequest(models.Model):
	class LeaveType(models.TextChoices):
		VACATION = 'vacation', 'Vacation'
		STUDY = 'study', 'Study'
		SPECIAL = 'special', 'Special'
		COMPASSIONATE = 'compassionate', 'Compassionate'
		SICK = 'sick', 'Sick'
		MATERNITY = 'maternity', 'Maternity'
		AWAY_ON_BUSINESS = 'away_on_business', 'Away on Business'
		PUBLIC_HOLIDAY = 'public_holiday', 'Public Holiday'

	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		FORWARDED = 'forwarded', 'Forwarded to Management'
		APPROVED = 'approved', 'Approved'
		REJECTED = 'rejected', 'Rejected'

	employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
	leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
	requested_days = models.PositiveIntegerField(null=True, blank=True)
	start_date = models.DateField()
	end_date = models.DateField()
	reason = models.TextField(blank=True)
	total_leave_days_taken = models.PositiveIntegerField(null=True, blank=True)
	total_leave_days_accrued = models.PositiveIntegerField(null=True, blank=True)
	leave_days_balance = models.PositiveIntegerField(null=True, blank=True)
	applicant_signature = models.CharField(max_length=150, blank=True)
	applicant_signed_date = models.DateField(null=True, blank=True)
	authorized_by = models.CharField(max_length=150, blank=True)
	authorized_signature = models.CharField(max_length=150, blank=True)
	authorized_date = models.DateField(null=True, blank=True)
	qualifies_for_leave = models.CharField(
		max_length=3,
		choices=[('yes', 'Yes'), ('no', 'No')],
		blank=True,
	)
	qualification_reason = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	management_comment = models.TextField(blank=True)
	reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leave_requests')
	reviewed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.employee.full_name} - {self.get_leave_type_display()}"


class AttendanceRecord(models.Model):
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
	date = models.DateField()
	clock_in = models.TimeField()
	clock_out = models.TimeField()
	overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)

	class Meta:
		ordering = ['-date']

	def __str__(self):
		return f"{self.employee.full_name} - {self.date}"


class TrainingProgram(models.Model):
	title = models.CharField(max_length=160)
	description = models.TextField(blank=True)
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)
	material_file = models.FileField(upload_to='training_materials/', null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title


class PolicyDocument(models.Model):
	class PolicyCategory(models.TextChoices):
		HR = 'hr', 'HR Policies'
		COMPLIANCE = 'compliance', 'Compliance Policies'

	company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='policies', null=True, blank=True)
	title = models.CharField(max_length=160)
	category = models.CharField(max_length=20, choices=PolicyCategory.choices, default=PolicyCategory.HR)
	description = models.TextField(blank=True)
	file = models.FileField(upload_to='policies/', null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.title


class AppraisalDocument(models.Model):
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='appraisal_documents')
	title = models.CharField(max_length=160)
	appraisal_period = models.CharField(max_length=80, blank=True)
	description = models.TextField(blank=True)
	file = models.FileField(upload_to='appraisal_documents/', null=True, blank=True)
	uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_appraisal_documents')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.employee.full_name} - {self.title}"


class WeeklyMenuItem(models.Model):
	company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='weekly_menus', null=True, blank=True)
	week_start = models.DateField(help_text='Start date of the menu week (usually Monday).')
	week_end = models.DateField(help_text='End date of the menu week (usually Friday or Sunday).')
	item_name = models.CharField(max_length=150, blank=True, default='')
	description = models.TextField(blank=True)
	menu_image = models.ImageField(upload_to='food_menus/', null=True, blank=True)
	is_available = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-week_start', 'item_name']

	def __str__(self):
		company_name = f" - {self.company.name}" if self.company else ""
		return f"Week {self.week_start} to {self.week_end} - {self.item_name}{company_name}"


class FoodOrder(models.Model):
	WEEKDAY_CHOICES = [
		('monday', 'Monday'),
		('tuesday', 'Tuesday'),
		('wednesday', 'Wednesday'),
		('thursday', 'Thursday'),
		('friday', 'Friday'),
	]

	company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='food_orders', null=True, blank=True)
	menu_item = models.ForeignKey(WeeklyMenuItem, on_delete=models.SET_NULL, null=True, blank=True)
	week_start = models.DateField(null=True, blank=True)
	week_end = models.DateField(null=True, blank=True)
	order_day = models.CharField(max_length=10, choices=WEEKDAY_CHOICES, default='monday', help_text='Day to receive the food order')
	requested_item = models.CharField(max_length=150, blank=True, default='', help_text='Type of food requested')
	ordered_by = models.ForeignKey(User, on_delete=models.CASCADE)
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True)
	quantity = models.PositiveIntegerField(default=1)
	notes = models.CharField(max_length=255, blank=True)
	ordered_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-week_start', 'order_day', '-ordered_at']

	def __str__(self):
		item = self.requested_item or (self.menu_item.item_name if self.menu_item else 'Order')
		return f"{self.ordered_by.username} - {item} ({self.get_order_day_display()}) x{self.quantity}"


class FoodFeedback(models.Model):
	submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True)
	feedback_date = models.DateField(help_text='Date for the meal being reviewed (e.g., previous day).')
	rating = models.PositiveSmallIntegerField(null=True, blank=True)
	remarks = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-feedback_date', '-created_at']

	def __str__(self):
		return f"{self.submitted_by.username} - {self.feedback_date}"


class TrainingFeedback(models.Model):
	class Rating(models.TextChoices):
		POOR = '1', 'Poor'
		FAIR = '2', 'Fair'
		GOOD = '3', 'Good'
		VERY_GOOD = '4', 'Very Good'
		EXCELLENT = '5', 'Excellent'

	training = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='feedbacks')
	submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='training_feedbacks')
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.SET_NULL, null=True, blank=True)
	rating = models.CharField(max_length=1, choices=Rating.choices, default=Rating.GOOD)
	feedback_text = models.TextField(help_text='Your overall feedback on the training')
	recommendations = models.TextField(blank=True, help_text='Recommendations for upcoming trainings')
	areas_for_elaboration = models.TextField(blank=True, help_text='Areas where the presenter should elaborate more')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		unique_together = ('training', 'submitted_by')

	def __str__(self):
		return f"{self.submitted_by.username} - {self.training.title}"
