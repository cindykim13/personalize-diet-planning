"""
Custom forms for the planner application.
"""
from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class PersonalDetailsForm(forms.Form):
    """Collect personal information for step 1 of the registration wizard."""

    first_name = forms.CharField(
        max_length=150,
        label='First Name',
        help_text='Used to personalise your plan.',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
            'autocomplete': 'given-name',
        }),
    )
    
    last_name = forms.CharField(
        max_length=150,
        label='Last Name',
        help_text='Displayed on your profile.',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
            'autocomplete': 'family-name',
        }),
    )
    
    email = forms.EmailField(
        label='Email Address',
        help_text='We send important plan updates here.',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    
    date_of_birth = forms.DateField(
        label='Date of Birth',
        help_text='Must be at least 13 years old.',
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'autocomplete': 'bday',
        }),
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        label='Phone Number',
        help_text='Optional contact number.',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+1234567890',
            'autocomplete': 'tel',
        }),
    )

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 13:
                raise forms.ValidationError('You must be at least 13 years old to register.')
            if age > 120:
                raise forms.ValidationError('Please enter a realistic date of birth.')
            if dob > today:
                raise forms.ValidationError('Date of birth cannot be in the future.')
        return dob


class AccountCredentialsForm(UserCreationForm):
    """Collect account credentials for step 2 of the registration wizard."""

    username = forms.CharField(
        max_length=20,
        label='Username',
        help_text='Up to 20 characters. Letters, numbers, @/./+/-/_ allowed.',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Choose a username',
            'autocomplete': 'username',
            'maxlength': '20',
        }),
        error_messages={
            'unique': 'That username is already taken.',
            'max_length': 'Use 20 characters or fewer.',
        },
    )
    
    password1 = forms.CharField(
        label='Password',
        help_text='',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
            'id': 'id_password1',
        }),
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        help_text='Repeat your password.',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password',
            'id': 'id_password2',
        }),
    )
    
    class Meta:
        model = User
        fields = ('username',)

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if len(username) > 20:
            raise forms.ValidationError('Use 20 characters or fewer for your username.')
        return username

    def save(self, personal_data: dict, commit: bool = True):
        """Create the user and associated profile using combined form data."""

        user = super().save(commit=False)
        user.email = personal_data.get('email', '')
        user.first_name = personal_data.get('first_name', '')
        user.last_name = personal_data.get('last_name', '')
        
        if commit:
            user.save()

            # Parse date of birth string back to date object
            dob_str = personal_data.get('date_of_birth')
            dob_value = None
            if dob_str:
                try:
                    dob_value = date.fromisoformat(dob_str)
                except ValueError:
                    dob_value = None

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'date_of_birth': dob_value,
                    'phone_number': personal_data.get('phone_number') or None,
                },
            )
        
        return user
