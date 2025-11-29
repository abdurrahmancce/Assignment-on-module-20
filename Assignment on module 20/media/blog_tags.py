# blog/templatetags/blog_tags.py
from django import template
from blog.models import Post
from taggit.models import Tag

register = template.Library()

@register.simple_tag
def recent_posts(limit=5):
    return Post.objects.filter(status='published').order_by('-created_at')[:limit]

@register.simple_tag(takes_context=True)
def tags(context):
    return Tag.objects.all()
