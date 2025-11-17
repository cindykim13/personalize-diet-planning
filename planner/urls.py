"""
URL configuration for planner app.
"""
from django.urls import path
from . import views

app_name = 'planner'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('register/', views.register_personal_view, name='register'),
    path('register/credentials/', views.register_credentials_view, name='register_credentials'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('generate-plan/', views.generate_plan_view, name='generate_plan'),
    path('generate-plan/continue/', views.generate_plan_continue_view, name='generate_plan_continue'),
    path('swap-recipe/', views.swap_recipe_view, name='swap_recipe'),
    path('recipe/<int:recipe_id>/', views.recipe_detail_view, name='recipe_detail'),
    path('recipes/', views.recipe_library_view, name='recipe_library'),
    path('recipes/<str:meal_type_slug>/', views.recipe_list_by_type_view, name='recipe_list_by_type'),
]

