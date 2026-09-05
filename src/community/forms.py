from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'video_url']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Partagez un conseil ou une recette...'}),
            'title': forms.TextInput(attrs={'placeholder': 'Titre de votre publication'}),
            'video_url': forms.URLInput(attrs={'placeholder': 'Lien YouTube (optionnel)'}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={'placeholder': 'Ajouter un commentaire...', 'class': 'rounded-pill'}),
        }