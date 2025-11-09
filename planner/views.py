"""
Views for the planner application.
Handles user authentication, dashboard, plan generation, and recipe details.
"""
from datetime import date
import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
import json

from .forms import AccountCredentialsForm, PersonalDetailsForm, GeneratePlanForm
from .models import Recipe, UserProfile, GeneratedPlan, PlanGenerationEvent
from .planner_service import generate_full_meal_plan
from .image_service import get_or_fetch_image_url, get_image_url_for_recipe_dict


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
    
    Displays:
    - Current meal plan (if exists) with tabbed interface for each day
    - Pie charts for daily macronutrient breakdown
    - Recipe images (fetched/cached from Unsplash)
    - Explore recipes sidebar
    """
    user = request.user
    
    # Get user's profile
    try:
        user_profile = user.profile
    except UserProfile.DoesNotExist:
        user_profile = None
    
    # Get most recent GeneratedPlan for the user
    current_plan = None
    plan_data = None
    plan_with_images = None
    daily_nutrition_data = {}
    
    if user_profile:
        # Get most recent plan generation event for this user
        latest_event = PlanGenerationEvent.objects.filter(
            user_profile=user_profile,
            status='success'
        ).order_by('-created_at').first()
        
        if latest_event:
            try:
                current_plan = GeneratedPlan.objects.get(event=latest_event)
                plan_data = current_plan.plan_data
                
                # Process plan data to add images and calculate nutrition
                plan_with_images = {}
                daily_nutrition_data = {}
                
                for day_key, day_plan in plan_data.items():
                    day_with_images = {}
                    day_calories = 0
                    day_protein = 0
                    day_fat = 0
                    day_carbs = 0
                    
                    for meal_name, recipes in day_plan.items():
                        meal_recipes = []
                        
                        for recipe_dict in recipes:
                            # Get recipe ID to fetch Recipe object for caching
                            recipe_id = recipe_dict.get('id')
                            recipe_obj = None
                            
                            if recipe_id:
                                # Get or fetch image URL (caches in database) - uses recipe_id
                                image_url = get_or_fetch_image_url(recipe_id)
                            else:
                                # No ID, use dictionary-based fetching
                                image_url = get_image_url_for_recipe_dict(recipe_dict)
                            
                            # Add image URL to recipe dictionary
                            recipe_dict_with_image = recipe_dict.copy()
                            recipe_dict_with_image['image_url'] = image_url
                            
                            # Accumulate nutrition data
                            day_calories += recipe_dict.get('avg_calories', 0)
                            day_protein += recipe_dict.get('avg_protein_g', 0)
                            day_fat += recipe_dict.get('avg_fat_g', 0)
                            day_carbs += recipe_dict.get('avg_carbs_g', 0)
                            
                            meal_recipes.append(recipe_dict_with_image)
                        
                        day_with_images[meal_name] = meal_recipes
                    
                    plan_with_images[day_key] = day_with_images
                    
                    # Calculate macro percentages for pie chart
                    total_grams = day_protein + day_fat + day_carbs
                    if total_grams > 0:
                        protein_pct = (day_protein / total_grams) * 100
                        fat_pct = (day_fat / total_grams) * 100
                        carbs_pct = (day_carbs / total_grams) * 100
                    else:
                        protein_pct = fat_pct = carbs_pct = 0
                    
                    # Get daily targets from latest event
                    daily_targets = {
                        'calories': 2200,
                        'protein_g': 150,
                        'carbs_g': 300,
                        'fat_g': 65,
                    }
                    
                    if latest_event and latest_event.calculated_targets:
                        try:
                            targets = latest_event.calculated_targets
                            daily_targets = {
                                'calories': targets.get('calories', 2200),
                                'protein_g': targets.get('protein_g', 150),
                                'carbs_g': targets.get('carbs_g', 300),
                                'fat_g': targets.get('fat_g', 65),
                            }
                        except:
                            pass
                    
                    # Store nutrition data for Chart.js with values and targets
                    daily_nutrition_data[day_key] = {
                        'value': {
                            'calories': round(day_calories, 1),
                            'protein_g': round(day_protein, 1),
                            'fat_g': round(day_fat, 1),
                            'carbs_g': round(day_carbs, 1),
                        },
                        'target': daily_targets,
                        'percentages': {
                            'protein': round(protein_pct, 1),
                            'fat': round(fat_pct, 1),
                            'carbs': round(carbs_pct, 1),
                        }
                    }
                
            except GeneratedPlan.DoesNotExist:
                current_plan = None
                plan_data = None
    
    # Get 4 random recipes for "Explore Recipes" card
    explore_recipes = Recipe.objects.order_by('?')[:4]
    explore_recipes_with_images = []
    
    for recipe in explore_recipes:
        image_url = get_or_fetch_image_url(recipe.id)
        explore_recipes_with_images.append({
            'id': recipe.id,
            'name': recipe.name,
            'image_url': image_url,
            'avg_calories': recipe.avg_calories,
        })
    
    # Convert plan_data to JSON-safe format
    import json as json_module
    plan_data_json = json_module.dumps(plan_with_images) if plan_with_images else '{}'
    nutrition_data_json = json_module.dumps(daily_nutrition_data) if daily_nutrition_data else '{}'
    
    context = {
        'user': user,
        'user_profile': user_profile,
        'current_plan': current_plan,
        'plan_data': plan_with_images,
        'plan_data_json': plan_data_json,
        'daily_nutrition_data': nutrition_data_json,
        'explore_recipes': explore_recipes_with_images,
    }
    
    # Use new dashboard template for authenticated users
    return render(request, 'planner/dashboard_new.html', context)


@login_required
def generate_plan_view(request):
    """
    Handle plan generation form display and processing.
    
    GET: Display the form
    POST: Process form, generate plan, and redirect to dashboard
    """
    user = request.user
    
    if request.method == 'POST':
        form = GeneratePlanForm(request.POST, user=user)
        
        if form.is_valid():
            # Get user profile data
            try:
                user_profile_obj = user.profile
                age = None
                if user_profile_obj.date_of_birth:
                    today = date.today()
                    age = today.year - user_profile_obj.date_of_birth.year - (
                        (today.month, today.day) < (user_profile_obj.date_of_birth.month, user_profile_obj.date_of_birth.day)
                    )
                gender = user_profile_obj.gender
                height_cm = user_profile_obj.height_cm
                # Get weight from form or latest plan generation event, or use None
                weight_kg = form.cleaned_data.get('weight_kg')
                if not weight_kg:
                    try:
                        latest_event = PlanGenerationEvent.objects.filter(
                            user_profile=user_profile_obj
                        ).order_by('-created_at').first()
                        if latest_event:
                            weight_kg = latest_event.weight_kg_at_request
                    except:
                        pass
                activity_level = user_profile_obj.activity_level
                allergies = ', '.join(user_profile_obj.allergies) if isinstance(user_profile_obj.allergies, list) else (user_profile_obj.allergies or '')
                dislikes = ', '.join(user_profile_obj.dislikes) if isinstance(user_profile_obj.dislikes, list) else (user_profile_obj.dislikes or '')
            except UserProfile.DoesNotExist:
                # Use defaults if profile doesn't exist
                age = 30
                gender = 'male'
                height_cm = 170
                weight_kg = 70
                activity_level = 'moderate'
                allergies = ''
                dislikes = ''
            
            # Build user_profile dictionary for service layer
            user_profile = {
                'age': age or 30,
                'gender': gender or 'male',
                'height_cm': height_cm or 170,
                'weight_kg': weight_kg or 70,
                'activity_level': activity_level or 'moderate',
                'primary_goal': form.cleaned_data['primary_goal'],
                'dietary_style': form.cleaned_data['dietary_style'],
                'pace': 'moderate',  # Can be added to form later
                'number_of_days': form.cleaned_data['number_of_days'],
                'allergies': form.cleaned_data.get('allergies', '') or allergies,
                'dislikes': form.cleaned_data.get('dislikes', '') or dislikes,
            }
            
            try:
                # Call service layer to generate plan
                # This may take some time, but for this implementation we do it synchronously
                weekly_plan = generate_full_meal_plan(user_profile, user_id=user.id)
                
                # Plan generation successful - redirect to dashboard
                messages.success(request, f'Your {form.cleaned_data["number_of_days"]}-day meal plan has been generated successfully!')
                return redirect('planner:dashboard')
                
            except Exception as e:
                # Plan generation failed
                messages.error(request, f'Error generating meal plan: {str(e)}. Please try again.')
                print(f"[VIEWS] Error generating plan: {e}")
    
    else:
        # GET request - display form
        form = GeneratePlanForm(user=user)
    
    # Use app layout for authenticated users
    return render(request, 'planner/generate_plan_form.html', {
        'form': form,
        'user': user,
    })


@login_required
def recipe_detail_view(request, recipe_id):
    """
    Display detailed information about a specific recipe.
    
    :param recipe_id: ID of the recipe to display
    """
    recipe = get_object_or_404(Recipe, id=recipe_id)
    
    # Get or fetch image URL
    image_url = get_or_fetch_image_url(recipe_id)
    
    # Parse ingredients and steps (they're stored as JSON)
    ingredients = recipe.ingredients_list if isinstance(recipe.ingredients_list, list) else []
    steps = recipe.steps if isinstance(recipe.steps, list) else []
    
    context = {
        'recipe': recipe,
        'image_url': image_url,
        'ingredients': ingredients,
        'steps': steps,
    }
    
    return render(request, 'planner/recipe_detail.html', context)
