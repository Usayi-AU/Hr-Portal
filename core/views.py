import csv
from datetime import timedelta
from io import BytesIO
import os

from django.conf import settings

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import ExtractWeekDay
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image

from .forms import (
	EmployeeProfileForm,
	AppraisalDocumentForm,
	FoodFeedbackForm,
	FoodOrderForm,
	LeaveRequestForm,
	ManagementLeaveDecisionForm,
	PolicyDocumentForm,
	TrainingFeedbackForm,
	TrainingProgramForm,
	WeeklyMenuItemForm,
)
from .models import (
	Company,
	EmployeeProfile,
	AppraisalDocument,
	FoodFeedback,
	FoodOrder,
	LeaveRequest,
	PolicyDocument,
	TrainingFeedback,
	TrainingProgram,
	WeeklyMenuItem,
)

PAYSLIP_ACCESS_CODE = '12345'


def is_hr_user(user):
	return user.is_authenticated and (user.is_superuser or user.is_staff or user.groups.filter(name='HR').exists())


def is_management_user(user):
	return user.is_authenticated and user.groups.filter(name='Management').exists()


def get_user_employee_profile(user):
	if not user.is_authenticated:
		return None
	return EmployeeProfile.objects.filter(user=user).first()


def get_user_company(user):
	profile = get_user_employee_profile(user)
	return profile.company if profile else None


def get_company_employee_queryset(user):
	queryset = EmployeeProfile.objects.all()
	if not user.is_authenticated:
		return queryset.none()
	if not is_hr_user(user):
		profile = get_user_employee_profile(user)
		return queryset.filter(pk=profile.pk) if profile else queryset.none()
	company = get_user_company(user)
	if company:
		return queryset.filter(company=company)
	return queryset


def get_active_menu_item_for_weekday(weekday):
	return WeeklyMenuItem.objects.filter(
		weekday=weekday,
		is_available=True,
	).order_by('-week_start', '-created_at').first()


class RoleRedirectView(LoginRequiredMixin, View):
	def get(self, request, *args, **kwargs):
		if is_hr_user(request.user):
			return redirect('core:hr-dashboard')
		if is_management_user(request.user):
			return redirect('core:management-dashboard')
		return redirect('core:employee-dashboard')


class RoleBasedLoginView(LoginView):
	template_name = 'core/login.html'
	redirect_authenticated_user = True

	def get_success_url(self):
		if is_hr_user(self.request.user):
			return reverse_lazy('core:hr-dashboard')
		if is_management_user(self.request.user):
			return reverse_lazy('core:management-dashboard')
		return reverse_lazy('core:employee-dashboard')


class HRRequiredMixin(UserPassesTestMixin):
	def test_func(self):
		return is_hr_user(self.request.user)

	def handle_no_permission(self):
		return redirect('core:employee-dashboard')


class DashboardContextMixin(LoginRequiredMixin):
	dashboard_title = 'HR Dashboard'
	dashboard_subtitle = 'Manage employee records, leave, payroll, food services, and policies.'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		if is_hr_user(self.request.user):
			sidebar_role = 'hr'
		elif is_management_user(self.request.user):
			sidebar_role = 'management'
		else:
			sidebar_role = 'employee'
		company = get_user_company(self.request.user)
		context.update(
			{
				'dashboard_title': self.dashboard_title,
				'dashboard_subtitle': self.dashboard_subtitle,
				'sidebar_role': sidebar_role,
				'is_hr': is_hr_user(self.request.user),
				'company_name': company.name if company else '',
			}
		)
		return context


class ModuleListContextMixin(DashboardContextMixin):
	page_title = ''
	create_url_name = ''
	hr_only_create = False

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		can_create = not self.hr_only_create or is_hr_user(self.request.user)
		context.update(
			{
				'page_title': self.page_title,
				'create_url': reverse_lazy(self.create_url_name) if can_create else None,
				'can_create': can_create,
			}
		)
		return context


class ModuleFormContextMixin(DashboardContextMixin):
	form_title = ''
	cancel_url_name = ''
	submit_label = 'Save Changes'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(
			{
				'title': self.form_title,
				'cancel_url': reverse_lazy(self.cancel_url_name),
				'submit_label': self.submit_label,
			}
		)
		return context


class ModuleDeleteContextMixin(DashboardContextMixin):
	cancel_url_name = ''

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update({'cancel_url': reverse_lazy(self.cancel_url_name)})
		return context


