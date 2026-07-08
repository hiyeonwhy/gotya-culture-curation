from django.db import migrations, models


def populate_login_ids(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    used_ids = set()

    for user in User.objects.order_by("pk"):
        if user.email:
            base = user.email.split("@", 1)[0].strip().lower()
        else:
            base = f"user{user.pk}"

        base = (base or f"user{user.pk}")[:50]
        login_id = base
        suffix = 1
        while login_id in used_ids:
            suffix_text = f"-{suffix}"
            login_id = f"{base[:50 - len(suffix_text)]}{suffix_text}"
            suffix += 1

        user.login_id = login_id
        user.save(update_fields=["login_id"])
        used_ids.add(login_id)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="login_id",
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name="아이디"),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.RunPython(populate_login_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="login_id",
            field=models.CharField(max_length=50, unique=True, verbose_name="아이디"),
        ),
    ]
