from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'video_url']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': _('Share a tip or a recipe...')}),
            'title': forms.TextInput(attrs={'placeholder': _('Title of your post')}),
            'video_url': forms.URLInput(attrs={'placeholder': _('YouTube link (optional)')}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={'placeholder': _('Add a comment...'), 'class': 'rounded-pill'}),
        }