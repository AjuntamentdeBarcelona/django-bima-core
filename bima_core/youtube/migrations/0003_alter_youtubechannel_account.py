# Generated by Django 3.2 on 2022-02-22 18:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('youtube', '0002_auto_20171013_1531'),
    ]

    operations = [
        migrations.AlterField(
            model_name='youtubechannel',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='youtube.youtubeaccount', verbose_name='Youtube account'),
        ),
    ]