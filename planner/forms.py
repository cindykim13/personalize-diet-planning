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

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    first_name = forms.CharField(
        max_length=150,
        label='First Name',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
            'autocomplete': 'given-name',
        }),
    )
    
    last_name = forms.CharField(
        max_length=150,
        label='Last Name',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
            'autocomplete': 'family-name',
        }),
    )
    
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    
    date_of_birth = forms.DateField(
        label='Date of Birth',
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
            'autocomplete': 'bday',
        }),
    )

    gender = forms.ChoiceField(
        label='Gender',
        choices=GENDER_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'gender-input',
        }),
    )

    country_code = forms.CharField(
        max_length=5,
        required=False,
        initial='+1',
        widget=forms.HiddenInput(),
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-input phone-input',
            'placeholder': 'Phone number',
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
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
            'id': 'id_password1',
        }),
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
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


class GeneratePlanForm(forms.Form):
    """Form for generating a new meal plan."""
    
    PRIMARY_GOAL_CHOICES = [
        ('lose_weight', 'Lose Weight'),
        ('maintain', 'Maintain Weight'),
        ('gain_muscle', 'Gain Muscle'),
        ('gain_weight', 'Gain Weight'),
    ]
    
    DIETARY_STYLE_CHOICES = [
        ('balanced', 'Balanced'),
        ('low_carb', 'Low Carb'),
        ('low_fat', 'Low Fat'),
    ]
    
    PACE_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('fast', 'Fast'),
    ]
    
    number_of_days = forms.IntegerField(
        label='Number of Days',
        min_value=1,
        max_value=30,
        initial=7,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'min': '1',
            'max': '30'
        }),
        help_text='How many days would you like your meal plan to cover? (1-30 days)'
    )
    
    primary_goal = forms.ChoiceField(
        label='Primary Goal',
        choices=PRIMARY_GOAL_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        help_text='What is your primary health and fitness goal?'
    )
    
    weight_kg = forms.FloatField(
        label='Current Weight (kg)',
        required=False,
        min_value=20.0,
        max_value=300.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.1',
            'placeholder': 'e.g., 70.5'
        }),
        help_text='Optional: Your current weight in kilograms (used for calorie calculations)'
    )
    
    height_cm = forms.FloatField(
        label='Height (cm)',
        required=False,
        min_value=50.0,
        max_value=250.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.1',
            'placeholder': 'e.g., 175.0'
        }),
        help_text='Optional: Your height in centimeters (used for BMR calculation)'
    )
    
    ACTIVITY_LEVEL_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('light', 'Light'),
        ('moderate', 'Moderate'),
        ('active', 'Active'),
        ('very_active', 'Very Active'),
    ]
    
    activity_level = forms.ChoiceField(
        label='Activity Level',
        choices=ACTIVITY_LEVEL_CHOICES,
        required=False,
        initial='moderate',
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        help_text='Your daily activity level (used for TDEE calculation)'
    )
    
    dietary_style = forms.ChoiceField(
        label='Dietary Style',
        choices=DIETARY_STYLE_CHOICES,
        initial='balanced',
        widget=forms.Select(attrs={
            'class': 'form-input'
        }),
        help_text='Choose your preferred dietary approach.'
    )
    
    allergies = forms.CharField(
        label='Allergies',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., peanuts, shellfish, dairy'
        }),
        help_text='List any food allergies (comma-separated). Leave blank if none.'
    )
    
    dislikes = forms.CharField(
        label='Dislikes',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g., lamb, bitter melon, mushrooms'
        }),
        help_text='List any foods you dislike (comma-separated). Leave blank if none.'
    )
    
    def __init__(self, *args, **kwargs):
        """Initialize form with user's current preferences."""
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate with user's profile data if available
        if user:
            try:
                profile = user.profile
                # Set initial values from profile
                if profile.allergies:
                    self.fields['allergies'].initial = ', '.join(profile.allergies) if isinstance(profile.allergies, list) else profile.allergies
                if profile.dislikes:
                    self.fields['dislikes'].initial = ', '.join(profile.dislikes) if isinstance(profile.dislikes, list) else profile.dislikes
                # Pre-populate height from profile
                if profile.height_cm:
                    self.fields['height_cm'].initial = profile.height_cm
                # Pre-populate activity level from profile
                if profile.activity_level:
                    self.fields['activity_level'].initial = profile.activity_level
                # Get weight from latest plan generation event if available
                from .models import PlanGenerationEvent
                try:
                    latest_event = PlanGenerationEvent.objects.filter(
                        user_profile=profile
                    ).order_by('-created_at').first()
                    if latest_event and latest_event.weight_kg_at_request:
                        self.fields['weight_kg'].initial = latest_event.weight_kg_at_request
                except:
                    pass
            except UserProfile.DoesNotExist:
                pass
