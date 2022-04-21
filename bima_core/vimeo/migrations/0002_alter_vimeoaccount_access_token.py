# Generated by Django 3.2 on 2022-02-22 18:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vimeo', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vimeoaccount',
            name='access_token',
            field=models.CharField(help_text='Token must have at least scopes "public private create edit upload".', max_length=100, unique=True, verbose_name='Access token'),
        ),
    ]