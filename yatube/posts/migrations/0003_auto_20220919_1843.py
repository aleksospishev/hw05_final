# Generated by Django 2.2.19 on 2022-09-19 18:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_auto_20220917_1931'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='descriptions',
            new_name='description',
        ),
    ]
