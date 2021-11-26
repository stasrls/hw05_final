from http import HTTPStatus
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache

from ..models import Post, Group


User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.user)
        cache.clear()

    def test_homepage(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_detail_url(self):
        pk = StaticURLTests.post.pk
        response = self.guest_client.get(reverse('posts:post_detail',
                                                 kwargs={'post_id': pk}))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_url(self):
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url(self):
        pk = StaticURLTests.post.pk
        response = self.authorized_client.get(reverse('posts:post_edit',
                                              kwargs={'post_id': pk}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_create_url(self):
        response = self.guest_client.get(reverse('posts:post_create'))
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_follow_url(self):
        response = self.guest_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        # Гость
        self.guest_client = Client()
        # Автор
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        # Пользователь
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)
        cache.clear()

    def test_status_urls(self):
        open_urls_names = [
            reverse('posts:index'),
            reverse('posts:group_list', args={self.group.slug}),
            reverse('posts:profile', args={self.author.username}),
            reverse('posts:post_detail', args={self.post.pk}),
        ]
        for reverse_name in open_urls_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

        # Статус для пользователя
        response = self.authorized_user.get(
            reverse('posts:post_create')
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Статус для автора
        response = self.authorized_author.get(
            reverse('posts:post_edit', args={self.post.pk})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.authorized_author.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        response = self.guest_client.get('unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_redirect(self):
        # Редирект гостя
        urls_names = [
            reverse('posts:post_create'),
            reverse('posts:follow_index'),
            reverse('posts:post_edit', args={self.post.pk}),
        ]
        for reverse_name in urls_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name, follow=True)
                self.assertRedirects(
                    response, (
                        reverse('users:login') + f'?next={reverse_name}'
                    )
                )
        # Редирект пользователя
        response = self.authorized_user.get(
            reverse('posts:post_edit', args={self.post.pk}), follow=True
        )
        self.assertRedirects(
            response, (
                reverse('posts:post_detail', args={self.post.pk})
            )
        )

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
            reverse('posts:group_list', args={self.group.slug}):
                'posts/group_list.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in url_templates_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)
