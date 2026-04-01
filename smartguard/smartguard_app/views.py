import random
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Avg, Max, Count, F, Q
from .models import Building, Sensor, EnergyReading, Anomaly, Alert


def dashboard(request):
    context = {
        'building_count': Building.objects.count(),
        'sensor_count': Sensor.objects.count(),
        'reading_count': EnergyReading.objects.count(),
        'anomaly_count': Anomaly.objects.count(),
        'alert_count': Alert.objects.count(),
        'buildings': Building.objects.select_related('building_type').all(),
        'recent_anomalies': Anomaly.objects.select_related(
            'sensor', 'sensor__building'
        ).order_by('-detected_at')[:10],
        'recent_readings': EnergyReading.objects.select_related(
            'sensor', 'sensor__building'
        ).order_by('-timestamp')[:15],
    }
    return render(request, 'smartguard_template/dashboard.html', context)


def building_detail(request, building_id):
    building = get_object_or_404(Building, id=building_id)

    sensor_stats = []
    for sensor in building.sensors.all():
        stats = sensor.readings.aggregate(
            avg_power=Avg('power_watts'),
            max_power=Max('power_watts'),
            avg_pf=Avg('power_factor'),
            count=Count('id'),
        )
        stats['sensor'] = sensor
        stats['anomaly_count'] = sensor.anomalies.count()
        sensor_stats.append(stats)

    context = {
        'building': building,
        'sensor_stats': sensor_stats,
        'anomalies': Anomaly.objects.filter(
            sensor__building=building
        ).order_by('-detected_at'),
    }
    return render(request, 'smartguard_template/building_detail.html', context)


def generate_random_data(request):
    now = timezone.now()
    sensors = list(Sensor.objects.all())

    if not sensors:
        return redirect('smartguard:dashboard')

    # ==========================================
    # Generate random readings (5-20 per click)
    # ==========================================
    num_readings = random.randint(5, 20)
    new_readings = []

    profiles = {
        'Main Panel':              {'v': 220, 'c': 15, 'pf': 0.92},
        'HVAC System':             {'v': 220, 'c': 10, 'pf': 0.85},
        'Kitchen Circuit':         {'v': 220, 'c': 8,  'pf': 0.90},
        'Main Distribution Board': {'v': 220, 'c': 25, 'pf': 0.88},
        'Computer Lab':            {'v': 220, 'c': 12, 'pf': 0.95},
        'Gymnasium Lighting':      {'v': 220, 'c': 6,  'pf': 0.93},
        'Cafeteria Appliances':    {'v': 220, 'c': 14, 'pf': 0.87},
        'Espresso Machine Circuit': {'v': 220, 'c': 9, 'pf': 0.80},
        'Lighting and HVAC':       {'v': 220, 'c': 7,  'pf': 0.91},
        'Refrigeration Unit':      {'v': 220, 'c': 5,  'pf': 0.82},
        'Server Room UPS':         {'v': 220, 'c': 18, 'pf': 0.96},
        'Office Floor Lighting':   {'v': 220, 'c': 4,  'pf': 0.94},
    }

    for _ in range(num_readings):
        sensor = random.choice(sensors)
        p = profiles.get(sensor.appliance_name, {'v': 220, 'c': 10, 'pf': 0.90})

        ts = now - timedelta(
            minutes=random.randint(0, 60),
            seconds=random.randint(0, 59)
        )
        hour = ts.hour

        if 8 <= hour <= 12:
            load = random.uniform(0.85, 1.30)
        elif 12 < hour <= 18:
            load = random.uniform(0.60, 1.00)
        elif 18 < hour <= 22:
            load = random.uniform(0.40, 0.80)
        else:
            load = random.uniform(0.05, 0.30)

        is_abnormal = random.random() < 0.20
        if is_abnormal:
            load *= random.uniform(1.5, 3.0)

        voltage = p['v'] + random.uniform(-12, 12)
        if is_abnormal and random.random() < 0.5:
            voltage += random.choice([-30, -25, 25, 35])

        current = max(0.1, p['c'] * load + random.uniform(-0.5, 0.5))
        pf = max(0.40, min(1.0, p['pf'] + random.uniform(-0.08, 0.05)))
        if is_abnormal:
            pf = max(0.40, pf - random.uniform(0.1, 0.3))

        power = voltage * current * pf

        reading = EnergyReading(
            sensor=sensor,
            timestamp=ts,
            voltage=round(voltage, 2),
            current=round(current, 2),
            power_watts=round(power, 2),
            power_factor=round(pf, 3),
        )
        new_readings.append(reading)

    EnergyReading.objects.bulk_create(new_readings)

    # ==========================================
    # Detect anomalies from new readings
    # ==========================================
    anomaly_templates = [
        ('SPIKE', 'Sudden power spike of {val}W on {app}'),
        ('OVERLOAD', 'Overload for {mins} minutes on {app}'),
        ('ABNORMAL', 'Pattern deviates {pct}% from baseline on {app}'),
        ('LOW_PF', 'Power factor dropped to {pf_val} on {app}'),
        ('VOLTAGE_SAG', 'Voltage sagged to {v_val}V on {app}'),
        ('VOLTAGE_SWELL', 'Voltage surged to {v_val}V on {app}'),
    ]

    new_anomalies = []
    for reading in new_readings:
        detected = []
        if reading.power_watts > 3000:
            detected.append('SPIKE')
        if reading.power_factor < 0.70:
            detected.append('LOW_PF')
        if reading.voltage < 195:
            detected.append('VOLTAGE_SAG')
        if reading.voltage > 245:
            detected.append('VOLTAGE_SWELL')
        if reading.current > 20:
            detected.append('OVERLOAD')

        for a_type in detected:
            if a_type == 'SPIKE':
                severity = 'CRITICAL' if reading.power_watts > 5000 else 'HIGH'
            elif a_type == 'LOW_PF':
                severity = 'HIGH' if reading.power_factor < 0.55 else 'MEDIUM'
            elif a_type in ('VOLTAGE_SAG', 'VOLTAGE_SWELL'):
                severity = 'HIGH'
            elif a_type == 'OVERLOAD':
                severity = 'CRITICAL' if reading.current > 30 else 'HIGH'
            else:
                severity = 'MEDIUM'

            template = next(
                t[1] for t in anomaly_templates if t[0] == a_type
            )
            desc = template.format(
                val=round(reading.power_watts),
                app=reading.sensor.appliance_name,
                mins=random.randint(10, 90),
                pct=random.randint(25, 95),
                pf_val=round(reading.power_factor, 2),
                v_val=round(reading.voltage, 1),
            )

            anomaly = Anomaly.objects.create(
                sensor=reading.sensor,
                reading=reading,
                anomaly_type=a_type,
                severity=severity,
                description=desc,
                detected_at=reading.timestamp,
                resolved=False,
            )
            new_anomalies.append(anomaly)

    for anomaly in new_anomalies:
        Alert.objects.create(
            building=anomaly.sensor.building,
            sensor=anomaly.sensor,
            anomaly=anomaly,
            alert_type='ANOMALY',
            message=f"{anomaly.get_anomaly_type_display()} [{anomaly.severity}]: {anomaly.description}",
            sent_at=anomaly.detected_at,
            acknowledged=False,
        )

    return redirect('smartguard:dashboard')