from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow
from django.views.decorators.cache import cache_page


def paginator_func(request, objects):
    paginator = Paginator(
        objects, settings.PAGINATOR_DEFAULT_SIZE
    )
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return page_obj


@cache_page(20, key_prefix='index_page')
def index(request):
    template = 'posts/index.html'
    posts = Post.objects.all()
    page_obj = paginator_func(request, posts)
    context = {
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    template_groups = 'posts/group_list.html'
    page_obj = paginator_func(request, posts)
    context = {
        'posts': posts,
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template_groups, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    post_count = posts.count()
    page_obj = paginator_func(request, posts)
    context = {
        'author': author,
        'page_obj': page_obj,
        'post_count': post_count,
        'posts': posts,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()
    author = post.author
    posts_count = post.author.posts.count()
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'posts_count': posts_count,
        'comments': comments,
        'author': author,
        'form': form
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, template, {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=request.user.username)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post.id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if not form.is_valid():
        return render(
            request,
            template,
            {'form': form, 'post': post}
        )
    form.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = paginator_func(request, posts)
    context = {'page_obj': page_obj}
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    template = 'posts/follow.html'
    user = request.user
    author = get_object_or_404(User, username=username)
    if user != author:
        Follow.objects.get_or_create(
            user=user,
            author=author,
        )
    return redirect(template, author)


@login_required
def profile_unfollow(request, username):
    template = 'posts/profile.html'
    get_object_or_404(
        Follow, user=request.user, author__username=username).delete()
    return redirect(template, username=username)
