from django.contrib import admin
from django.utils.text import Truncator

from .models import Comment, Post


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("user", "content", "created_at")
    readonly_fields = ("user", "created_at")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_pinned", "nb_commentaires", "created_at")
    list_filter = ("is_pinned", "created_at")
    search_fields = ("title", "content", "author__email")
    list_editable = ("is_pinned",)
    date_hierarchy = "created_at"
    inlines = [CommentInline]

    @admin.display(description="Commentaires")
    def nb_commentaires(self, obj):
        return obj.comments.count()


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("apercu", "user", "post", "created_at")
    search_fields = ("content", "user__email", "post__title")
    date_hierarchy = "created_at"

    @admin.display(description="Commentaire")
    def apercu(self, obj):
        return Truncator(obj.content).chars(80)
