# Authentication System Setup and Verification Guide

## Overview

This document provides step-by-step instructions for verifying the complete authentication system implementation for the CNutrition application.

## Files Created/Modified

### 1. URL Routing
- **`core/urls.py`**: Updated to include planner app URLs and static file serving
- **`planner/urls.py`**: Created with authentication routes (`/register/`, `/login/`, `/logout/`, `/`)

### 2. Backend Views
- **`planner/views.py`**: Implements authentication views using Django's built-in auth framework:
  - `register_personal_view`: Step 1 of the wizard – personal details
  - `register_credentials_view`: Step 2 of the wizard – account credentials
  - `login_view`: Handles user login with `AuthenticationForm`
  - `logout_view`: Handles secure logout
  - `dashboard_view`: Protected dashboard for authenticated users

### 3. Frontend Templates
- **`planner/templates/planner/base.html`**: Master template with navigation bar and refreshed branding
- **`planner/templates/planner/register_step1.html`**: Registration wizard – Step 1 (Personal Details)
- **`planner/templates/planner/register_step2.html`**: Registration wizard – Step 2 (Account Credentials)
- **`planner/templates/planner/login.html`**: Login form page
- **`planner/templates/planner/dashboard.html`**: User dashboard page

### 4. Settings Configuration
- **`core/settings.py`**: Updated with:
  - Static files configuration
  - Login/Logout URL redirects
  - Template context processors

## Security Features Implemented

✅ **Password Hashing**: Django's `UserCreationForm` automatically uses PBKDF2 algorithm
✅ **Password Validation**: Enforced by Django's built-in validators (minimum length, common passwords, etc.)
✅ **CSRF Protection**: All forms include CSRF tokens
✅ **Session Management**: Secure session handling via Django's authentication framework
✅ **Password Confirmation**: Registration form includes password confirmation field

## Verification Steps

### Step 1: Start the Django Development Server

```bash
cd "/Users/nguyenthuong/Documents/DietPlanning copy"
source env-tf/bin/activate  # Activate virtual environment
python manage.py runserver
```

The server should start without errors and be accessible at `http://127.0.0.1:8000/`

### Step 2: Verify Static Files Configuration

1. Open your browser and navigate to: `http://127.0.0.1:8000/`
2. Check that the CNutrition logo appears in the navigation bar
3. If the logo doesn't appear, check:
   - Logo file exists at: `static/CNutrition.png`
   - Static files are being served (check Django console for static file errors)

### Step 3: Test User Registration (Two-Step Wizard)

1. **Navigate to Registration Page**:
   - Go to: `http://127.0.0.1:8000/register/`
   - Or click "Register" in the navigation bar

2. **Step 1 – Personal Details**:
   - Fill in `First Name`, `Last Name`, `Email`, `Date of Birth`, and optionally `Phone Number`
   - Click **Continue**
   - If validation fails (e.g., under 13 years old), errors will appear inline

3. **Step 2 – Account Credentials**:
   - Choose a username (max 20 characters)
   - Create a password and watch the live password checklist update as you type
   - Confirm the password
   - Use the **Back** button if you need to adjust Step 1 details (data is preserved)

4. **Password Validation Tests**:
   - Enter weak passwords (e.g., `123`, `password`) and confirm that the checklist and Django validators reject them
   - Enter mismatched passwords to confirm you see: "The two password fields didn't match."

5. **Successful Registration**:
   - Provide a strong password (e.g., `SecurePass123!`)
   - Submit the form using **Create Account**
   - You should be automatically logged in and redirected to the dashboard
   - A success message will display: "Welcome, <username>! Your account is ready."

### Step 4: Verify Password Hashing in Database

1. **Access Django Admin or Database**:
   ```bash
   python manage.py shell
   ```

2. **Check User Password Hash**:
   ```python
   from django.contrib.auth.models import User
   user = User.objects.get(username='testuser')
   print(f"Username: {user.username}")
   print(f"Password hash: {user.password}")
   print(f"Password hash length: {len(user.password)}")
   ```

3. **Verify Password Hash**:
   - The password field should contain a long string starting with `pbkdf2_sha256$`
   - The hash should be approximately 88-100 characters long
   - **CRITICAL**: The plain-text password should NOT be visible anywhere in the database

