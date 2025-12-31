from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from .models import Post, Comment
from .forms import PostForm, CommentForm
from django.contrib import messages

@login_required
def community_feed(request):
    posts = Post.objects.all().prefetch_related('comments__user')
    comment_form = CommentForm()
    post_form = PostForm() # Pour la modale
    
    if request.method == 'POST' and 'submit_comment' in request.POST:
        post_id = request.POST.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()
            messages.success(request, _("Commentaire ajouté !"))
            return redirect('community_feed')

    return render(request, 'community/feed.html', {
        'posts': posts,
        'comment_form': comment_form,
        'post_form': post_form, # Passé ici pour la modale
    })


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # On récupère uniquement les commentaires "parents" (ceux qui n'ont pas de parent_id)
    comments = post.comments.filter(parent=None)
    comment_form = CommentForm()

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user
            
            # On vérifie si c'est une réponse
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent_obj = Comment.objects.get(id=parent_id)
                comment.parent = parent_obj
                
            comment.save()
            messages.success(request, _("Message envoyé !"))
            return redirect('post_detail', pk=post.pk)

    return render(request, 'community/post_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form
    })

@login_required
def create_post(request):
    if request.user.role == 'dietitian' and request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, _("Votre article a été publié avec succès !"))
    return redirect('community_feed')


@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # Sécurité : Seule la diététicienne peut supprimer un post (ou l'auteur)
    if request.user.role == 'dietitian' or request.user == post.author:
        post.delete()
        messages.success(request, _("Publication supprimée."))
    return redirect('community_feed')

@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    # Sécurité : L'auteur du commentaire ou la diététicienne
    if request.user == comment.user or request.user.role == 'dietitian':
        post_pk = comment.post.pk
        comment.delete()
        messages.success(request, _("Commentaire supprimé."))
        return redirect('post_detail', pk=post_pk)
    return redirect('community_feed')


@login_required
def toggle_pin_post(request, pk):
    if request.user.role != 'dietitian':
        return redirect('community_feed')
    
    post = get_object_or_404(Post, pk=pk)
    post.is_pinned = not post.is_pinned # Inverse l'état (True -> False ou inversement)
    post.save()
    
    status = "épinglé" if post.is_pinned else "désépinglé"
    messages.success(request, f"Le post a été {status}.")
    return redirect('community_feed')