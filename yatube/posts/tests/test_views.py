from http import HTTPStatus
import random
import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment, Follow
from yatube.settings import NUMBER_OF_POSTS


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


User = get_user_model()


class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.groups = [
            Group.objects.create(
                title='Первая группа',
                slug='first',
                description='Описание первой группы',
            ),
            Group.objects.create(
                title='Вторая группа',
                slug='second',
                description='Описание второй группы',
            ),
        ]
        cls.group_1 = cls.groups[0]
        cls.group_2 = cls.groups[1]
        cls.posts = [
            Post.objects.create(
                text='Тестовый пост',
                author=cls.author,
                group=cls.group_1,
            ),
            Post.objects.create(
                text='Тестовый пост',
                author=cls.author,
                group=cls.group_2,
            ),
        ]
        cls.post_in_group = cls.posts[0]
        cls.post = cls.posts[1]

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        cache.clear()

    def test_correct_template(self):
        cache.clear()
        url_templates_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:profile', args={self.author.username}):
                'posts/profile.html',
            reverse('posts:post_edit', args={self.post.pk}):
                'posts/create_post.html',
            reverse('posts:post_detail', args={self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:group_list', args={self.group_1.slug}):
                'posts/group_list.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in url_templates_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_list_context(self):
        cache.clear()
        urls_posts = {
            reverse('posts:index'): len(self.posts),
            reverse('posts:profile', args={self.author.username}):
                self.author.posts.count(),
            reverse('posts:group_list', args={self.group_1.slug}):
                self.group_1.posts.count(),
            reverse('posts:group_list', args={self.group_2.slug}):
                self.group_2.posts.count(),
        }
        for reverse_name, object in urls_posts.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertIn('posts', response.context)
                self.assertEqual(len(response.context['posts']), object)

    def test_post_context(self):
        cache.clear()
        urls = [
            reverse('posts:index'),
            reverse('posts:profile', args={self.author.username}),
            reverse('posts:group_list', args={self.group_1.slug}),
        ]
        for reverse_name in urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                first_object = response.context['posts'][0]
                post_text_0 = first_object.text
                post_author_0 = first_object.author.username
                post_group_0 = self.group_1.title
                self.assertEqual(post_text_0, self.post_in_group.text)
                self.assertEqual(post_author_0, self.author.username)
                self.assertEqual(post_group_0, self.group_1.title)

    def test_post_id_context(self):
        response = self.authorized_author.get(
            reverse('posts:post_detail', args={self.post.pk})
        )
        post = response.context['post']
        self.assertEqual(post.pk, self.post.pk)

    def test_group_context(self):
        response = self.authorized_author.get(
            reverse('posts:group_list', args={self.group_1.slug})
        )
        post = response.context['posts'][0]
        self.assertEqual(post.pk, self.post_in_group.pk)
        self.assertNotEqual(post.pk, self.post.pk)

    def test_form_context(self):
        urls = [
            reverse('posts:post_edit', args={self.post.pk}),
            reverse('posts:post_create'),
        ]
        for reverse_name in urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                form_fields = {
                    'text': forms.fields.CharField,
                    'group': forms.fields.ChoiceField,
                }
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get('form').fields.get(
                            value)
                        self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Author')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Test test group',
            slug='test_group',
            description='Описание тестовой группы'
        )
        cls.add_pages = random.randint(1, NUMBER_OF_POSTS - 1)
        obj_posts = (Post(text='Test text',
                          author=cls.author,
                          group=cls.group
                          ) for i in range(NUMBER_OF_POSTS + cls.add_pages))
        cls.post = Post.objects.bulk_create(obj_posts)
        cls.urls_with_paginator = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.author.username}),
        }

    def test_first_page_contains_ten_records(self):
        cache.clear()
        for reverse_name in self.urls_with_paginator:
            response = self.authorized_client.get(reverse_name)
            self.assertEqual(len(response.context['page_obj']),
                             NUMBER_OF_POSTS)

    def test_second_page_contains_three_records(self):
        for reverse_name in self.urls_with_paginator:
            response = self.client.get(reverse_name + '?page=2')
            self.assertEqual(len(response.context['page_obj']),
                             self.add_pages)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)
        cache.clear()

    def test_post_with_image_exist(self):
        self.assertTrue(Post.objects.filter(image='posts/small.gif'))

    def test_index_show_correct_image_in_context(self):
        """Context в шаблоне index"""
        cache.clear()
        response = self.author_client.get(reverse('posts:index'))
        test_object = response.context['page_obj'][0]
        post_image = test_object.image
        self.assertEqual(post_image, 'posts/small.gif')

    def test_post_detail_image_exist(self):
        """Context в шаблоне post_detail"""
        response = self.author_client.get(
            reverse('posts:post_detail', args=[self.post.id])
        )
        test_object = response.context['post']
        post_image = test_object.image
        self.assertEqual(post_image, 'posts/small.gif')

    def test_group_and_profile_image_exist(self):
        """Context в шаблонах group и profile"""
        templates_pages_name = {
            'posts:group_list': self.group.slug,
            'posts:profile': self.user.username,
        }
        for names, args in templates_pages_name.items():
            with self.subTest(names=names):
                response = self.author_client.get(reverse(names, args=[args]))
                test_object = response.context['page_obj'][0]
                post_image = test_object.image
                self.assertEqual(post_image, 'posts/small.gif')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_cache_index_page(self):
        response = self.authorized_client.get(reverse('posts:index')).content
        Post.objects.create(
            author=self.user,
            text='Тестовый текст'
        )
        self.assertEqual(
            response, self.authorized_client.get(
                reverse('posts:index')).content
        )
        cache.clear()
        self.assertNotEqual(
            response, self.authorized_client.get
            (reverse('posts:index')).content
        )


class FollowsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.other_user = User.objects.create_user(username='user')

    @classmethod
    def tearDownClass(cls):
        cache.clear()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(FollowsTests.user)
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(FollowsTests.other_user)
        cache.clear()

    def test_follow(self):
        follow_count = Follow.objects.count()
        response = self.authorized_client.post(reverse(
            'posts:profile_follow', kwargs={'username': self.other_user})
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user, author=self.other_user).exists()
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unfollow(self):
        Follow.objects.create(
            user=self.user,
            author=self.other_user
        )
        response = self.authorized_client.post(reverse(
            'posts:profile_unfollow', kwargs={'username': self.other_user})
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user, author=self.other_user).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_context_index_follow(self):
        Follow.objects.create(user=self.other_user, author=self.user)
        post = Post.objects.create(text='Тестовый текст', author=self.user)
        response = self.authorized_client_1.get(reverse('posts:follow_index'))
        self.assertContains(response, post.text)

    def test_context_index_not_follow(self):
        Follow.objects.create(user=self.other_user, author=self.user)
        post = Post.objects.create(text='Тестовый текст', author=self.user)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotContains(response, post.text)
