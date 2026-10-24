from .models import InboxMessage


def inbox_unread(request):
    """Nombre de messages non lus, pour la pastille du menu de la nutritionniste."""
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and getattr(user, 'role', None) == 'dietitian':
        return {'inbox_unread_count': InboxMessage.objects.filter(is_read=False).count()}
    return {}
