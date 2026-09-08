from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    content = models.TextField(verbose_name=_("Content"))
    image = models.ImageField(upload_to='forum/posts/', blank=True, null=True, verbose_name=_("Image"))
    video_url = models.URLField(
        blank=True, null=True,
        verbose_name=_("Video URL"),
        help_text=_("YouTube link (e.g.: https://www.youtube.com/watch?v=...)")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False, verbose_name=_("Pinned"))

    def __str__(self):
        return self.title

    def get_youtube_id(self):
        if self.video_url and 'youtube.com' in self.video_url:
            # Extrait l'ID de la video apres 'v='
            import urllib.parse as urlparse
            url_data = urlparse.urlparse(self.video_url)
            query = urlparse.parse_qs(url_data.query)
            return query.get("v", [None])[0]
        return None

    class Meta:
        ordering = ['-is_pinned', '-created_at']


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(verbose_name=_("Content"))
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return _("Comment by %(user)s on %(post)s") % {"user": self.user.username, "post": self.post.title}