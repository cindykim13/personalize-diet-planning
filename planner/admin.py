from django.contrib import admin
from .models import Recipe, UserProfile, PlanGenerationEvent, GeneratedPlan


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'meal_type', 'cluster', 'cluster_name', 'avg_calories', 'avg_protein_g')
    list_filter = ('meal_type', 'cluster', 'cluster_name')
    search_fields = ('name',)
    readonly_fields = ('id',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'height_cm', 'activity_level', 'dietary_preferences', 'created_at')
    list_filter = ('gender', 'activity_level', 'dietary_preferences', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PlanGenerationEvent)
class PlanGenerationEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_profile', 'primary_goal', 'pace', 'status', 'predicted_cluster_name', 'created_at')
    list_filter = ('primary_goal', 'pace', 'status', 'predicted_cluster_name', 'created_at')
    search_fields = ('user_profile__user__username',)
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(GeneratedPlan)
class GeneratedPlanAdmin(admin.ModelAdmin):
    list_display = ('event', 'created_at', 'get_number_of_days', 'get_total_calories')
    list_filter = ('created_at',)
    search_fields = ('event__user_profile__user__username',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def get_number_of_days(self, obj):
        """Display number of days in the plan."""
        if obj.plan_data:
            return len(obj.plan_data)
        return 0
    get_number_of_days.short_description = 'Days'
    
    def get_total_calories(self, obj):
        """Display total calories from nutritional summary."""
        if obj.final_nutritional_summary:
            return obj.final_nutritional_summary.get('total_calories', 0)
        return 0
    get_total_calories.short_description = 'Total Calories'
