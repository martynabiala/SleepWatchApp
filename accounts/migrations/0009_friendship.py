from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_userprofile_active_hypothesis_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Friendship",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Oczekuje"), ("accepted", "Znajomi"), ("declined", "Odrzucone")], default="pending", max_length=12)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("receiver", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="received_friendships", to=settings.AUTH_USER_MODEL)),
                ("sender", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="sent_friendships", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Relacja znajomych",
                "verbose_name_plural": "Relacje znajomych",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="friendship",
            constraint=models.UniqueConstraint(fields=("sender", "receiver"), name="accounts_friendship_unique_pair"),
        ),
        migrations.AddConstraint(
            model_name="friendship",
            constraint=models.CheckConstraint(condition=models.Q(("sender", models.F("receiver")), _negated=True), name="accounts_friendship_no_self_relation"),
        ),
    ]
