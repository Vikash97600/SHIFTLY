from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'name@example.com'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': '••••••••'
    }))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    if user.role == User.Role.BUSINESS and user.status != User.AccountStatus.APPROVED:
                        raise forms.ValidationError(_("Your business account is currently under review. An administrator must approve your registration before you can access your dashboard."))
                    if not user.is_active:
                        raise forms.ValidationError(_("This account is currently inactive."))
                    user = authenticate(username=email, password=password)
                else:
                    user = None
            except User.DoesNotExist:
                user = None

            if not user:
                raise forms.ValidationError(_("Invalid email or password."))
            cleaned_data['user'] = user
        return cleaned_data


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': '••••••••'
    }), min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': '••••••••'
    }))
    
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'Jane'
    }))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'Doe'
    }))
    company_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'Red Coffee'
    }))
    owner_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'John Doe'
    }))
    mobile_number = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': '+1 (555) 019-2834'
    }))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': '123 Main St, Suite 100, City, State, ZIP',
        'rows': 3
    }))
    business_category = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'Food Services, Retail, Tech, etc.'
    }))
    gst_number = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'GSTIN123456789 (Optional)'
    }))
    business_license = forms.FileField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light'
    }))
    gst_document = forms.FileField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light'
    }))
    tax_document = forms.FileField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light'
    }))

    class Meta:
        model = User
        fields = ['email', 'role', 'password']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control bg-dark border-secondary text-light',
                'placeholder': 'name@example.com'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select bg-dark border-secondary text-light'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')

        if password != confirm_password:
            raise forms.ValidationError(_("Passwords do not match."))

        if role == User.Role.ADMIN:
            raise forms.ValidationError(_("Admin registration is not allowed publicly."))

        if role == User.Role.STUDENT:
            if not cleaned_data.get('first_name') or not cleaned_data.get('last_name'):
                raise forms.ValidationError(_("First name and last name are required for student accounts."))
        elif role == User.Role.BUSINESS:
            if not cleaned_data.get('company_name'):
                raise forms.ValidationError(_("Company name is required for business accounts."))
            if not cleaned_data.get('owner_name'):
                raise forms.ValidationError(_("Owner name is required for business accounts."))
            if not cleaned_data.get('mobile_number'):
                raise forms.ValidationError(_("Mobile number is required for business accounts."))
            if not cleaned_data.get('address'):
                raise forms.ValidationError(_("Address is required for business accounts."))
            if not cleaned_data.get('business_category'):
                raise forms.ValidationError(_("Business category is required for business accounts."))
            
            gst_number = cleaned_data.get('gst_number')
            if gst_number:
                from businesses.models import BusinessProfile
                if BusinessProfile.objects.filter(gst_number=gst_number).exists() or BusinessProfile.objects.filter(business_registration_no=gst_number).exists():
                    self.add_error('gst_number', _("A business with this GST number is already registered."))

        return cleaned_data


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'Your Name'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'name@example.com'
    }))
    subject = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'placeholder': 'Subject'
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control bg-dark border-secondary text-light',
        'rows': 5,
        'placeholder': 'Your message...'
    }))
