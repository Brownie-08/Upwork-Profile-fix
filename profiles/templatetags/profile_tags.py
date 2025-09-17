from django import template

register = template.Library()


@register.filter
def get_field(obj, field_name):
    """
    Dynamically get the value of a field from an object.
    Returns None if the field does not exist.
    """
    try:
        return getattr(obj, field_name)
    except AttributeError:
        return None
