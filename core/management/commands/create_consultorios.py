from django.core.management.base import BaseCommand
from core.models import Consultorio


class Command(BaseCommand):
    help = "Crea los 8 consultorios base (1-8) si no existen."

    def handle(self, *args, **options):
        created_count = 0
        for numero in range(1, 9):
            consultorio, created = Consultorio.objects.get_or_create(
                numero=numero,
                defaults={"nombre": f"Consultorio {numero}"},
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Creado {consultorio.nombre} (#{consultorio.numero})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Ya existe Consultorio {consultorio.numero} (sin cambios)"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"Listo. Consultorios creados: {created_count}/8")
        )
