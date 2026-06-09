from django import forms
from django.contrib.auth.models import User

from .models import (
    AttendanceRecord,
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


class EmployeeProfileForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="Select user (optional)",
        help_text="Link this profile to a system user account. Leave blank if the employee doesn't have an account yet."
    )

    email = forms.CharField(
        required=False,
        help_text="Enter the local part only (e.g. 'john.doe'); the company domain will be appended automatically.",
        widget=forms.TextInput(attrs={'placeholder': 'local-part (e.g. john.doe)'}),
    )

    class Meta:
        model = EmployeeProfile
        fields = [
            'user',
            'company',
            'employee_number',
            'full_name',
            'job_title',
            'date_of_birth',
            'date_joined',
            'dependents_count',
            'email',
            'phone',
            'address',
            'emergency_contact',
            'employment_history',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
            'employment_history': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_user(self):
        user = self.cleaned_data.get('user')
        if user:
            # Check if this user already has an employee profile
            existing_profile = EmployeeProfile.objects.filter(user=user).exclude(pk=self.instance.pk if self.instance else None)
            if existing_profile.exists():
                raise forms.ValidationError("An employee profile already exists for this user.")
        return user

    def clean(self):
        cleaned = super().clean()
        company = cleaned.get('company')
        email = cleaned.get('email')
        user = cleaned.get('user')

        # Map company to canonical email domain
        domain_map = {
            'Intellego Investment Consultants': '@intellego-ic.com',
            'HEW Corporate Lawyers': '@hewcorplaw.com',
            'MMC Capital': '@mmccapitalzim.com',
        }

        if company:
            domain = domain_map.get(company.name)
            if domain:
                if email:
                    # normalize local part and enforce company domain
                    if '@' in email:
                        local = email.split('@')[0]
                    else:
                        local = email
                    cleaned['email'] = f"{local}{domain}"
                elif user:
                    # if no email provided, build from username
                    cleaned['email'] = f"{user.username}{domain}"

        return cleaned


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            'employee',
            'leave_type',
            'requested_days',
            'start_date',
            'end_date',
            'reason',
            'total_leave_days_taken',
            'total_leave_days_accrued',
            'leave_days_balance',
            'applicant_signature',
            'applicant_signed_date',
            'authorized_by',
            'authorized_signature',
            'authorized_date',
            'qualifies_for_leave',
            'qualification_reason',
            'status',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'applicant_signed_date': forms.DateInput(attrs={'type': 'date'}),
            'authorized_date': forms.DateInput(attrs={'type': 'date'}),
            'qualifies_for_leave': forms.RadioSelect(choices=[('yes', 'Yes'), ('no', 'No')]),
        }

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        requested_days = cleaned.get('requested_days')

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('End date must be on or after start date.')

        if not requested_days and start_date and end_date:
            cleaned['requested_days'] = (end_date - start_date).days + 1

        return cleaned


class ManagementLeaveDecisionForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['status', 'management_comment']
        widgets = {
            'management_comment': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        management_comment = (cleaned_data.get('management_comment') or '').strip()

        if status == LeaveRequest.Status.REJECTED and not management_comment:
            raise forms.ValidationError('Please provide a reason when rejecting a leave request.')

        return cleaned_data


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['employee', 'date', 'clock_in', 'clock_out', 'overtime_hours']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'clock_in': forms.TimeInput(attrs={'type': 'time'}),
            'clock_out': forms.TimeInput(attrs={'type': 'time'}),
        }



class TrainingProgramForm(forms.ModelForm):
    class Meta:
        model = TrainingProgram
        fields = ['title', 'description', 'start_date', 'end_date', 'material_file']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PolicyDocumentForm(forms.ModelForm):
    class Meta:
        model = PolicyDocument
        fields = ['title', 'category', 'description', 'file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class AppraisalDocumentForm(forms.ModelForm):
    class Meta:
        model = AppraisalDocument
        fields = ['employee', 'title', 'appraisal_period', 'description', 'file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class WeeklyMenuItemForm(forms.ModelForm):
	class Meta:
		model = WeeklyMenuItem
		fields = ['week_start', 'week_end', 'item_name', 'description', 'menu_image', 'is_available']
		widgets = {
			'week_start': forms.DateInput(attrs={'type': 'date'}),
			'week_end': forms.DateInput(attrs={'type': 'date'}),
			'description': forms.Textarea(attrs={'rows': 3}),
		}


class FoodOrderForm(forms.ModelForm):
	class Meta:
		model = FoodOrder
		fields = ['order_day', 'requested_item', 'notes']
		widgets = {
			'order_day': forms.Select(attrs={'class': 'form-control'}),
			'requested_item': forms.TextInput(attrs={
				'placeholder': 'e.g., Chicken Rice, Vegetable Pasta, Beef Stew',
				'class': 'form-control',
			}),
			'notes': forms.Textarea(attrs={
				'rows': 2,
				'placeholder': 'Any special requests or allergies?',
				'class': 'form-control',
			}),
		}

	def clean(self):
		cleaned_data = super().clean()
		requested_item = cleaned_data.get('requested_item', '').strip()
		if not requested_item:
			raise forms.ValidationError('Please specify what food item you would like to order.')
		return cleaned_data


class FoodFeedbackForm(forms.ModelForm):
    class Meta:
        model = FoodFeedback
        fields = ['feedback_date', 'rating', 'remarks']
        widgets = {
            'feedback_date': forms.DateInput(attrs={'type': 'date'}),
        }


class TrainingFeedbackForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    class Meta:
        model = TrainingFeedback
        fields = ['training', 'rating', 'feedback_text', 'recommendations', 'areas_for_elaboration']
        widgets = {
            'feedback_text': forms.Textarea(attrs={'rows': 4}),
            'recommendations': forms.Textarea(attrs={'rows': 3}),
            'areas_for_elaboration': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_training(self):
        training = self.cleaned_data.get('training')
        if not training or not self.user:
            return training

        existing_feedback = TrainingFeedback.objects.filter(
            training=training,
            submitted_by=self.user,
        ).exclude(pk=self.instance.pk if self.instance else None)

        if existing_feedback.exists():
            raise forms.ValidationError(
                'You have already submitted feedback for this training program.'
            )

        return training
