from django.urls import path
from . import views

app_name = 'smartguard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('building/<int:building_id>/', views.building_detail, name='building_detail'),
    path('generate/', views.generate_random_data, name='generate_data'),
]