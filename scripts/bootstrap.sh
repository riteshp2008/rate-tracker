#!/bin/bash
# Bootstrap script to set up initial admin user and generate API token

set -e

echo "Rate-Tracker Bootstrap Setup"
echo "============================"

# Wait for database to be ready
echo "Waiting for database..."
sleep 5

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser (skip if already exists)
echo "Creating superuser..."
python manage.py shell <<EOF
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

# Create superuser
if not User.objects.filter(username='admin').exists():
    admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print(f"✅ Created superuser: admin")
    token = Token.objects.create(user=admin_user)
    print(f"✅ API Token: {token.key}")
else:
    admin_user = User.objects.get(username='admin')
    token, created = Token.objects.get_or_create(user=admin_user)
    print(f"✅ Admin user already exists")
    if created:
        print(f"✅ API Token: {token.key}")

# Create data_ingester user for webhook
if not User.objects.filter(username='data_ingester').exists():
    ingester_user = User.objects.create_user(username='data_ingester', password=User.objects.make_random_password())
    ingester_token = Token.objects.create(user=ingester_user)
    print(f"✅ Created data_ingester user")
    print(f"✅ Data Ingester Token: {ingester_token.key}")
EOF

echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "Next steps:"
echo "1. Admin panel: http://localhost:8000/admin/ (username: admin, password: admin)"
echo "2. API docs: http://localhost:8000/api/rates/latest/"
echo "3. Seed database: make seed-db"
