"""
Views for the planner application.
Handles user authentication, dashboard, plan generation, recipe details, and recipe library.
"""
from datetime import date
import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

from .forms import AccountCredentialsForm, PersonalDetailsForm, GeneratePlanForm
from .models import Recipe, UserProfile, GeneratedPlan, PlanGenerationEvent
from .planner_service import generate_full_meal_plan, calculate_nutritional_targets_from_profile, map_goal_to_cluster
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
            next_url = request.GET.get('next', 'planner:dashboard')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
    
    return render(request, 'planner/login.html', {'form': form})


def logout_view(request):
    """
    Handles user logout.
    
    Securely logs out the user and redirects to the login page.
    """
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    
    return redirect('planner:login')


@login_required
def dashboard_view(request):
    """
    Dashboard view for authenticated users.
    
    Displays:
    - Current meal plan (if exists) with tabbed interface for each day
    - Nutrition overview with donut chart and progress bars
    - Recipe images (fetched/cached from APIs)
    - Explore recipes sidebar
    - Progress tracking (consumed starts at 0)
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
                    
                    # PART 5: Consumed starts at 0 (user will log meals to track progress)
                    # Store nutrition data for Chart.js with targets only (consumed = 0 initially)
                    daily_nutrition_data[day_key] = {
                        'value': {
                            'calories': 0,  # Start at 0 - user will log meals
                            'protein_g': 0,
                            'fat_g': 0,
                            'carbs_g': 0,
                        },
                        'target': daily_targets,
                        'available': {  # Available nutrition from plan (for logging)
                            'calories': round(day_calories, 1),
                            'protein_g': round(day_protein, 1),
                            'fat_g': round(day_fat, 1),
                            'carbs_g': round(day_carbs, 1),
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
    POST: Process form, show calculation transparency, then generate plan
    """
    user = request.user
    
    if request.method == 'POST':
        form = GeneratePlanForm(request.POST, user=user)
        if form.is_valid():
            # Extract form data
            number_of_days = form.cleaned_data['number_of_days']
            primary_goal = form.cleaned_data['primary_goal']
            dietary_style = form.cleaned_data['dietary_style']
            weight_kg = form.cleaned_data.get('weight_kg')
            height_cm = form.cleaned_data.get('height_cm')
            activity_level = form.cleaned_data.get('activity_level')
            allergies = form.cleaned_data.get('allergies', '')
            dislikes = form.cleaned_data.get('dislikes', '')
            
            # Get existing user profile for default values (if exists)
            try:
                user_profile_obj = user.profile
                # Extract existing profile data for defaults
                existing_gender = user_profile_obj.gender or 'male'
                # Use form value if provided, otherwise use profile value, otherwise default
                existing_height_cm = height_cm if height_cm else (user_profile_obj.height_cm if user_profile_obj.height_cm else 170.0)
                existing_activity_level = activity_level if activity_level else (user_profile_obj.activity_level if user_profile_obj.activity_level else 'moderate')
                existing_date_of_birth = user_profile_obj.date_of_birth
            except UserProfile.DoesNotExist:
                # No existing profile - use defaults
                user_profile_obj = None
                existing_gender = 'male'
                existing_height_cm = height_cm if height_cm else 170.0
                existing_activity_level = activity_level if activity_level else 'moderate'
                existing_date_of_birth = None
            
            # Calculate age from date_of_birth if available
            age = 30  # Default age
            if existing_date_of_birth:
                from datetime import date
                today = date.today()
                age = today.year - existing_date_of_birth.year
                # Adjust if birthday hasn't occurred this year
                if today.month < existing_date_of_birth.month or (today.month == existing_date_of_birth.month and today.day < existing_date_of_birth.day):
                    age -= 1
            
            # Use weight from form, or default if not provided
            final_weight_kg = weight_kg if weight_kg else 70.0
            
            # Construct user_profile dictionary EXACTLY as expected by generate_full_meal_plan
            # This dictionary structure matches the validated test command workflow
            user_profile_dict = {
                'age': age,
                'gender': existing_gender,
                'height_cm': existing_height_cm,
                'weight_kg': final_weight_kg,
                'activity_level': existing_activity_level,
                'primary_goal': primary_goal,
                'dietary_style': dietary_style,
                'pace': 'moderate',  # Default pace (can be added to form later)
                'number_of_days': number_of_days,
                'allergies': allergies,  # Pass as string (service will parse)
                'dislikes': dislikes,    # Pass as string (service will parse)
            }
            
            # PART 3: Calculate nutritional targets and show transparency modal
            from .planner_service import calculate_nutritional_targets_from_profile, map_goal_to_cluster
            from .models import Recipe
            
            # Calculate targets
            daily_targets = calculate_nutritional_targets_from_profile(user_profile_dict)
            
            # Calculate BMR and TDEE for display
            gender = existing_gender.lower()
            if gender == 'male':
                bmr = (10 * final_weight_kg) + (6.25 * existing_height_cm) - (5 * age) + 5
            else:
                bmr = (10 * final_weight_kg) + (6.25 * existing_height_cm) - (5 * age) - 161
            
            activity_multipliers = {
                'sedentary': 1.2,
                'light': 1.375,
                'moderate': 1.55,
                'active': 1.725,
                'very_active': 1.9
            }
            multiplier = activity_multipliers.get(existing_activity_level.lower(), 1.55)
            tdee = bmr * multiplier
            
            # Calculate goal adjustment
            goal_adjustments = {
                ('lose_weight', 'fast'): -750,
                ('lose_weight', 'moderate'): -500,
                ('lose_weight', 'mild'): -250,
                ('maintain', 'mild'): 0,
                ('maintain', 'moderate'): 0,
                ('maintain', 'fast'): 0,
                ('gain_muscle', 'mild'): 250,
                ('gain_muscle', 'moderate'): 400,
                ('gain_muscle', 'fast'): 500,
                ('gain_weight', 'mild'): 300,
                ('gain_weight', 'moderate'): 500,
                ('gain_weight', 'fast'): 750
            }
            pace = 'moderate'  # Default
            adjustment_key = (primary_goal, pace)
            goal_adjustment = goal_adjustments.get(adjustment_key, 0)
            
            goal_adjustment_labels = {
                'lose_weight': 'Weight Loss',
                'maintain': 'Weight Maintenance',
                'gain_muscle': 'Muscle Gain',
                'gain_weight': 'Weight Gain'
            }
            goal_adjustment_label = goal_adjustment_labels.get(primary_goal, 'Maintenance')
            
            target_calories = daily_targets['calories']
            
            # Calculate macro percentages
            total_calories = target_calories
            if total_calories > 0:
                protein_pct = (daily_targets['protein_g'] * 4 / total_calories) * 100
                fat_pct = (daily_targets['fat_g'] * 9 / total_calories) * 100
                carbs_pct = (daily_targets['carbs_g'] * 4 / total_calories) * 100
            else:
                protein_pct = fat_pct = carbs_pct = 0
            
            # Get cluster name
            predicted_cluster = map_goal_to_cluster(primary_goal, dietary_style)
            cluster_map = dict(Recipe.objects.values_list('cluster', 'cluster_name').distinct())
            cluster_name = cluster_map.get(predicted_cluster, "Unknown")
            
            # Store calculation data in session for continuation
            request.session['plan_generation_data'] = {
                'user_profile_dict': user_profile_dict,
                'number_of_days': number_of_days,
            }
            request.session.modified = True
            
            # Render calculation transparency page
            context = {
                'bmr': bmr,
                'tdee': tdee,
                'goal_adjustment': goal_adjustment,
                'goal_adjustment_label': goal_adjustment_label,
                'target_calories': target_calories,
                'protein_pct': protein_pct,
                'fat_pct': fat_pct,
                'carbs_pct': carbs_pct,
                'primary_goal': primary_goal,
                'cluster_name': cluster_name,
                'number_of_days': number_of_days,
                'calculation_data': user_profile_dict,  # Pass for form submission
            }
            
            return render(request, 'planner/calculation_transparency.html', context)
    
    else:
        # GET request - display form
        form = GeneratePlanForm(user=user)
    
    # Use app layout for authenticated users
    return render(request, 'planner/generate_plan_form.html', {
        'form': form,
        'user': user,
    })


