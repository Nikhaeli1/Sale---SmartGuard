from django.db import models
from django.utils import timezone


class BuildingType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Building(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    building_type = models.ForeignKey(
        BuildingType,
        on_delete=models.CASCADE,
        related_name='buildings'
    )

    def __str__(self):
        return f"{self.name} ({self.building_type.name})"


class Sensor(models.Model):
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name='sensors'
    )
    sensor_label = models.CharField(max_length=100)
    appliance_name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.sensor_label} - {self.appliance_name} @ {self.building.name}"


class EnergyReading(models.Model):
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='readings'
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    voltage = models.FloatField()
    current = models.FloatField()
    power_watts = models.FloatField()
    power_factor = models.FloatField(default=1.0)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.power_watts:.1f}W @ {self.timestamp}"


class Anomaly(models.Model):
    ANOMALY_TYPES = [
        ('SPIKE', 'Sudden Power Spike'),
        ('OVERLOAD', 'Prolonged Overloading'),
        ('ABNORMAL', 'Abnormal Consumption Pattern'),
        ('LOW_PF', 'Low Power Factor'),
        ('VOLTAGE_SAG', 'Voltage Sag'),
        ('VOLTAGE_SWELL', 'Voltage Swell'),
    ]
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='anomalies'
    )
    reading = models.ForeignKey(
        EnergyReading,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anomalies'
    )
    anomaly_type = models.CharField(max_length=20, choices=ANOMALY_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    description = models.TextField()
    detected_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Anomalies'

    def __str__(self):
        return f"{self.get_anomaly_type_display()} [{self.severity}]"


class Alert(models.Model):
    ALERT_TYPES = [
        ('ANOMALY', 'Anomaly Alert'),
        ('MAINTENANCE', 'Maintenance Reminder'),
        ('THRESHOLD', 'Threshold Exceeded'),
        ('SYSTEM', 'System Notification'),
    ]

    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts'
    )
    anomaly = models.ForeignKey(
        Anomaly,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts'
    )
    alert_type = models.CharField(max_length=15, choices=ALERT_TYPES)
    message = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)
    acknowledged = models.BooleanField(default=False)

    def __str__(self):
        return f"Alert [{self.alert_type}] - {self.building.name}"