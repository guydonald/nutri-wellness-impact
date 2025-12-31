from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, verbose_name="Titre")
    content = models.TextField(verbose_name="Contenu")
    image = models.ImageField(upload_to='community/posts/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text="Lien YouTube (ex: https://www.youtube.com/watch?v=...)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    
    def get_youtube_id(self):
        if self.video_url and 'youtube.com' in self.video_url:
            # Extrait l'ID de la vidéo après 'v='
            import urllib.parse as urlparse
            url_data = urlparse.urlparse(self.video_url)
            query = urlparse.parse_qs(url_data.query)
            return query.get("v", [None])[0]
        return None

    class Meta:
        ordering = ['-is_pinned', '-created_at']

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commentaire de {self.user.username} sur {self.post.title}"