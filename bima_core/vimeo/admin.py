# -*- coding: utf-8 -*-

from django.contrib import admin

from . import models


@admin.register(models.VimeoAccount)
class VimeoAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'username')
    search_fields = ('name', 'username')
