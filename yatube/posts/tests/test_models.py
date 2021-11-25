from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, Comment, Follow

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )

    def test_models_have_correct_object_names(self):
        group = PostModelTest.group
        post = PostModelTest.post
        field_str = {
            post: post.text,
            group: group.title,
        }
        for field, expected_value in field_str.items():
            with self.subTest(field=field):
                self.assertEqual(
                    expected_value, str(field),
                )

    def test_verbose_name(self):
        post = PostModelTest.post
        field_verboses_post = {
            'text': 'Текст',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
            'group': 'Группа',
        }
        for field, expected_value in field_verboses_post.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name, expected_value)

        group = PostModelTest.group
        field_verboses = {
            'title': 'Имя выборки',
            'slug': 'Уникальный адрес выборки',
            'description': 'Описание выборки',
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    group._meta.get_field(field).verbose_name, expected_value)

    def test_help_text(self):
        post = PostModelTest.post
        field_help_texts = {
            'text': 'Введите текст',
            'group': 'Выберите группу',
        }
        for field, expected_value in field_help_texts.items():
            with self.subTest(field=field):
                self.assertEqual(
                    post._meta.get_field(field).help_text, expected_value)


class CommentModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий'
        )

    def test_models_correct_verbose_name(self):
        comment = CommentModelTest.comment
        dict_verbose = {
            'post': comment._meta.get_field('post').verbose_name,
            'author': comment._meta.get_field('author').verbose_name,
            'text': comment._meta.get_field('text').verbose_name,
            'created': comment._meta.get_field('created').verbose_name,
        }
        for name, value in dict_verbose.items():
            with self.subTest(name=name):
                response = comment._meta.get_field(name)
                self.assertEqual(response.verbose_name, value)


class FollowModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.other_user = User.objects.create_user(username='user')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )
        cls.follow = Follow.objects.create(
            user=cls.other_user,
            author=cls.other_user
        )

    def test_models_correct_verbose_name(self):
        follow = FollowModelTest.follow
        dict_verbose = {
            'user': follow._meta.get_field('user').verbose_name,
            'author': follow._meta.get_field('author').verbose_name,
        }
        for name, value in dict_verbose.items():
            with self.subTest(name=name):
                response = follow._meta.get_field(name)
                self.assertEqual(response.verbose_name, value)
