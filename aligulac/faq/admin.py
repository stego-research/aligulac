from django.contrib import admin

from faq.models import Post


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'index')


admin.site.register(Post, PostAdmin)