4. **Verify Password Validation**:
   ```python
   from django.contrib.auth import authenticate
   # This should return the user object if password is correct
   user = authenticate(username='testuser', password='SecurePass123!')
   print(f"Authentication successful: {user is not None}")
   # This should return None if password is incorrect
   user = authenticate(username='testuser', password='WrongPassword')
   print(f"Wrong password returns None: {user is None}")
   ```

### Step 5: Test User Login

1. **Logout** (if still logged in):
   - Click "Logout" in the navigation bar
   - You should be redirected to the login page
   - Success message: "You have been successfully logged out, testuser."

2. **Test Invalid Credentials**:
   - Go to: `http://127.0.0.1:8000/login/`
   - Enter incorrect username or password
   - Submit the form
   - Error message should appear: "Invalid username or password. Please try again."

3. **Test Valid Credentials**:
   - Enter correct username: "testuser"
   - Enter correct password: "SecurePass123!"
   - Submit the form
   - You should be redirected to the dashboard
   - Success message: "Welcome back, testuser!"

### Step 6: Test Protected Views

1. **Access Dashboard While Logged Out**:
   - Logout if currently logged in
   - Try to access: `http://127.0.0.1:8000/`
   - You should be redirected to: `http://127.0.0.1:8000/login/?next=/`
   - After logging in, you should be redirected back to the dashboard

2. **Verify Session Persistence**:
   - Login successfully
   - Navigate to different pages
   - Refresh the page
   - You should remain logged in (username should appear in navbar)

### Step 7: Test Navigation Bar Dynamic Display

1. **While Logged Out**:
   - Navigation bar should show: "Register" and "Login" buttons

2. **While Logged In**:
   - Navigation bar should show: "Dashboard", "Create Plan", "Logout" buttons
   - Your username should be displayed

## Expected Database State

After successful registration, check the `auth_user` table:

```sql
SELECT id, username, password, date_joined, is_active 
FROM auth_user 
WHERE username = 'testuser';
```

**Expected Results**:
- `username`: The username you registered
- `password`: A long hashed string (starting with `pbkdf2_sha256$`)
- `date_joined`: Current timestamp
- `is_active`: `true`

## Troubleshooting

### Issue: Logo Not Displaying
- **Solution**: Ensure `CNutrition.png` exists in the `static/` directory
- Run: `python manage.py collectstatic` (if in production)
- Check browser console for 404 errors on static files

### Issue: Forms Not Displaying
- **Solution**: Check that `planner/templates/planner/` directory exists
- Verify template files are named correctly (case-sensitive)

### Issue: CSRF Token Error
- **Solution**: Ensure `{% csrf_token %}` is included in all forms
- Check that `CsrfViewMiddleware` is in `MIDDLEWARE` in `settings.py`

### Issue: Password Validation Not Working
- **Solution**: Verify `AUTH_PASSWORD_VALIDATORS` in `settings.py` contains all validators
- Check Django console for validation errors

### Issue: Redirect Loop
- **Solution**: Verify `LOGIN_URL` and `LOGIN_REDIRECT_URL` in `settings.py` are correct
- Check that authentication middleware is enabled

## Security Checklist

✅ Passwords are hashed using PBKDF2 (never stored in plain text)
✅ Password validation is enforced (minimum length, common passwords, etc.)
✅ CSRF protection is enabled on all forms
✅ Sessions are securely managed
✅ Protected views require authentication
✅ Logout properly clears session data
✅ Password confirmation prevents typos
✅ Error messages don't reveal sensitive information

## Next Steps

After verifying the authentication system:

1. **Create User Profile Form**: Allow users to update their profile information
2. **Implement Meal Plan Generation**: Connect the dashboard to the backend meal plan generator
3. **Add Plan History View**: Display previously generated meal plans
4. **Enhance UI/UX**: Add more styling and interactive elements

## Support

If you encounter any issues during verification, check:
- Django console output for error messages
- Browser developer console for JavaScript/CSS errors
- Database connection in `settings.py`
- Virtual environment is activated
- All dependencies are installed

