# Data migration: populate Constituency.region based on district name

from django.db import migrations


DISTRICT_REGION_MAP = {
    'Kasaragod': 'north',
    'Kannur': 'north',
    'Wayanad': 'north',
    'Kozhikode': 'north',
    'Malappuram': 'central_north',
    'Palakkad': 'central_north',
    'Thrissur': 'central_north',
    'Ernakulam': 'south_central',
    'Idukki': 'south_central',
    'Kottayam': 'south_central',
    'Alappuzha': 'south_central',
    'Pathanamthitta': 'south',
    'Kollam': 'south',
    'Thiruvananthapuram': 'south',
}


def populate_regions(apps, schema_editor):
    Constituency = apps.get_model('core', 'Constituency')
    for constituency in Constituency.objects.select_related('district').all():
        district_name = constituency.district.name
        region = DISTRICT_REGION_MAP.get(district_name, '')
        if region and constituency.region != region:
            constituency.region = region
            constituency.save(update_fields=['region'])


def reverse_regions(apps, schema_editor):
    Constituency = apps.get_model('core', 'Constituency')
    Constituency.objects.all().update(region='')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_add_region_to_constituency'),
    ]

    operations = [
        migrations.RunPython(populate_regions, reverse_regions),
    ]