def home(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if is_hr_user(request.user):
		return redirect('core:hr-dashboard')
	if is_management_user(request.user):
		return redirect('core:management-dashboard')
	return redirect('core:employee-dashboard')


def employee_dashboard(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if is_hr_user(request.user):
		return redirect('core:hr-dashboard')
	if is_management_user(request.user):
		return redirect('core:management-dashboard')

	company = get_user_company(request.user)
	employee_profile = get_user_employee_profile(request.user)

	user_leave_requests = LeaveRequest.objects.filter(employee=employee_profile) if employee_profile else LeaveRequest.objects.none()
	user_leave_request_count = user_leave_requests.count()
	pending_leave_requests = user_leave_requests.filter(status=LeaveRequest.Status.PENDING).count()
	approved_leave_requests = user_leave_requests.filter(status=LeaveRequest.Status.APPROVED).count()
	food_orders_this_week = FoodOrder.objects.filter(
		ordered_by=request.user,
		ordered_at__date__gte=timezone.localdate() - timedelta(days=timezone.localdate().weekday()),
	).count()
	training_feedback_count = TrainingFeedback.objects.filter(submitted_by=request.user).count()
	appraisal_documents_count = AppraisalDocument.objects.filter(employee=employee_profile).count() if employee_profile else 0

	return render(
		request,
		'core/employee_dashboard.html',
		{
			'dashboard_title': 'Employee Dashboard',
			'dashboard_subtitle': 'Track your requests, records, and personal HR services.',
			'sidebar_role': 'employee',
			'company_name': company.name if company else '',
			'user_leave_request_count': user_leave_request_count,
			'pending_leave_requests': pending_leave_requests,
			'approved_leave_requests': approved_leave_requests,
			'food_orders_this_week': food_orders_this_week,
			'training_feedback_count': training_feedback_count,
			'appraisal_documents_count': appraisal_documents_count,
		},
	)


def management_dashboard(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if is_hr_user(request.user):
		return redirect('core:hr-dashboard')
	if not is_management_user(request.user):
		return redirect('core:employee-dashboard')

	assigned_requests = LeaveRequest.objects.filter(
		employee__management_approver=request.user,
	).select_related('employee', 'reviewed_by').order_by('-created_at')
	company = get_user_company(request.user)
	return render(
		request,
		'core/management_dashboard.html',
		{
			'dashboard_title': 'Management Dashboard',
			'dashboard_subtitle': '',
			'sidebar_role': 'management',
			'is_hr': False,
			'company_name': company.name if company else '',
			'pending_reviews': assigned_requests.filter(status=LeaveRequest.Status.FORWARDED).count(),
			'approved_reviews': assigned_requests.filter(status=LeaveRequest.Status.APPROVED).count(),
			'rejected_reviews': assigned_requests.filter(status=LeaveRequest.Status.REJECTED).count(),
			'total_assigned_requests': assigned_requests.count(),
			'recent_requests': assigned_requests[:8],
		},
	)


def hr_dashboard(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if not is_hr_user(request.user):
		return redirect('core:employee-dashboard')

	company = get_user_company(request.user)
	company_employees = get_company_employee_queryset(request.user)
	company_leave_requests = LeaveRequest.objects.filter(employee__company=company) if company else LeaveRequest.objects.none()
	company_training_feedback = TrainingFeedback.objects.filter(employee__company=company) if company else TrainingFeedback.objects.none()
	company_appraisals = AppraisalDocument.objects.filter(employee__company=company) if company else AppraisalDocument.objects.none()
	company_policies = PolicyDocument.objects.filter(company=company) if company else PolicyDocument.objects.none()

	weekday_names = {
		1: 'Sunday',
		2: 'Monday',
		3: 'Tuesday',
		4: 'Wednesday',
		5: 'Thursday',
		6: 'Friday',
		7: 'Saturday',
	}

	leave_pattern_metrics = []
	leave_counts = (
		company_leave_requests.exclude(start_date__isnull=True)
		.annotate(weekday=ExtractWeekDay('start_date'))
		.values('weekday')
		.annotate(total=Count('id'))
		.order_by('-total')
	)
	for row in leave_counts:
		leave_pattern_metrics.append(
			{
				'day': weekday_names.get(row['weekday'], 'Unknown'),
				'count': row['total'],
			}
		)

	top_leave_day = leave_pattern_metrics[0] if leave_pattern_metrics else None

	selected_employee_id = request.GET.get('employee')
	employee_options = company_employees.order_by('full_name')
	selected_employee = None
	if selected_employee_id:
		selected_employee = employee_options.filter(pk=selected_employee_id).first()
	if not selected_employee:
		selected_employee = employee_options.first()

	return render(
		request,
		'core/hr_dashboard.html',
		{
			'dashboard_title': 'HR Dashboard',
			'dashboard_subtitle': 'Oversee employees, approvals, payroll, and compliance tasks.',
			'sidebar_role': 'hr',
			'company_name': company.name if company else '',
			'total_employees': company_employees.count(),
			'pending_leave_requests': company_leave_requests.filter(status=LeaveRequest.Status.PENDING).count(),
			'approved_leave_requests': company_leave_requests.filter(status=LeaveRequest.Status.APPROVED).count(),
			'rejected_leave_requests': company_leave_requests.filter(status=LeaveRequest.Status.REJECTED).count(),
			'total_training_feedback': company_training_feedback.count(),
			'total_appraisals': company_appraisals.count(),
			'total_policies': company_policies.count(),
			'leave_pattern_metrics': leave_pattern_metrics,
			'top_leave_day': top_leave_day,
			'employee_options': employee_options,
			'selected_employee': selected_employee,
		},
	)


class EmployeeProfileListView(ModuleListContextMixin, ListView):
	model = EmployeeProfile
	template_name = 'core/profile_list.html'
	context_object_name = 'items'
	page_title = 'Employee Profiles'
	create_url_name = 'core:profile-create'
	hr_only_create = True

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			return get_company_employee_queryset(self.request.user)
		profile = get_user_employee_profile(self.request.user)
		return queryset.filter(pk=profile.pk) if profile else queryset.none()


class EmployeeProfileCreateView(HRRequiredMixin, ModuleFormContextMixin, CreateView):
	model = EmployeeProfile
	form_class = EmployeeProfileForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:profile-list')
	form_title = 'Create Employee Profile'
	cancel_url_name = 'core:profile-list'
	submit_label = 'Add Employee'

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		company = get_user_company(self.request.user)
		if company and not self.request.user.is_superuser:
			form.fields['company'].queryset = Company.objects.filter(pk=company.pk)
			form.fields['company'].initial = company
		return form


class EmployeeProfileUpdateView(HRRequiredMixin, ModuleFormContextMixin, UpdateView):
	model = EmployeeProfile
	form_class = EmployeeProfileForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:profile-list')
	form_title = 'Edit Employee Profile'
	cancel_url_name = 'core:profile-list'

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		company = get_user_company(self.request.user)
		if company and not self.request.user.is_superuser:
			form.fields['company'].queryset = Company.objects.filter(pk=company.pk)
		return form


class EmployeeProfileDeleteView(HRRequiredMixin, ModuleDeleteContextMixin, DeleteView):
	model = EmployeeProfile
	template_name = 'core/confirm_delete.html'
	success_url = reverse_lazy('core:profile-list')
	cancel_url_name = 'core:profile-list'


class EmployeeProfileDetailView(DashboardContextMixin, DetailView):
	model = EmployeeProfile
	template_name = 'core/profile_detail.html'
	context_object_name = 'profile'

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			company = get_user_company(self.request.user)
			return queryset.filter(company=company) if company else queryset
		profile = get_user_employee_profile(self.request.user)
		return queryset.filter(pk=profile.pk) if profile else queryset.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(
			{
				'dashboard_title': 'Employee Record',
				'dashboard_subtitle': 'Employment and pension profile details.',
				'back_url': reverse_lazy('core:profile-list'),
			}
		)
		return context


class LeaveRequestListView(ModuleListContextMixin, ListView):
	model = LeaveRequest
	template_name = 'core/leave_list.html'
	context_object_name = 'items'
	page_title = 'Leave Requests'
	create_url_name = 'core:leave-create'

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			return queryset.filter(employee__in=get_company_employee_queryset(self.request.user))
		if is_management_user(self.request.user):
			return queryset.filter(employee__management_approver=self.request.user).select_related('employee', 'reviewed_by')
		profile = get_user_employee_profile(self.request.user)
		return queryset.filter(employee=profile) if profile else queryset.none()


class LeaveRequestCreateView(ModuleFormContextMixin, CreateView):
	model = LeaveRequest
	form_class = LeaveRequestForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:leave-list')
	form_title = 'Create Leave Request'
	cancel_url_name = 'core:leave-list'
	submit_label = 'Send Request'

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		if not is_hr_user(self.request.user):
			profile = get_user_employee_profile(self.request.user)
			if profile:
				form.fields['employee'].queryset = EmployeeProfile.objects.filter(pk=profile.pk)
				form.fields['employee'].initial = profile
				form.fields['employee'].widget = form.fields['employee'].hidden_widget()
			if 'status' in form.fields:
				del form.fields['status']
			for field_name in [
				'authorized_by',
				'authorized_signature',
				'authorized_date',
				'qualifies_for_leave',
				'qualification_reason',
			]:
				if field_name in form.fields:
					del form.fields[field_name]
		else:
			form.fields['employee'].queryset = get_company_employee_queryset(self.request.user).order_by('full_name')
		return form

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		if not is_hr_user(self.request.user):
			context['leave_employee'] = get_user_employee_profile(self.request.user)
		return context

	def form_valid(self, form):
		if not is_hr_user(self.request.user):
			profile = get_user_employee_profile(self.request.user)
			if not profile:
				return redirect('core:profile-list')
			form.instance.employee = profile
			form.instance.status = LeaveRequest.Status.PENDING
		return super().form_valid(form)


class LeaveRequestUpdateView(HRRequiredMixin, ModuleFormContextMixin, UpdateView):
	model = LeaveRequest
	form_class = LeaveRequestForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:leave-list')
	form_title = 'Edit Leave Request'
	cancel_url_name = 'core:leave-list'

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(employee__in=get_company_employee_queryset(self.request.user))

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		if 'status' in form.fields:
			form.fields['status'].choices = [
				(LeaveRequest.Status.PENDING, 'Pending'),
				(LeaveRequest.Status.FORWARDED, 'Forwarded to Management'),
			]
		return form


class LeaveRequestDecisionView(ModuleFormContextMixin, UpdateView):
	model = LeaveRequest
	form_class = ManagementLeaveDecisionForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:leave-list')
	form_title = 'Review Leave Request'
	cancel_url_name = 'core:leave-list'
	submit_label = 'Save Decision'

	def dispatch(self, request, *args, **kwargs):
		if not is_management_user(request.user):
			return redirect('core:employee-dashboard')
		leave_request = self.get_object()
		if leave_request.employee.management_approver_id != request.user.id:
			return redirect('core:management-dashboard')
		return super().dispatch(request, *args, **kwargs)

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(employee__management_approver=self.request.user)

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		form.fields['status'].choices = [
			(LeaveRequest.Status.APPROVED, 'Approve'),
			(LeaveRequest.Status.REJECTED, 'Reject'),
		]
		return form

	def form_valid(self, form):
		form.instance.reviewed_by = self.request.user
		form.instance.reviewed_at = timezone.now()
		if form.instance.status == LeaveRequest.Status.APPROVED and not form.instance.authorized_by:
			form.instance.authorized_by = self.request.user.get_full_name() or self.request.user.username
			form.instance.authorized_date = timezone.localdate()
		return super().form_valid(form)


class LeaveRequestDeleteView(HRRequiredMixin, ModuleDeleteContextMixin, DeleteView):
	model = LeaveRequest
	template_name = 'core/confirm_delete.html'
	success_url = reverse_lazy('core:leave-list')
	cancel_url_name = 'core:leave-list'

	def get_queryset(self):
		queryset = super().get_queryset()
		return queryset.filter(employee__in=get_company_employee_queryset(self.request.user))


@require_POST
def forward_leave_to_management(request, pk):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if not is_hr_user(request.user):
		return redirect('core:employee-dashboard')
	leave = LeaveRequest.objects.filter(pk=pk, employee__in=get_company_employee_queryset(request.user)).first()
	if leave:
		if not leave.employee.management_approver_id:
			messages.error(request, f'No management approver is assigned to {leave.employee.full_name}.')
			return redirect('core:leave-list')
		leave.status = LeaveRequest.Status.FORWARDED
		leave.management_comment = ''
		leave.reviewed_by = None
		leave.reviewed_at = None
		leave.save(update_fields=['status', 'management_comment', 'reviewed_by', 'reviewed_at'])
		messages.success(request, 'Leave request forwarded to management.')
	return redirect('core:leave-list')




class FoodPortalView(DashboardContextMixin, View):
	template_name = 'core/food_portal.html'
	dashboard_title = 'Food Services'
	dashboard_subtitle = 'Weekly menu uploaded by HR.'

	def get(self, request, *args, **kwargs):
		return render(request, self.template_name, self._build_context())

	def post(self, request, *args, **kwargs):
		action = request.POST.get('action')
		if action == 'create_menu':
			if not is_hr_user(request.user):
				return redirect('core:food-portal')
			menu_form = WeeklyMenuItemForm(request.POST, request.FILES)
			if menu_form.is_valid():
				menu = menu_form.save(commit=False)
				menu.company = get_user_company(request.user)
				menu.save()
				messages.success(request, 'Weekly menu item uploaded for your company.')
				return redirect('core:food-portal')
			return render(
				request,
				self.template_name,
				self._build_context(menu_form=menu_form),
			)

		return redirect('core:food-portal')

	def _build_context(self, menu_form=None):
		today = timezone.localdate()
		start_of_week = today - timedelta(days=today.weekday())
		company = get_user_company(self.request.user)
		
		menu_queryset = WeeklyMenuItem.objects.filter(week_start__gte=start_of_week)
		if company:
			menu_queryset = menu_queryset.filter(company=company)
		if not is_hr_user(self.request.user):
			menu_queryset = menu_queryset.filter(is_available=True)

		context = {
			'dashboard_title': self.dashboard_title,
			'dashboard_subtitle': 'Weekly menu uploaded by HR for your company.',
			'sidebar_role': 'hr' if is_hr_user(self.request.user) else 'employee',
			'is_hr': is_hr_user(self.request.user),
			'company_name': company.name if company else '',
			'food_active_tab': 'menu',
			'menu_items': menu_queryset,
			'menu_form': menu_form or WeeklyMenuItemForm(),
		}
		return context


class FoodOrderPageView(DashboardContextMixin, View):
	template_name = 'core/food_orders_page.html'
	dashboard_title = 'Food Services'
	dashboard_subtitle = 'Place and manage food orders.'

	def get(self, request, *args, **kwargs):
		return render(request, self.template_name, self._build_context())

	def post(self, request, *args, **kwargs):
		order_form = FoodOrderForm(request.POST)
		if order_form.is_valid():
			order = order_form.save(commit=False)
			order.ordered_by = request.user
			order.employee = get_user_employee_profile(request.user)
			company = get_user_company(request.user)
			order.company = company
			
			# Find the current week's menu for this day
			today = timezone.localdate()
			start_of_week = today - timedelta(days=today.weekday())
			end_of_week = start_of_week + timedelta(days=4)  # Friday
			order.week_start = start_of_week
			order.week_end = end_of_week
			
			# Check if there's an available menu for this week and company
			menu_items = WeeklyMenuItem.objects.filter(
				week_start=start_of_week,
				is_available=True,
				company=company,
			)
			if menu_items.exists():
				order.menu_item = menu_items.first()
			
			order.save()
			messages.success(request, f'Food order for {order.get_order_day_display()} submitted successfully.')
			return redirect('core:food-orders-page')
		return render(request, self.template_name, self._build_context(order_form=order_form))

	def _build_context(self, order_form=None):
		company = get_user_company(self.request.user)
		orders = FoodOrder.objects.select_related('ordered_by', 'employee', 'menu_item')
		
		if is_hr_user(self.request.user):
			# HR sees all orders for their company
			orders = orders.filter(company=company) if company else orders.none()
		else:
			# Employees see only their orders
			orders = orders.filter(ordered_by=self.request.user)

		return {
			'dashboard_title': self.dashboard_title,
			'dashboard_subtitle': 'Place and manage food orders per day for your company.',
			'sidebar_role': 'hr' if is_hr_user(self.request.user) else 'employee',
			'is_hr': is_hr_user(self.request.user),
			'company_name': company.name if company else '',
			'food_active_tab': 'orders',
			'orders': orders,
			'order_form': order_form or FoodOrderForm(),
		}


class FoodFeedbackPageView(DashboardContextMixin, View):
	template_name = 'core/food_feedback_page.html'
	dashboard_title = 'Food Services'
	dashboard_subtitle = 'Submit and review food feedback.'

	def get(self, request, *args, **kwargs):
		return render(request, self.template_name, self._build_context())

	def post(self, request, *args, **kwargs):
		feedback_form = FoodFeedbackForm(request.POST)
		if feedback_form.is_valid():
			feedback = feedback_form.save(commit=False)
			feedback.submitted_by = request.user
			feedback.employee = get_user_employee_profile(request.user)
			feedback.save()
			messages.success(request, 'Food feedback submitted.')
			return redirect('core:food-feedback-page')
		return render(request, self.template_name, self._build_context(feedback_form=feedback_form))

	def _build_context(self, feedback_form=None):
		feedback_items = FoodFeedback.objects.select_related('submitted_by', 'employee')
		if not is_hr_user(self.request.user):
			feedback_items = feedback_items.filter(submitted_by=self.request.user)
		company = get_user_company(self.request.user)

		return {
			'dashboard_title': self.dashboard_title,
			'dashboard_subtitle': self.dashboard_subtitle,
			'sidebar_role': 'hr' if is_hr_user(self.request.user) else 'employee',
			'is_hr': is_hr_user(self.request.user),
			'company_name': company.name if company else '',
			'food_active_tab': 'feedback',
			'feedback_items': feedback_items,
			'feedback_form': feedback_form or FoodFeedbackForm(initial={'feedback_date': timezone.localdate() - timedelta(days=1)}),
		}


class FoodOrderUpdateView(DashboardContextMixin, UpdateView):
	model = FoodOrder
	form_class = FoodOrderForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:food-orders-page')
	form_title = 'Edit Food Order'
	cancel_url_name = 'core:food-orders-page'

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			company = get_user_company(self.request.user)
			return queryset.filter(company=company) if company else queryset.none()
		return queryset.filter(ordered_by=self.request.user)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update({'title': self.form_title, 'cancel_url': reverse_lazy(self.cancel_url_name)})
		return context


class TrainingFeedbackListView(ModuleListContextMixin, ListView):
	model = TrainingFeedback
	template_name = 'core/training_feedback_list.html'
	context_object_name = 'items'
	page_title = 'Training Feedback'
	create_url_name = 'core:training-feedback-create'
	hr_only_create = False

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			return queryset
		return queryset.filter(submitted_by=self.request.user)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		if is_hr_user(self.request.user):
			context['can_create'] = False
			context['create_url'] = None
		return context


class TrainingFeedbackCreateView(ModuleFormContextMixin, CreateView):
	model = TrainingFeedback
	form_class = TrainingFeedbackForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:training-list')
	form_title = 'Submit Training Feedback'
	cancel_url_name = 'core:training-feedback-list'
	submit_label = 'Submit Feedback'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['user'] = self.request.user
		return kwargs

	def form_valid(self, form):
		form.instance.submitted_by = self.request.user
		employee_profile = get_user_employee_profile(self.request.user)
		if employee_profile:
			form.instance.employee = employee_profile
		messages.success(self.request, 'Your feedback has been sent.')
		return super().form_valid(form)


class TrainingFeedbackUpdateView(ModuleFormContextMixin, UpdateView):
	model = TrainingFeedback
	form_class = TrainingFeedbackForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:training-feedback-list')
	form_title = 'Edit Training Feedback'
	cancel_url_name = 'core:training-feedback-list'
	submit_label = 'Save Changes'

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['user'] = self.request.user
		return kwargs

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			return queryset
		return queryset.none()


class TrainingFeedbackDetailView(DashboardContextMixin, DetailView):
	model = TrainingFeedback
	template_name = 'core/training_feedback_detail.html'
	context_object_name = 'item'

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			return queryset
		return queryset.filter(submitted_by=self.request.user)


class TrainingFeedbackDeleteView(ModuleDeleteContextMixin, DeleteView):
	model = TrainingFeedback
	template_name = 'core/confirm_delete.html'
	success_url = reverse_lazy('core:training-feedback-list')
	cancel_url_name = 'core:training-feedback-list'

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			return queryset
		return queryset.none()


def download_food_orders_report(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if not is_hr_user(request.user):
		return redirect('core:employee-dashboard')

	company = get_user_company(request.user)
	response = HttpResponse(content_type='text/csv; charset=utf-8')
	response['Content-Disposition'] = f'attachment; filename="food_orders_{company.name.replace(" ", "_") if company else "all"}.csv"'
	writer = csv.writer(response)

	# Write header row with clear columns
	writer.writerow([
		'Week Start',
		'Order Day',
		'Food Item Requested',
		'Employee Name',
		'Username',
		'Quantity',
		'Special Notes',
		'Order Submitted At',
	])

	# Filter orders by company for HR
	orders_qs = FoodOrder.objects.select_related('menu_item', 'ordered_by', 'employee')
	if company:
		orders_qs = orders_qs.filter(company=company)
	
	orders_qs = orders_qs.order_by('-week_start', 'order_day', '-ordered_at')
	
	for order in orders_qs:
		week_start_str = order.week_start.strftime('%d/%m/%Y') if order.week_start else ''
		ordered_at_str = order.ordered_at.strftime('%d/%m/%Y %H:%M:%S') if order.ordered_at else ''
		
		writer.writerow([
			week_start_str,
			order.get_order_day_display(),
			order.requested_item,
			order.employee.full_name if order.employee else '',
			order.ordered_by.username if order.ordered_by else '',
			order.quantity,
			order.notes,
			ordered_at_str,
		])
	return response


def download_food_feedback_report(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if not is_hr_user(request.user):
		return redirect('core:employee-dashboard')

	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename="food_feedback_report.csv"'
	writer = csv.writer(response)
	writer.writerow(['Submitted At', 'Feedback Date', 'Username', 'Employee Name', 'Rating', 'Remarks'])

	for feedback in FoodFeedback.objects.select_related('submitted_by', 'employee'):
		writer.writerow(
			[
				feedback.created_at,
				feedback.feedback_date,
				feedback.submitted_by.username,
				feedback.employee.full_name if feedback.employee else '',
				feedback.rating if feedback.rating is not None else '',
				feedback.remarks,
			]
		)
	return response


def download_training_feedback_report(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if not is_hr_user(request.user):
		return redirect('core:employee-dashboard')

	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename="training_feedback_report.csv"'
	writer = csv.writer(response)
	writer.writerow([
		'Training Program',
		'Submitted By',
		'Employee Name',
		'Rating',
		'Feedback Text',
		'Recommendations',
		'Areas For Elaboration',
		'Submitted At',
	])

	for item in TrainingFeedback.objects.select_related('training', 'submitted_by', 'employee').order_by('-created_at'):
		writer.writerow(
			[
				item.training.title if item.training else '',
				item.submitted_by.username if item.submitted_by else '',
				item.employee.full_name if item.employee else '',
				item.get_rating_display(),
				item.feedback_text,
				item.recommendations,
				item.areas_for_elaboration,
				item.created_at,
			]
		)
	return response


def download_training_feedback_detail(request, pk):
	if not request.user.is_authenticated:
		return redirect('core:login')

	queryset = TrainingFeedback.objects.select_related('training', 'submitted_by', 'employee')
	if not is_hr_user(request.user):
		queryset = queryset.filter(submitted_by=request.user)

	item = queryset.filter(pk=pk).first()
	if not item:
		return redirect('core:training-feedback-list')

	response = HttpResponse(content_type='text/csv; charset=utf-8')
	response['Content-Disposition'] = f'attachment; filename="training_feedback_{item.pk}.csv"'
	writer = csv.writer(response)
	writer.writerow(['Field', 'Value'])
	writer.writerow(['Training Program', item.training.title if item.training else ''])
	writer.writerow(['Submitted By', item.submitted_by.username if item.submitted_by else ''])
	writer.writerow(['Employee Name', item.employee.full_name if item.employee else ''])
	writer.writerow(['Rating', item.get_rating_display()])
	writer.writerow(['Feedback Text', item.feedback_text])
	writer.writerow(['Recommendations', item.recommendations])
	writer.writerow(['Areas For Elaboration', item.areas_for_elaboration])
	writer.writerow(['Submitted At', item.created_at])
	return response


def download_leave_requests_report(request):
	if not request.user.is_authenticated:
		return redirect('core:login')
	if not is_hr_user(request.user):
		return redirect('core:employee-dashboard')

	company = get_user_company(request.user)
	leave_requests = LeaveRequest.objects.select_related('employee__company', 'reviewed_by').filter(status=LeaveRequest.Status.APPROVED).order_by('-created_at')
	if company:
		leave_requests = leave_requests.filter(employee__company=company)

	buffer = BytesIO()
	doc = SimpleDocTemplate(
		buffer,
		pagesize=A4,
		rightMargin=18 * mm,
		leftMargin=18 * mm,
		topMargin=18 * mm,
		bottomMargin=18 * mm,
	)

	styles = getSampleStyleSheet()
	styles.add(ParagraphStyle(name='ReportTitle', fontSize=18, leading=22, spaceAfter=8, alignment=1, textColor=colors.HexColor('#0f172a')))
	styles.add(ParagraphStyle(name='ReportHeader', fontSize=10, leading=14, spaceAfter=6, textColor=colors.HexColor('#334155')))
	styles.add(ParagraphStyle(name='ReportNote', fontSize=10, leading=13, spaceAfter=10, textColor=colors.HexColor('#475569')))

	content = []
	content.append(Paragraph('Approved Leave Requests', styles['ReportTitle']))
	content.append(Paragraph(f'Company: {company.name if company else "All Companies"}', styles['ReportHeader']))
	content.append(Paragraph(f'Generated: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}', styles['ReportHeader']))
	content.append(Spacer(1, 12))

	if not leave_requests.exists():
		content.append(Paragraph('No approved leave requests found for the selected company.', styles['ReportNote']))
	else:
		table_data = [
			['Employee', 'Leave Type', 'Days', 'Period', 'Balance', 'Authorized By', 'Reviewed At'],
		]

		for item in leave_requests:
			period_text = ''
			if item.start_date and item.end_date:
				period_text = f"{item.start_date.strftime('%d/%m/%Y')} – {item.end_date.strftime('%d/%m/%Y')}"
			table_data.append([
				item.employee.full_name if item.employee else '',
				item.get_leave_type_display(),
				item.requested_days if item.requested_days is not None else '',
				period_text,
				item.leave_days_balance if item.leave_days_balance is not None else '',
				item.authorized_by or '',
				item.reviewed_at.strftime('%d/%m/%Y %H:%M') if item.reviewed_at else '',
			])

		table = Table(table_data, colWidths=[70 * mm, 30 * mm, 18 * mm, 38 * mm, 20 * mm, 30 * mm, 30 * mm])
		table.setStyle(TableStyle([
			('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
			('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
			('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
			('ALIGN', (2, 0), (-1, -1), 'CENTER'),
			('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
			('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
			('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
			('LEFTPADDING', (0, 0), (-1, -1), 6),
			('RIGHTPADDING', (0, 0), (-1, -1), 6),
		]))
		content.append(table)

	doc.build(content)
	buffer.seek(0)

	response = HttpResponse(buffer.read(), content_type='application/pdf')
	response['Content-Disposition'] = f'attachment; filename="approved_leave_requests_{company.name.replace(" ", "_") if company else "all"}.pdf"'
	return response


def download_leave_request_pdf(request, pk):
	if not request.user.is_authenticated:
		return redirect('core:login')

	queryset = LeaveRequest.objects.select_related('employee__company', 'reviewed_by')
	if is_hr_user(request.user):
		queryset = queryset.filter(employee__in=get_company_employee_queryset(request.user))
	elif is_management_user(request.user):
		queryset = queryset.filter(employee__management_approver=request.user)
	else:
		profile = get_user_employee_profile(request.user)
		queryset = queryset.filter(employee=profile) if profile else queryset.none()

	leave = queryset.filter(pk=pk).first()
	if not leave:
		return redirect('core:leave-list')

	buffer = BytesIO()
	doc = SimpleDocTemplate(
		buffer,
		pagesize=A4,
		rightMargin=18 * mm,
		leftMargin=18 * mm,
		topMargin=18 * mm,
		bottomMargin=18 * mm,
	)

	styles = getSampleStyleSheet()
	styles.add(ParagraphStyle(name='FormTitle', fontSize=20, leading=24, spaceAfter=12, alignment=1, textColor=colors.HexColor('#0f172a')))
	styles.add(ParagraphStyle(name='FieldLabel', fontSize=10, leading=12, textColor=colors.HexColor('#334155'), spaceAfter=2))
	styles.add(ParagraphStyle(name='FieldValue', fontSize=10, leading=14, textColor=colors.HexColor('#0f172a')))
	styles.add(ParagraphStyle(name='Note', fontSize=9, leading=11, textColor=colors.HexColor('#475569'), spaceAfter=8))

	content = []
	if leave.employee and leave.employee.company:
		logo_file = f"{leave.employee.company.name.lower()}.logo.png"
		logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', logo_file)
		if os.path.exists(logo_path):
			logo = Image(logo_path, width=50*mm, height=20*mm)
			content.append(logo)
			content.append(Spacer(1, 12))
	content.append(Paragraph('Leave Request Form', styles['FormTitle']))
	content.append(Spacer(1, 12))

	def safe_text(value):
		return str(value) if value is not None else ''

	def format_date(value):
		return value.strftime('%d/%m/%Y') if value else ''

	def format_datetime(value):
		return value.strftime('%d/%m/%Y %H:%M') if value else ''

	fields = [
		['Employee Name', leave.employee.full_name if leave.employee else ''],
		['Employee Number', leave.employee.employee_number if leave.employee else ''],
		['Company', leave.employee.company.name if leave.employee and leave.employee.company else ''],
		['Job Title', leave.employee.job_title if leave.employee else ''],
		['Leave Type', leave.get_leave_type_display()],
		['Start Date', format_date(leave.start_date)],
		['End Date', format_date(leave.end_date)],
		['Reason for Leave', leave.reason or ''],
		['Total Leave Days Taken', safe_text(leave.total_leave_days_taken)],
		['Total Leave Days Accrued', safe_text(leave.total_leave_days_accrued)],
		['Leave Balance', safe_text(leave.leave_days_balance)],
		['Qualifies for Leave', leave.get_qualifies_for_leave_display() if leave.qualifies_for_leave else ''],
		['Qualification Reason', leave.qualification_reason or ''],
		['Status', leave.get_status_display()],
		['Reviewed By', leave.reviewed_by.get_full_name() if leave.reviewed_by else ''],
		['Reviewed At', format_datetime(leave.reviewed_at)],
		['Applicant Signed Date', format_date(leave.applicant_signed_date)],
		['Applicant Signature', leave.applicant_signature or ''],
		['Authorized Date', format_date(leave.authorized_date)],
		['Authorized By', leave.authorized_by or ''],
		['Authorized Signature', leave.authorized_signature or ''],
	]

	table_data = []
	for label, value in fields:
		table_data.append([
			Paragraph(f'<b>{label}</b>', styles['FieldLabel']),
			Paragraph(value.replace('\n', '<br/>'), styles['FieldValue']),
		])

	table = Table(table_data, colWidths=[55 * mm, 115 * mm], hAlign='LEFT')
	table.setStyle(TableStyle([
		('VALIGN', (0, 0), (-1, -1), 'TOP'),
		('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#0f172a')),
		('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#0f172a')),
		('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
		('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
		('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
		('BACKGROUND', (0, 1), (-1, -1), colors.white),
		('LEFTPADDING', (0, 0), (-1, -1), 6),
		('RIGHTPADDING', (0, 0), (-1, -1), 6),
		('BOTTOMPADDING', (0, 0), (-1, -1), 6),
		('TOPPADDING', (0, 0), (-1, -1), 6),
	]))

	content.append(table)
	if leave.employee and leave.employee.company and leave.employee.company.name.lower() == 'intellego' and leave.authorized_by == 'Welcome.Mavingire':
		sig_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'welcome.png')
		if os.path.exists(sig_path):
			content.append(Spacer(1, 12))
			content.append(Paragraph('Authorized Signature:', styles['FieldLabel']))
			sig = Image(sig_path, width=50*mm, height=20*mm)
			content.append(sig)
	doc.build(content)
	buffer.seek(0)

	response = HttpResponse(buffer.read(), content_type='application/pdf')
	response['Content-Disposition'] = f'attachment; filename="leave_request_{leave.pk}_{leave.employee.employee_number if leave.employee else "unknown"}.pdf"'
	return response


class TrainingProgramListView(ModuleListContextMixin, ListView):
	model = TrainingProgram
	template_name = 'core/training_list.html'
	context_object_name = 'items'
	page_title = 'Training Programs'
	create_url_name = 'core:training-create'
	hr_only_create = True

	def get_queryset(self):
		queryset = super().get_queryset()
		if is_hr_user(self.request.user):
			return queryset
		# Employees can see all training programs, not just future ones
		return queryset


class TrainingProgramCreateView(HRRequiredMixin, ModuleFormContextMixin, CreateView):
	model = TrainingProgram
	form_class = TrainingProgramForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:training-list')
	form_title = 'Create Training Program'
	cancel_url_name = 'core:training-list'


class TrainingProgramUpdateView(HRRequiredMixin, ModuleFormContextMixin, UpdateView):
	model = TrainingProgram
	form_class = TrainingProgramForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:training-list')
	form_title = 'Edit Training Program'
	cancel_url_name = 'core:training-list'


class TrainingProgramDeleteView(HRRequiredMixin, ModuleDeleteContextMixin, DeleteView):
	model = TrainingProgram
	template_name = 'core/confirm_delete.html'
	success_url = reverse_lazy('core:training-list')
	cancel_url_name = 'core:training-list'


class PolicyDocumentListView(ModuleListContextMixin, ListView):
	model = PolicyDocument
	template_name = 'core/policy_list.html'
	context_object_name = 'items'
	page_title = 'Policy Hub'
	create_url_name = 'core:policy-create'
	hr_only_create = True
	allowed_categories = {'hr', 'compliance'}

	def get_queryset(self):
		queryset = super().get_queryset()
		# Filter by company
		company = get_user_company(self.request.user)
		if company:
			queryset = queryset.filter(company=company)
		# Filter by category
		category = self.request.GET.get('category')
		if category in self.allowed_categories:
			queryset = queryset.filter(category=category)
		self.current_category = category if category in self.allowed_categories else 'all'
		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['current_category'] = getattr(self, 'current_category', 'all')
		context['policy_categories'] = PolicyDocument.PolicyCategory.choices
		return context


class PolicyDocumentCreateView(HRRequiredMixin, ModuleFormContextMixin, CreateView):
	model = PolicyDocument
	form_class = PolicyDocumentForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:policy-list')
	form_title = 'Create Policy Document'
	cancel_url_name = 'core:policy-list'

	def form_valid(self, form):
		form.instance.company = get_user_company(self.request.user)
		return super().form_valid(form)


class PolicyDocumentUpdateView(HRRequiredMixin, ModuleFormContextMixin, UpdateView):
	model = PolicyDocument
	form_class = PolicyDocumentForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:policy-list')
	form_title = 'Edit Policy Document'
	cancel_url_name = 'core:policy-list'

	def get_queryset(self):
		queryset = super().get_queryset()
		company = get_user_company(self.request.user)
		if company:
			queryset = queryset.filter(company=company)
		return queryset


class PolicyDocumentDeleteView(HRRequiredMixin, ModuleDeleteContextMixin, DeleteView):
	model = PolicyDocument
	template_name = 'core/confirm_delete.html'
	success_url = reverse_lazy('core:policy-list')
	cancel_url_name = 'core:policy-list'

	def get_queryset(self):
		queryset = super().get_queryset()
		company = get_user_company(self.request.user)
		if company:
			queryset = queryset.filter(company=company)
		return queryset


class AppraisalDocumentListView(ModuleListContextMixin, ListView):
	model = AppraisalDocument
	template_name = 'core/appraisal_document_list.html'
	context_object_name = 'items'
	page_title = 'Performance Appraisals'
	create_url_name = 'core:appraisal-create'
	hr_only_create = True

	def get_queryset(self):
		queryset = super().get_queryset().select_related('employee', 'uploaded_by')
		if is_hr_user(self.request.user):
			employee_id = self.request.GET.get('employee')
			if employee_id:
				queryset = queryset.filter(employee_id=employee_id)
			return queryset
		employee_profile = get_user_employee_profile(self.request.user)
		return queryset.filter(employee=employee_profile) if employee_profile else queryset.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		if is_hr_user(self.request.user):
			context['employee_options'] = get_company_employee_queryset(self.request.user).order_by('full_name')
			context['selected_employee_id'] = self.request.GET.get('employee', '')
		return context


class AppraisalDocumentCreateView(HRRequiredMixin, ModuleFormContextMixin, CreateView):
	model = AppraisalDocument
	form_class = AppraisalDocumentForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:appraisal-list')
	form_title = 'Upload Appraisal Document'
	cancel_url_name = 'core:appraisal-list'
	submit_label = 'Upload'

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		form.fields['employee'].queryset = get_company_employee_queryset(self.request.user).order_by('full_name')
		return form

	def form_valid(self, form):
		form.instance.uploaded_by = self.request.user
		messages.success(self.request, 'The appraisal document has been uploaded successfully.')
		return super().form_valid(form)


class AppraisalDocumentUpdateView(HRRequiredMixin, ModuleFormContextMixin, UpdateView):
	model = AppraisalDocument
	form_class = AppraisalDocumentForm
	template_name = 'core/form.html'
	success_url = reverse_lazy('core:appraisal-list')
	form_title = 'Edit Appraisal Document'
	cancel_url_name = 'core:appraisal-list'

	def get_queryset(self):
		queryset = super().get_queryset().select_related('employee', 'uploaded_by')
		return queryset.filter(employee__in=get_company_employee_queryset(self.request.user))

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		form.fields['employee'].queryset = get_company_employee_queryset(self.request.user).order_by('full_name')
		return form


class AppraisalDocumentDeleteView(HRRequiredMixin, ModuleDeleteContextMixin, DeleteView):
	model = AppraisalDocument
	template_name = 'core/confirm_delete.html'
	success_url = reverse_lazy('core:appraisal-list')
	cancel_url_name = 'core:appraisal-list'

	def get_queryset(self):
		queryset = super().get_queryset().select_related('employee', 'uploaded_by')
		return queryset.filter(employee__in=get_company_employee_queryset(self.request.user))
