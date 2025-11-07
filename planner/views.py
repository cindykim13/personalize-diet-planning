"""
Views for the planner application.
Handles user authentication and dashboard.
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .forms import AccountCredentialsForm, PersonalDetailsForm


PERSONAL_SESSION_KEY = 'planner_registration_personal'


def register_personal_view(request):
    """Step 1 of the registration wizard: collect personal details."""

    if request.user.is_authenticated:
        return redirect('planner:dashboard')

    existing_data = request.session.get(PERSONAL_SESSION_KEY, {})

    if request.method == 'POST':
        form = PersonalDetailsForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data.copy()
            dob = cleaned.get('date_of_birth')
            cleaned['date_of_birth'] = dob.isoformat() if dob else ''
            request.session[PERSONAL_SESSION_KEY] = cleaned
            request.session.modified = True
            return redirect('planner:register_credentials')
        messages.error(request, 'Please review the highlighted fields.')
    else:
        initial = existing_data.copy()
        dob_str = initial.get('date_of_birth')
        if dob_str:
            try:
                initial['date_of_birth'] = date.fromisoformat(dob_str)
            except ValueError:
                initial.pop('date_of_birth', None)
        form = PersonalDetailsForm(initial=initial)

    return render(request, 'planner/register_step1.html', {'form': form})


def register_credentials_view(request):
    """Step 2 of the registration wizard: collect account credentials."""

    if request.user.is_authenticated:
        return redirect('planner:dashboard')

    personal_data = request.session.get(PERSONAL_SESSION_KEY)
    if not personal_data:
        messages.info(request, 'Please complete your personal details first.')
        return redirect('planner:register')

    if request.method == 'POST':
        form = AccountCredentialsForm(request.POST)
        if form.is_valid():
            user = form.save(personal_data=personal_data)
            login(request, user)
            first_name = user.first_name or user.username
            messages.success(request, f'Welcome, {first_name}! Your account is ready.')
            request.session.pop(PERSONAL_SESSION_KEY, None)
            return redirect('planner:dashboard')
        messages.error(request, 'Please fix the issues below and try again.')
    else:
        form = AccountCredentialsForm()

    return render(request, 'planner/register_step2.html', {'form': form})


def login_view(request):
    """
    Handles user login.
    
    Uses Django's AuthenticationForm which provides:
    - Secure authentication
    - CSRF protection
    - Error handling for invalid credentials
    """
    if request.user.is_authenticated:
        # If user is already logged in, redirect to dashboard
        return redirect('planner:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # Get the user from the form
            user = form.get_user()
            # Log the user in (creates session)
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            # Redirect to the page the user was trying to access, or dashboard
            next_url = request.GET.get('next', None)
            if next_url:
                return redirect(next_url)
            return redirect('planner:dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'planner/login.html', {'form': form})


def logout_view(request):
    """
    Handles user logout.
    
    Uses Django's logout function which:
    - Flushes the user's session data
    - Prevents session hijacking
    - Clears authentication cookies
    """
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'You have been successfully logged out, {username}.')
    
    return redirect('planner:login')


@login_required
def dashboard_view(request):
    """
    Dashboard view for authenticated users.
    
    Protected by @login_required decorator which:
    - Redirects unauthenticated users to LOGIN_URL
    - Ensures only logged-in users can access this view
    """
    return render(request, 'planner/dashboard.html', {
        'user': request.user
    })
