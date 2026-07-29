#!/usr/bin/env python
"""Initialize database with admin user"""

from src.database.db import Database
from src.services.auth_service import AuthenticationService

# Initialize database
db = Database()
auth = AuthenticationService()

# Check existing users
users = db.fetch_all('SELECT username, role FROM users')
print(f'Existing users: {len(users)}')

if users:
    for user in users:
        print(f'  - {user["username"]} ({user["role"]})')
else:
    print('No users found. Creating admin user...')
    try:
        success, msg, user_id = auth.create_user(
            username='admin',
            email='admin@medistock.local',
            password='password123',
            full_name='System Administrator',
            role='Administrator'
        )
        if success:
            print('[OK] Admin user created successfully!')
            print('     Username: admin')
            print('     Password: password123')
        else:
            print(f'[ERROR] {msg}')
    except Exception as e:
        print(f'[ERROR] {e}')

db.close()