@login_required
@require_http_methods(["POST"])
def generate_plan_continue_view(request):
    """
    Continue plan generation after showing calculation transparency.
    This view is called from the calculation transparency page.
    """
    user = request.user
    
    # Retrieve data from session
    plan_data = request.session.get('plan_generation_data')
    if not plan_data:
        messages.error(request, 'Session expired. Please start over.')
        return redirect('planner:generate_plan')
    
    user_profile_dict = plan_data['user_profile_dict']
    number_of_days = plan_data['number_of_days']
    
    try:
        # Generate meal plan using the service layer
        # The service handles ALL database operations internally:
        # - Creates/updates UserProfile
        # - Creates PlanGenerationEvent
        # - Creates GeneratedPlan
        weekly_plan = generate_full_meal_plan(
            user_profile=user_profile_dict,
            user_id=user.id
        )
        
        # Clear session data
        request.session.pop('plan_generation_data', None)
        
        if weekly_plan:
            messages.success(request, f'Your {number_of_days}-day meal plan has been generated successfully!')
            return redirect('planner:dashboard')
        else:
            messages.error(request, 'Failed to generate meal plan. Please try again.')
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        messages.error(request, f'Error generating meal plan: {str(e)}')
        # Log error for debugging (in production, use proper logging)
        print(f"[ERROR] Plan generation failed: {e}")
        print(f"[ERROR] Traceback: {error_details}")
        # Clear session on error
        request.session.pop('plan_generation_data', None)
    
    return redirect('planner:dashboard')


