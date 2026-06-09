from django.contrib import admin

from .models import (
	AttendanceRecord,
	EmployeeProfile,
	FoodFeedback,
	FoodOrder,
	LeaveRequest,
	PolicyDocument,
	TrainingProgram,
	WeeklyMenuItem,
)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
	list_display = ('employee_number', 'full_name', 'job_title', 'email', 'user')
	search_fields = ('employee_number', 'full_name', 'email', 'user__username')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
	list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status')
	list_filter = ('leave_type', 'status')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
	list_display = ('employee', 'date', 'clock_in', 'clock_out', 'overtime_hours')
	list_filter = ('date',)


@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
	list_display = ('title', 'start_date', 'end_date', 'material_file', 'created_at')
	search_fields = ('title',)


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
	list_display = ('title', 'file', 'created_at')
	search_fields = ('title',)


@admin.register(WeeklyMenuItem)
class WeeklyMenuItemAdmin(admin.ModelAdmin):
	list_display = ('week_start', 'week_end', 'item_name', 'is_available')
	list_filter = ('week_start', 'is_available')
	search_fields = ('item_name',)


@admin.register(FoodOrder)
class FoodOrderAdmin(admin.ModelAdmin):
	list_display = ('ordered_by', 'menu_item', 'quantity', 'ordered_at')
	list_filter = ('ordered_at', 'week_start')
	search_fields = ('ordered_by__username', 'menu_item__item_name')


@admin.register(FoodFeedback)
class FoodFeedbackAdmin(admin.ModelAdmin):
	list_display = ('submitted_by', 'feedback_date', 'rating', 'created_at')
	list_filter = ('feedback_date', 'rating')
	search_fields = ('submitted_by__username', 'remarks')
