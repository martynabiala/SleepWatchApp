from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(blank=True, max_length=100, verbose_name="Nazwa wyswietlana")),
                ("age_group", models.CharField(blank=True, choices=[("18-25", "18-25 lat"), ("26-35", "26-35 lat"), ("36-50", "36-50 lat"), ("51+", "51+ lat")], max_length=10, verbose_name="Grupa wiekowa")),
                ("lifestyle", models.CharField(blank=True, choices=[("student", "Student"), ("office", "Pracownik biurowy"), ("shift", "Pracownik zmianowy"), ("active", "Aktywny sportowo")], max_length=20, verbose_name="Styl zycia")),
                ("sleep_goal_hours", models.PositiveSmallIntegerField(default=8, verbose_name="Cel snu (godziny)")),
                ("bio", models.TextField(blank=True, verbose_name="O mnie")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Profil uzytkownika",
                "verbose_name_plural": "Profile uzytkownikow",
            },
        ),
    ]
