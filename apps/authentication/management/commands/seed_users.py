from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction, models

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea usuarios de prueba con diferentes roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la creación de usuarios incluso si ya existen',
        )

    def handle(self, *args, **options):
        users_data = [
            {
                'email': 'admin@example.com',
                'username': 'admin_user',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'collaborator@example.com',
                'username': 'collaborator_user',
                'first_name': 'Collaborator',
                'last_name': 'User',
                'role': User.Role.COLLABORATOR,
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'email': 'viewer@example.com',
                'username': 'viewer_user',
                'first_name': 'Viewer',
                'last_name': 'User',
                'role': User.Role.VIEWER,
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        password = '12345678'
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for user_data in users_data:
                email = user_data['email']
                username = user_data['username']
                
                # Verificar si el usuario ya existe por email o username
                existing_user = User.objects.filter(
                    models.Q(email=email) | models.Q(username=username)
                ).first()
                
                if existing_user:
                    if options['force']:
                        # Actualizar usuario existente
                        for key, value in user_data.items():
                            setattr(existing_user, key, value)
                        existing_user.set_password(password)
                        existing_user.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'Usuario actualizado: {email}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'Usuario ya existe: {email} (usa --force para actualizar)')
                        )
                else:
                    # Crear nuevo usuario
                    user = User.objects.create_user(
                        password=password,
                        **user_data
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Usuario creado: {email}')
                    )

        # Resumen
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Usuarios creados: {created_count}'))
        self.stdout.write(self.style.WARNING(f'Usuarios actualizados: {updated_count}'))
        self.stdout.write('\nCredenciales de prueba:')
        self.stdout.write('- admin@example.com / 12345678 (Administrador)')
        self.stdout.write('- collaborator@example.com / 12345678 (Colaborador)')
        self.stdout.write('- viewer@example.com / 12345678 (Visor)')
        self.stdout.write('='*50)