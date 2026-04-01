from django.contrib import admin
from .models import (
    BuildingType, Building, Sensor,
    EnergyReading, Anomaly, Alert
)


@admin.register(BuildingType)
class BuildingTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'building_type', 'address']
    list_filter = ['building_type']


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ['id', 'sensor_label', 'appliance_name', 'building']
    list_filter = ['building']


@admin.register(EnergyReading)
class EnergyReadingAdmin(admin.ModelAdmin):
    list_display = ['id', 'sensor', 'timestamp', 'voltage', 'current', 'power_watts', 'power_factor']
    list_filter = ['sensor__building']
    list_per_page = 50


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ['id', 'anomaly_type', 'severity', 'sensor', 'detected_at', 'resolved']
    list_filter = ['anomaly_type', 'severity', 'resolved']


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['id', 'alert_type', 'building', 'sent_at', 'acknowledged']
    list_filter = ['alert_type', 'acknowledged']