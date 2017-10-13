# -*- coding: utf-8 -*-

from django.contrib import admin

from . import models


class YoutubeChanelInlineAdmin(admin.TabularInline):
    model = models.YoutubeChannel
    extra = 0


@admin.register(models.YoutubeAccount)
class YoutubeAccountAdmin(admin.ModelAdmin):
    list_display = ('username',)
    search_fields = ('username',)
    inlines = (YoutubeChanelInlineAdmin,)
