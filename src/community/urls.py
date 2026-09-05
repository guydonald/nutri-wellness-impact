from django.urls import path
from . import views

urlpatterns = [
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('feed/', views.community_feed, name='community_feed'),
    path('post/new/', views.create_post, name='create_post'),
    path('post/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
]