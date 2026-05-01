#!/bin/bash

# Kerala Election 2026 - Quick Setup Script
# This script sets up the initial database structure and imports historical data

set -e

echo "🗳️  Kerala Election 2026 - Quick Setup"
echo "======================================"
echo ""

# Check if we're in the backend directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Run this script from the backend/ directory"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "   Please activate: source venv/bin/activate"
    exit 1
fi

echo "Step 1: Running migrations..."
python manage.py migrate

echo ""
echo "Step 2: Populating districts..."
python manage.py shell << EOF
from core.models import District

districts = [
    ('Kasaragod', 1),
    ('Kannur', 2),
    ('Wayanad', 3),
    ('Kozhikode', 4),
    ('Malappuram', 5),
    ('Palakkad', 6),
    ('Thrissur', 7),
    ('Ernakulam', 8),
    ('Idukki', 9),
    ('Kottayam', 10),
    ('Alappuzha', 11),
    ('Pathanamthitta', 12),
    ('Kollam', 13),
    ('Thiruvananthapuram', 14),
]

for name, order in districts:
    district, created = District.objects.get_or_create(name=name, defaults={'order': order})
    print(f"{'✓ Created' if created else '  Updated'}: {name}")

print(f"\n✅ Total districts: {District.objects.count()}")
EOF

echo ""
echo "Step 3: Populating parties..."
python manage.py shell << EOF
from core.models import Party

parties = [
    # UDF
    ('INC', 'Indian National Congress', 'UDF', '#19AAED'),
    ('IUML', 'Indian Union Muslim League', 'UDF', '#00A650'),
    ('KC(M)', 'Kerala Congress (M)', 'UDF', '#FFA500'),
    ('KC(J)', 'Kerala Congress (Joseph)', 'UDF', '#FFD700'),
    ('RSP', 'Revolutionary Socialist Party', 'UDF', '#FF69B4'),
    
    # LDF
    ('CPI(M)', 'Communist Party of India (Marxist)', 'LDF', '#ED1E26'),
    ('CPI', 'Communist Party of India', 'LDF', '#FF0000'),
    ('JD(S)', 'Janata Dal (Secular)', 'LDF', '#138808'),
    ('NCP', 'Nationalist Congress Party', 'LDF', '#00B2B2'),
    
    # NDA
    ('BJP', 'Bharatiya Janata Party', 'NDA', '#FF9933'),
    ('BDJS', 'Bharath Dharma Jana Sena', 'NDA', '#FF6B6B'),
    
    # Others
    ('SDPI', 'Social Democratic Party of India', 'OTH', '#006400'),
    ('AAP', 'Aam Aadmi Party', 'OTH', '#0066CC'),
    ('IND', 'Independent', 'OTH', '#808080'),
]

for code, name, alliance, color in parties:
    party, created = Party.objects.get_or_create(
        code=code,
        defaults={'full_name': name, 'alliance': alliance, 'color_code': color}
    )
    print(f"{'✓ Created' if created else '  Updated'}: {code} ({alliance})")

print(f"\n✅ Total parties: {Party.objects.count()}")
EOF

echo ""
echo "⚠️  IMPORTANT: You need to import constituencies before proceeding!"
echo "   The constituency master list (all 140) is not included in this script."
echo "   See DEV_GUIDE.md for instructions on importing constituencies."
echo ""

# Check if CSV files exist
if [ -f "../data/election_candidates.csv" ]; then
    echo "Step 4: Importing 2021 LA results..."
    python manage.py import_2021_results ../data/election_candidates.csv
else
    echo "⚠️  Skipping 2021 results: ../data/election_candidates.csv not found"
fi

if [ -f "../data/2019_Parliment.csv" ]; then
    echo ""
    echo "Step 5: Importing 2019 Parliament results..."
    python manage.py import_parliament_results 2019 ../data/2019_Parliment.csv
else
    echo "⚠️  Skipping 2019 results: ../data/2019_Parliment.csv not found"
fi

if [ -f "../data/2024_Parliment.csv" ]; then
    echo ""
    echo "Step 6: Importing 2024 Parliament results..."
    python manage.py import_parliament_results 2024 ../data/2024_Parliment.csv
else
    echo "⚠️  Skipping 2024 results: ../data/2024_Parliment.csv not found"
fi

echo ""
echo "======================================"
echo "✅ Setup complete!"
echo ""
echo "📊 Database Status:"
python manage.py shell << EOF
from core.models import *

print(f"  Districts: {District.objects.count()}")
print(f"  Constituencies: {Constituency.objects.count()}")
print(f"  Parties: {Party.objects.count()}")
print(f"  2021 LA Results: {HistoricalResult2021.objects.count()}")
print(f"  2019 LS Results: {ParliamentResult.objects.filter(year=2019).count()}")
print(f"  2024 LS Results: {ParliamentResult.objects.filter(year=2024).count()}")
print(f"  2026 Candidates: {Candidate.objects.count()}")
EOF

echo ""
echo "🚀 Next Steps:"
echo "   1. Import constituencies (see DEV_GUIDE.md)"
echo "   2. Create superuser: python manage.py createsuperuser"
echo "   3. Start server: python manage.py runserver"
echo "   4. Access admin: http://localhost:8000/admin/"
echo ""
