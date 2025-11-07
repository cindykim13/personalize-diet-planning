# planner/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Recipe(models.Model):
    """
    Master library of all processed and labeled recipes.
    Standalone table containing recipe data with nutritional features and cluster labels.
    """
    # Thông tin định danh và hiển thị
    name = models.CharField(max_length=500)
    steps = models.JSONField(default=list)
    ingredients_list = models.JSONField(default=list)
    meal_type = models.CharField(max_length=50, default='Unknown')

    # Các đặc trưng dinh dưỡng (từ EDA)
    protein_percent = models.FloatField(default=0.0)
    fat_percent = models.FloatField(default=0.0)
    carbs_percent = models.FloatField(default=0.0)
    avg_sugar_g = models.FloatField(default=0.0)
    avg_fiber_g = models.FloatField(default=0.0)
    
    # Nhãn cụm
    cluster = models.IntegerField()
    cluster_name = models.CharField(max_length=100)

    # Giá trị calo trung bình (để tham khảo và tối ưu hóa)
    avg_calories = models.FloatField(default=0.0)
    
    # Các giá trị gram trung bình (để tham khảo)
    avg_protein_g = models.FloatField(default=0.0)
    avg_fat_g = models.FloatField(default=0.0)
    avg_carbs_g = models.FloatField(default=0.0)

    def __str__(self):
        return self.name

    class Meta:
        # Tên bảng trong PostgreSQL sẽ là 'planner_recipe'
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"


class UserProfile(models.Model):
    """
    Stores static demographic and biometric data for a user.
    One-to-One relationship with Django's built-in User model.
    """
    # Gender choices
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    # Activity level choices
    ACTIVITY_LEVEL_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('light', 'Light'),
        ('moderate', 'Moderate'),
        ('active', 'Active'),
        ('very_active', 'Very Active'),
    ]
    
    # Dietary preference choices
    DIETARY_PREFERENCE_CHOICES = [
        ('none', 'None'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('pescatarian', 'Pescatarian'),
        ('keto', 'Keto'),
        ('paleo', 'Paleo'),
        ('mediterranean', 'Mediterranean'),
    ]
    
    # One-to-One relationship with User (acts as Primary Key)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='profile',
        verbose_name='User'
    )
    
    # Demographic and biometric data
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date of Birth'
    )
    
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
        verbose_name='Gender'
    )
    
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Phone Number',
        help_text='Optional: Enter your phone number (e.g., +1234567890)'
    )
    
    height_cm = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(50.0), MaxValueValidator(250.0)],
        verbose_name='Height (cm)'
    )
    
    activity_level = models.CharField(
        max_length=20,
        choices=ACTIVITY_LEVEL_CHOICES,
        default='moderate',
        verbose_name='Activity Level'
    )
    
    # Dietary restrictions and preferences
    allergies = models.JSONField(
        default=list,
        blank=True,
        help_text='List of allergies (e.g., ["peanuts", "shellfish"])',
        verbose_name='Allergies'
    )
    
    dislikes = models.JSONField(
        default=list,
        blank=True,
        help_text='List of disliked foods (e.g., ["lamb", "bitter melon"])',
        verbose_name='Dislikes'
    )
    
    dietary_preferences = models.CharField(
        max_length=20,
        choices=DIETARY_PREFERENCE_CHOICES,
        default='none',
        verbose_name='Dietary Preferences'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        db_table = 'planner_userprofile'


class PlanGenerationEvent(models.Model):
    """
    A log of every plan generation request. This is the core of our Data Flywheel.
    Many-to-One relationship with UserProfile. One UserProfile can have many PlanGenerationEvent instances.
    """
    # Goal choices
    PRIMARY_GOAL_CHOICES = [
        ('lose_weight', 'Lose Weight'),
        ('maintain', 'Maintain Weight'),
        ('gain_muscle', 'Gain Muscle'),
    ]
    
    # Pace choices
    PACE_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('fast', 'Fast'),
    ]
    
    # Status choices
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('fallback_default', 'Fallback Default'),
        ('failed', 'Failed'),
        ('infeasible', 'Infeasible'),
        ('timeout', 'Timeout'),
    ]
    
    # Primary Key (AutoField)
    id = models.AutoField(primary_key=True)
    
    # Many-to-One relationship with UserProfile
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name='plan_generation_events',
        verbose_name='User Profile'
    )
    
    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    # Plan generation parameters
    primary_goal = models.CharField(
        max_length=20,
        choices=PRIMARY_GOAL_CHOICES,
        verbose_name='Primary Goal'
    )
    
    pace = models.CharField(
        max_length=20,
        choices=PACE_CHOICES,
        default='moderate',
        verbose_name='Pace'
    )
    
    weight_kg_at_request = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(20.0), MaxValueValidator(300.0)],
        verbose_name='Weight (kg) at Request'
    )
    
    # Calculated targets (stored as JSON)
    calculated_targets = models.JSONField(
        default=dict,
        blank=True,
        help_text='Calculated nutritional targets (calories, protein_g, fat_g, carbs_g)',
        verbose_name='Calculated Targets'
    )
    
    # Cluster prediction
    predicted_cluster_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Predicted Cluster Name'
    )
    
    # Status of plan generation
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='success',
        verbose_name='Status'
    )
    
    # Additional metadata
    number_of_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name='Number of Days'
    )
    
    def __str__(self):
        return f"Plan Generation Event #{self.id} for {self.user_profile.user.username} ({self.created_at})"
    
    class Meta:
        verbose_name = "Plan Generation Event"
        verbose_name_plural = "Plan Generation Events"
        db_table = 'planner_plangenerationevent'
        ordering = ['-created_at']  # Most recent first


class GeneratedPlan(models.Model):
    """
    Stores the successful output of a plan generation event.
    One-to-One relationship with PlanGenerationEvent. Each successful PlanGenerationEvent has exactly one GeneratedPlan.
    """
    # One-to-One relationship with PlanGenerationEvent (acts as Primary Key)
    event = models.OneToOneField(
        PlanGenerationEvent,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='generated_plan',
        verbose_name='Plan Generation Event'
    )
    
    # Plan data (entire multi-day meal plan dictionary)
    plan_data = models.JSONField(
        default=dict,
        help_text='Complete multi-day meal plan structure (Day 1, Day 2, etc.)',
        verbose_name='Plan Data'
    )
    
    # Final nutritional summary
    final_nutritional_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text='Actual nutritional totals of the generated plan',
        verbose_name='Final Nutritional Summary'
    )
    
    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    def __str__(self):
        return f"Generated Plan for Event #{self.event.id}"
    
    class Meta:
        verbose_name = "Generated Plan"
        verbose_name_plural = "Generated Plans"
        db_table = 'planner_generatedplan'