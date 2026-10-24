from django import template

register = template.Library()


@register.simple_tag
def elided_pages(page_obj, on_each_side=1, on_ends=1):
    """Numeros de pages a afficher : 1 … 4 5 6 … 20"""
    return page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=on_each_side, on_ends=on_ends)
