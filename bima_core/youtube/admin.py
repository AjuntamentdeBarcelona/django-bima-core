# -*- coding: utf-8 -*-

from django.contrib import admin

from . import models


@admin.register(models.YoutubeAccount)
class YoutubeAccountAdmin(admin.ModelAdmin):
    list_display = ('username',)
    search_fields = ('username',)


@admin.register(models.YoutubeChannel)
class YoutubeChanelAdmin(admin.ModelAdmin):
    list_display = ('channel_id', 'name', 'account')
    list_filter = ('account',)
    search_fields = ('channel_id', 'name')