@login_required
@require_http_methods(["POST"])
def swap_recipe_view(request):
    """
    PART 2: Smart Swap functionality.
    
    AJAX view that finds a suitable replacement recipe for a given recipe.
    The replacement must:
    - Belong to the same cluster
    - Belong to the same meal_type
    - Have similar nutritional profile
    - Not already be in the user's current plan
    """
    user = request.user
    
    try:
        # Get request data
        recipe_id = int(request.POST.get('recipe_id'))
        meal_name = request.POST.get('meal_name', '')
        day_key = request.POST.get('day_key', '')
        
        # Get the original recipe
        original_recipe = get_object_or_404(Recipe, id=recipe_id)
        original_cluster = original_recipe.cluster
        original_meal_type = original_recipe.meal_type
        
        # Get user's current plan to exclude already-used recipes
        used_recipe_ids = set()
        try:
            user_profile = user.profile
            latest_event = PlanGenerationEvent.objects.filter(
                user_profile=user_profile,
                status='success'
            ).order_by('-created_at').first()
            
            if latest_event:
                current_plan = GeneratedPlan.objects.get(event=latest_event)
                plan_data = current_plan.plan_data
                
                # Collect all recipe IDs from the current plan
                for day_plan in plan_data.values():
                    for meal_recipes in day_plan.values():
                        for recipe_dict in meal_recipes:
                            recipe_id_from_plan = recipe_dict.get('id')
                            if recipe_id_from_plan:
                                used_recipe_ids.add(recipe_id_from_plan)
        except:
            pass
        
        # Find replacement recipes that match cluster and meal_type
        replacement_candidates = Recipe.objects.filter(
            cluster=original_cluster,
            meal_type=original_meal_type
        ).exclude(
            id__in=used_recipe_ids
        ).exclude(
            id=recipe_id  # Exclude the original recipe
        )
        
        if not replacement_candidates.exists():
            return JsonResponse({
                'success': False,
                'error': 'No suitable replacement recipes found'
            }, status=404)
        
        # Calculate nutritional similarity score
        # Use Euclidean distance for calories, protein, fat, carbs
        best_match = None
        best_score = float('inf')
        
        original_calories = original_recipe.avg_calories
        original_protein = original_recipe.avg_protein_g
        original_fat = original_recipe.avg_fat_g
        original_carbs = original_recipe.avg_carbs_g
        
        for candidate in replacement_candidates:
            # Calculate nutritional distance
            cal_diff = abs(candidate.avg_calories - original_calories)
            prot_diff = abs(candidate.avg_protein_g - original_protein)
            fat_diff = abs(candidate.avg_fat_g - original_fat)
            carbs_diff = abs(candidate.avg_carbs_g - original_carbs)
            
            # Weighted distance (protein is more important)
            score = (cal_diff * 0.3) + (prot_diff * 0.4) + (fat_diff * 0.15) + (carbs_diff * 0.15)
            
            if score < best_score:
                best_score = score
                best_match = candidate
        
        if not best_match:
            return JsonResponse({
                'success': False,
                'error': 'No suitable replacement found'
            }, status=404)
        
        # Get image URL for the replacement recipe
        image_url = get_or_fetch_image_url(best_match.id)
        
        # Return JSON response with recipe data
        return JsonResponse({
            'success': True,
            'recipe': {
                'id': best_match.id,
                'name': best_match.name,
                'image_url': image_url,
                'avg_calories': best_match.avg_calories,
                'avg_protein_g': best_match.avg_protein_g,
                'avg_fat_g': best_match.avg_fat_g,
                'avg_carbs_g': best_match.avg_carbs_g,
                'meal_type': best_match.meal_type,
            }
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] Swap recipe failed: {e}")
        print(f"[ERROR] Traceback: {error_details}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def recipe_detail_view(request, recipe_id):
    """
    Display detailed information about a specific recipe.
    """
    recipe = get_object_or_404(Recipe, id=recipe_id)
    image_url = get_or_fetch_image_url(recipe_id)
    
    # Extract ingredients and steps from recipe
    ingredients = recipe.ingredients_list if recipe.ingredients_list else []
    steps = recipe.steps if recipe.steps else []
    
    context = {
        'recipe': recipe,
        'image_url': image_url,
        'ingredients': ingredients,
        'steps': steps,
    }
    
    return render(request, 'planner/recipe_detail.html', context)


@login_required
def recipe_library_view(request):
    """
    Display the recipe library with category cards.
    Each card represents a meal_type category.
    """
    # Get all distinct meal types with counts (exclude empty/null/Unknown)
    meal_types = Recipe.objects.exclude(
        Q(meal_type__isnull=True) | Q(meal_type='') | Q(meal_type='Unknown')
    ).values('meal_type').annotate(
        count=Count('id')
    ).order_by('meal_type')
    
    # Create category data with representative images
    categories = []
    for meal_type_data in meal_types:
        meal_type = meal_type_data['meal_type']
        count = meal_type_data['count']
        
        # Skip if meal_type is empty or None
        if not meal_type or meal_type == 'Unknown':
            continue
        
        # Get a random recipe from this category for the image
        try:
            representative_recipe = Recipe.objects.filter(meal_type=meal_type).order_by('?').first()
            if representative_recipe:
                image_url = get_or_fetch_image_url(representative_recipe.id)
            else:
                image_url = None
        except Exception as e:
            print(f"[RECIPE_LIBRARY] Error fetching image for meal_type '{meal_type}': {e}")
            image_url = None
        
        # Create slug from meal_type
        slug = meal_type.lower().replace(' ', '-').replace('_', '-').replace('/', '-')
        
        # Format meal type name for display
        display_name = meal_type.replace('_', ' ').title()
        if display_name == 'Main Course':
            display_name = 'Main Courses'
        elif display_name == 'Side Dish':
            display_name = 'Side Dishes'
        elif display_name == 'Dessert':
            display_name = 'Desserts'
        elif display_name == 'Drink':
            display_name = 'Drinks'
        elif display_name == 'Snack':
            display_name = 'Snacks'
        
        categories.append({
            'meal_type': meal_type,
            'slug': slug,
            'display_name': display_name,
            'count': count,
            'image_url': image_url,
        })
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'planner/recipe_library.html', context)


@login_required
def recipe_list_by_type_view(request, meal_type_slug):
    """
    Display a paginated list of recipes for a specific meal_type.
    """
    # Get all distinct meal types from database
    all_meal_types = list(Recipe.objects.exclude(
        Q(meal_type__isnull=True) | Q(meal_type='') | Q(meal_type='Unknown')
    ).values_list('meal_type', flat=True).distinct())
    
    # Build mapping from slug to actual meal_type (case-insensitive)
    meal_type_map = {}
    for mt in all_meal_types:
        if mt:
            # Create slug from meal_type
            slug = mt.lower().replace(' ', '-').replace('_', '-').replace('/', '-')
            meal_type_map[slug] = mt
            # Also add common variations
            if 'course' in mt.lower():
                meal_type_map['main-courses'] = mt
                meal_type_map['main-course'] = mt
            if 'dish' in mt.lower():
                meal_type_map['side-dishes'] = mt
                meal_type_map['side-dish'] = mt
    
    # Get meal_type from slug
    meal_type = meal_type_map.get(meal_type_slug.lower())
    
    # If still not found, try case-insensitive database lookup
    if not meal_type:
        # Try various slug transformations
        possible_types = [
            meal_type_slug.replace('-', ' ').title(),
            meal_type_slug.replace('-', '_').title(),
            meal_type_slug.replace('-', ' '),
        ]
        
        for possible_type in possible_types:
            # Case-insensitive lookup
            matching_recipes = Recipe.objects.filter(meal_type__iexact=possible_type)
            if matching_recipes.exists():
                meal_type = matching_recipes.first().meal_type
                break
        
        # If still not found, return 404 or empty list
        if not meal_type:
            from django.http import Http404
            raise Http404(f"Meal type '{meal_type_slug}' not found")
    
    # Get recipes for this meal_type
    recipes = Recipe.objects.filter(meal_type=meal_type).order_by('name')
    
    # Pagination
    paginator = Paginator(recipes, 24)  # 24 recipes per page
    page = request.GET.get('page', 1)
    
    try:
        recipes_page = paginator.page(page)
    except PageNotAnInteger:
        recipes_page = paginator.page(1)
    except EmptyPage:
        recipes_page = paginator.page(paginator.num_pages)
    
    # Get images for recipes on current page
    recipes_with_images = []
    for recipe in recipes_page:
        image_url = get_or_fetch_image_url(recipe.id)
        recipes_with_images.append({
            'id': recipe.id,
            'name': recipe.name,
            'image_url': image_url,
            'avg_calories': recipe.avg_calories,
        })
    
    # Format display name
    display_name = meal_type.replace('_', ' ').title()
    if display_name == 'Main Course':
        display_name = 'Main Courses'
    elif display_name == 'Side Dish':
        display_name = 'Side Dishes'
    
    context = {
        'meal_type': meal_type,
        'meal_type_slug': meal_type_slug,
        'display_name': display_name,
        'recipes': recipes_with_images,
        'recipes_page': recipes_page,
    }
    
    return render(request, 'planner/recipe_list.html', context)
