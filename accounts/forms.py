from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import Account , Courier
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
import re
from django.contrib.auth import get_user_model


class RegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'placeholder': 'First Name'}),
        help_text='Required'
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name'}),
        help_text='Required'
    )
    email = forms.EmailField(
        max_length=100,
        widget=forms.EmailInput(attrs={'placeholder': 'Email'}),
        help_text='Required. Add a valid email address'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        help_text='Required. Enter a password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}),
        help_text='Required. Confirm your password'
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}),
        help_text='Enter a valid phone number'
    )

    class Meta:
        model = Account
        fields = ("first_name", "last_name", "email", "password", "confirm_password", "phone_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control form-control-lg',
                'style': 'border: 1px solid black;'
            })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Account.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])  # Hash the password
        if commit:
            user.save()
        return user






class LoginForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=100)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control form-control-bg',
            'style': 'border: 1px solid black;',
            'placeholder': 'Enter your email'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-bg',
            'style': 'border: 1px solid black;',
            'placeholder': 'Enter your password'
        })

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        # Authenticate with email and password
        user = authenticate(email=email, password=password)
        if user is None:
            raise forms.ValidationError("Invalid email or password.")
        self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class CourierForm(forms.ModelForm):
    class Meta:
        model = Courier
        fields = [
            'receiver_name', 'receiver_contact_number', 'receiver_email', 'receiver_address',
            'sender_name', 'sender_contact_number', 'sender_email', 'sender_address',
            'item_description', 'number_of_items', 'parcel_colour',
            'destination', 'date_sent', 'estimated_delivery_date', 'weight', 'category'
        ]
        widgets = {
            'receiver_name': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid black;'}),
            'receiver_contact_number': forms.TextInput(attrs={'class': 'form-control','type': 'number', 'style': 'border: 1px solid black;'}),
            'receiver_email': forms.EmailInput(attrs={'class': 'form-control', 'style': 'border: 1px solid black;'}),
            'receiver_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style': 'border: 1px solid black;'}),
            'sender_name': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid black;'}),
            'sender_contact_number': forms.TextInput(attrs={'class': 'form-control','type': 'number', 'style': 'border: 1px solid black;'}),
            'sender_email': forms.EmailInput(attrs={'class': 'form-control', 'style': 'border: 1px solid black;'}),
            'sender_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style': 'border: 1px solid black;'}),
            'item_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'style': 'border: 1px solid black;'}),
            'number_of_items': forms.NumberInput(attrs={'class': 'form-control', 'type': 'number', 'style': 'border: 1px solid black;'}),
            'parcel_colour': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid black;'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'style': 'border: 1px solid black;'}),
            'date_sent': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'style': 'border: 1px solid black;'}),
            'estimated_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'style': 'border: 1px solid black;'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'style': 'border: 1px solid black;'}),
            'category': forms.Select(attrs={'class': 'form-control', 'style': 'border: 1px solid black;'}),
        }

    def clean_estimated_delivery_date(self):
        """Ensure the estimated delivery date is not before the date sent."""
        date_sent = self.cleaned_data.get('date_sent')
        estimated_delivery_date = self.cleaned_data.get('estimated_delivery_date')
        if estimated_delivery_date and date_sent and estimated_delivery_date < date_sent:
            raise ValidationError("Estimated delivery date cannot be before the date sent.")
        return estimated_delivery_date


class SendresetcodeForm(forms.Form):
    email = forms.EmailField(
        max_length=100,
        help_text='Required. Enter your email address to receive a password reset code.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set Bootstrap classes and placeholders
        self.fields['email'].widget.attrs.update({
            'class': 'form-control form-control-bg',
            'style': 'border: 1px solid black;',
            'placeholder': 'Enter your email'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        User = get_user_model()  # Get the custom user model
        if not User.objects.filter(email=email).exists():
            raise ValidationError('No user is associated with this email address.')
        return email
    



class PasswordResetForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        help_text="Required. Enter your email address."
    )
    reset_code = forms.CharField(
        label="Reset Code",
        help_text="Required. Enter the reset code you received."
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(),
        min_length=8,
        help_text="Required. Minimum length is 8 characters."
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(),
        help_text="Required. Please confirm your new password."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set Bootstrap classes and placeholders
        self.fields['email'].widget.attrs.update({
            'class': 'form-control form-control-bg',
            'style': 'border: 1px solid black;',
            'placeholder': 'Enter your email'
        })
        self.fields['reset_code'].widget.attrs.update({
            'class': 'form-control form-control-bg',
            'style': 'border: 1px solid black;',
            'placeholder': 'Enter your reset code'
        })
        self.fields['new_password'].widget.attrs.update({
            'class': 'form-control form-control-bg',
            'style': 'border: 1px solid black;',
            'placeholder': 'Enter your new password'
        })
        self.fields['confirm_password'].widget.attrs.update({
            'class': 'form-control form-control-bg',
            'style': 'border: 1px solid black;',
            'placeholder': 'Confirm your new password'
        })

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError("The two password fields must match.")

        return cleaned_data

