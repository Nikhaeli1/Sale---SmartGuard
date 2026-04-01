import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from smartguard_app.models import (
    BuildingType, Building, Sensor,
    EnergyReading, Anomaly, Alert
)


class Command(BaseCommand):
    help = 'Populate SmartGuard with simulated data'

    def handle(self, *args, **options):

        # Clear data
        self.stdout.write("Clearing old data...")
        Alert.objects.all().delete()
        Anomaly.objects.all().delete()
        EnergyReading.objects.all().delete()
        Sensor.objects.all().delete()
        Building.objects.all().delete()
        BuildingType.objects.all().delete()

        now = timezone.now()

        # ========================================
        # 1. BUILDING TYPES
        # ========================================
        self.stdout.write("\n[1/6] Building Types...")

        bt_res = BuildingType.objects.create(name='Residential')
        bt_sch = BuildingType.objects.create(name='School')
        bt_com = BuildingType.objects.create(name='Commercial')
        bt_gov = BuildingType.objects.create(name='Government')

        self.stdout.write("  Created 4 types")

        # ========================================
        # 2. BUILDINGS (at least 3)
        # ========================================
        self.stdout.write("\n[2/6] Buildings...")

        b1 = Building.objects.create(
            name='Maple Street Residence',
            address='42 Maple St, Springfield',
            building_type=bt_res
        )
        b2 = Building.objects.create(
            name='Lincoln Elementary School',
            address='100 Education Blvd, Springfield',
            building_type=bt_sch
        )
        b3 = Building.objects.create(
            name='Downtown Brew Coffee Shop',
            address='7 Main St, Springfield',
            building_type=bt_com
        )
        b4 = Building.objects.create(
            name='City Hall Annex',
            address='1 Government Plaza, Springfield',
            building_type=bt_gov
        )

        for b in [b1, b2, b3, b4]:
            self.stdout.write(f"  {b.name}")

        # ========================================
        # 3. SENSORS (at least 2 per building)
        # ========================================
        self.stdout.write("\n[3/6] Sensors...")

        sensors_config = {
            b1: [
                ('SEN-RES-001', 'Main Panel'),
                ('SEN-RES-002', 'HVAC System'),
                ('SEN-RES-003', 'Kitchen Circuit'),
            ],
            b2: [
                ('SEN-SCH-001', 'Main Distribution Board'),
                ('SEN-SCH-002', 'Computer Lab'),
                ('SEN-SCH-003', 'Gymnasium Lighting'),
                ('SEN-SCH-004', 'Cafeteria Appliances'),
            ],
            b3: [
                ('SEN-COM-001', 'Espresso Machine Circuit'),
                ('SEN-COM-002', 'Lighting and HVAC'),
                ('SEN-COM-003', 'Refrigeration Unit'),
            ],
            b4: [
                ('SEN-GOV-001', 'Server Room UPS'),
                ('SEN-GOV-002', 'Office Floor Lighting'),
            ],
        }

        all_sensors = []
        for building, sensor_list in sensors_config.items():
            for label, appliance in sensor_list:
                s = Sensor.objects.create(
                    building=building,
                    sensor_label=label,
                    appliance_name=appliance
                )
                all_sensors.append(s)
                self.stdout.write(f"  {label} -> {appliance} @ {building.name}")

        # ========================================
        # 4. ENERGY READINGS (at least 100/sensor)
        # ========================================
        self.stdout.write("\n[4/6] Energy Readings...")

        READINGS_PER_SENSOR = 150

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

        all_readings = []
        for sensor in all_sensors:
            p = profiles.get(sensor.appliance_name, {'v': 220, 'c': 10, 'pf': 0.90})

            for i in range(READINGS_PER_SENSOR):
                ts = now - timedelta(
                    days=random.uniform(0, 30),
                    hours=random.uniform(0, 23),
                    minutes=random.uniform(0, 59)
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

                voltage = p['v'] + random.uniform(-12, 12)
                current = max(0.1, p['c'] * load + random.uniform(-0.5, 0.5))
                pf = max(0.50, min(1.0, p['pf'] + random.uniform(-0.05, 0.05)))
                power = voltage * current * pf

                all_readings.append(EnergyReading(
                    sensor=sensor,
                    timestamp=ts,
                    voltage=round(voltage, 2),
                    current=round(current, 2),
                    power_watts=round(power, 2),
                    power_factor=round(pf, 3),
                ))

        EnergyReading.objects.bulk_create(all_readings, batch_size=500)
        self.stdout.write(f"  Created {len(all_readings)} readings")

        # ========================================
        # 5. ANOMALIES (at least 10)
        # ========================================
        self.stdout.write("\n[5/6] Anomalies...")

        templates = [
            ('SPIKE', 'HIGH', 'Sudden power spike of {val}W on {app}'),
            ('SPIKE', 'CRITICAL', 'Dangerous spike of {val}W on {app}'),
            ('SPIKE', 'MEDIUM', 'Moderate spike of {val}W on {app}'),
            ('OVERLOAD', 'HIGH', 'Overload for {mins} minutes on {app}'),
            ('OVERLOAD', 'MEDIUM', 'Moderate overload on {app} for {mins} min'),
            ('OVERLOAD', 'CRITICAL', 'Severe overload on {app}'),
            ('ABNORMAL', 'MEDIUM', 'Pattern deviates {pct}% from baseline on {app}'),
            ('ABNORMAL', 'LOW', 'Minor irregularity on {app}'),
            ('LOW_PF', 'MEDIUM', 'Power factor dropped to {pf_val} on {app}'),
            ('LOW_PF', 'HIGH', 'Critical PF degradation to {pf_val} on {app}'),
            ('VOLTAGE_SAG', 'HIGH', 'Voltage sagged to {v_val}V on {app}'),
            ('VOLTAGE_SAG', 'MEDIUM', 'Moderate voltage sag to {v_val}V'),
            ('VOLTAGE_SWELL', 'HIGH', 'Voltage surged to {v_val}V on {app}'),
            ('VOLTAGE_SWELL', 'MEDIUM', 'Voltage swell to {v_val}V on {app}'),
            ('ABNORMAL', 'HIGH', 'Severe abnormal pattern on {app}'),
        ]

        anomalies = []
        for i in range(15):
            sensor = random.choice(all_sensors)
            reading = EnergyReading.objects.filter(sensor=sensor).order_by('?').first()
            a_type, severity, template = templates[i]

            desc = template.format(
                val=random.randint(200, 1200),
                app=sensor.appliance_name,
                mins=random.randint(10, 90),
                pct=random.randint(25, 95),
                pf_val=round(random.uniform(0.50, 0.70), 2),
                v_val=round(random.uniform(175, 265), 1),
            )

            a = Anomaly.objects.create(
                sensor=sensor,
                reading=reading,
                anomaly_type=a_type,
                severity=severity,
                description=desc,
                detected_at=reading.timestamp if reading else now,
                resolved=random.choice([True, True, False]),
            )
            anomalies.append(a)
            self.stdout.write(f"  [{severity}] {a_type} -> {sensor.appliance_name}")

        # ========================================
        # 6. ALERTS
        # ========================================
        self.stdout.write("\n[6/6] Alerts...")

        for anomaly in anomalies:
            Alert.objects.create(
                building=anomaly.sensor.building,
                sensor=anomaly.sensor,
                anomaly=anomaly,
                alert_type='ANOMALY',
                message=f"{anomaly.get_anomaly_type_display()} [{anomaly.severity}]: {anomaly.description}",
                acknowledged=anomaly.resolved,
            )

        # Summary
        self.stdout.write("\n" + "=" * 40)
        self.stdout.write("  SUMMARY")
        self.stdout.write("=" * 40)
        self.stdout.write(f"  Building Types:  {BuildingType.objects.count()}")
        self.stdout.write(f"  Buildings:       {Building.objects.count()}")
        self.stdout.write(f"  Sensors:         {Sensor.objects.count()}")
        self.stdout.write(f"  Readings:        {EnergyReading.objects.count()}")
        self.stdout.write(f"  Anomalies:       {Anomaly.objects.count()}")
        self.stdout.write(f"  Alerts:          {Alert.objects.count()}")
        self.stdout.write(self.style.SUCCESS("\nDone!"))