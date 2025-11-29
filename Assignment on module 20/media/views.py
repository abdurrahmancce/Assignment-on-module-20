# blog/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count
from django.contrib import messages
from django.urls import reverse_lazy
from taggit.models import Tag

from .models import Post, Comment, Like
from .forms import PostForm, CommentForm

class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 5  # 3.3 pagination

    def get_queryset(self):
        qs = Post.objects.filter(status='published').select_related('author').prefetch_related('tags')
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['query'] = self.request.GET.get('q', '')
        return ctx

class TagListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        tag_slug = self.kwargs.get('tag_slug')
        tag = get_object_or_404(Tag, slug=tag_slug)
        return Post.objects.filter(status='published', tags__in=[tag]).distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tag'] = self.kwargs.get('tag_slug')
        return ctx

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    # Only published posts are public; author can view drafts via detail for edit convenience
    if post.status != 'published' and post.author != request.user:
        messages.warning(request, 'This post is not published.')
        return redirect('post_list')

    comments = post.comments.select_related('user')
    liked = False
    if request.user.is_authenticated:
        liked = Like.objects.filter(post=post, user=request.user).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Login required to comment.')
            return redirect('login')
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment added.')
            return redirect(post.get_absolute_url())
    else:
        form = CommentForm()

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'comments': comments,
        'form': form,
        'liked': liked,
        'like_count': post.likes.count(),
    })

class AuthorPermissionMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return obj.author == self.request.user

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, 'Post created.')
        return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin, AuthorPermissionMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Post updated.')
        return super().form_valid(form)

class PostDeleteView(LoginRequiredMixin, AuthorPermissionMixin, DeleteView):
    model = Post
    template_name = 'blog/post_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Post deleted.')
        return super().delete(request, *args, **kwargs)

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'blog/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['my_posts'] = Post.objects.filter(author=self.request.user).annotate(
            like_count=Count('likes')
        ).order_by('-created_at')
        return ctx

def like_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if not request.user.is_authenticated:
        messages.error(request, 'Login required to like posts.')
        return redirect('login')
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
        messages.info(request, 'Like removed.')
    else:
        messages.success(request, 'Post liked.')
    return redirect(post.get_absolute_url())
