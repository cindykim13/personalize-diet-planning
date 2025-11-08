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
    path('recipe/<int:recipe_id>/', views.recipe_detail_view, name='recipe_detail'),
]

