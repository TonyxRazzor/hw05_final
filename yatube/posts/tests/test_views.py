import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
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
        cls.user = User.objects.create_user(username='uKurva')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Текст поста',
            author=cls.user,
            group=cls.group,
            image=uploaded
        )
        cls.templates_pages_names = {
            reverse("posts:index"): "posts/index.html",
            reverse(
                "posts:group_list", kwargs={"slug": cls.group.slug}
            ): "posts/group_list.html",
            reverse(
                "posts:profile", kwargs={"username": cls.post.author}
            ): "posts/profile.html",
            reverse(
                "posts:post_detail", kwargs={"post_id": cls.post.id}
            ): "posts/post_detail.html",
            reverse(
                "posts:post_edit", kwargs={"post_id": cls.post.id}
            ): "posts/create_post.html",
            reverse("posts:post_create"): "posts/create_post.html",
        }
        cls.comment_post = Comment.objects.create(
            author=cls.user,
            text='А мне только битвы запомнились»',
            post=cls.post
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTest.user)
        cache.clear()

    def post_exist(self, page_context):
        """Метод для проверки существования поста на страницах."""
        if 'page_obj' in page_context:
            post = page_context['page_obj'][0]
        else:
            post = page_context['post']
        task_author = post.author
        task_text = post.text
        task_image = post.image
        task_group = post.group
        self.assertEqual(
            task_image,
            'posts/small.gif'
        )
        self.assertEqual(
            task_author,
            PostPagesTest.post.author
        )
        self.assertEqual(
            task_text,
            PostPagesTest.post.text
        )
        self.assertEqual(
            task_group,
            PostPagesTest.post.group
        )
        self.assertEqual(
            post.comments.last(),
            PostPagesTest.comment_post
        )

    def test_paginator_correct_context(self):
        """Шаблон index, group_list и profile
        сформированы с корректным Paginator.
        """
        paginator_objects = []
        for i in range(1, 18):
            new_post = Post(
                author=PostPagesTest.user,
                text='Тестовый пост ' + str(i),
                group=PostPagesTest.group
            )
            paginator_objects.append(new_post)
        Post.objects.bulk_create(paginator_objects)
        paginator_data = {
            'index': reverse('posts:index'),
            'group': reverse(
                'posts:group_list',
                kwargs={'slug': PostPagesTest.group.slug}
            ),
            'profile': reverse(
                'posts:profile',
                kwargs={'username': PostPagesTest.user.username}
            )
        }
        for paginator_place, paginator_page in paginator_data.items():
            with self.subTest(paginator_place=paginator_place):
                response_page_1 = self.authorized_client.get(paginator_page)
                response_page_2 = self.authorized_client.get(
                    paginator_page + '?page=2'
                )
                self.assertEqual(len(
                    response_page_1.context['page_obj']),
                    10
                )
                self.assertEqual(len(
                    response_page_2.context['page_obj']),
                    8
                )

    def test_views_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for template, reverse_name in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def test_indext_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        expected = list(Post.objects.all()[:10])
        self.assertEqual(list(response.context.get('page_obj')), expected)

    def test_grouplist__page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        expected = list(Post.objects.filter(group_id=self.group.id)[:10])
        self.assertEqual(list(response.context.get('page_obj')), expected)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse("posts:profile", args=(self.post.author,))
        )
        expected = list(Post.objects.filter(author_id=self.user.id)[:10])
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        self.assertEqual(response.context.get("post").text, self.post.text)
        self.assertEqual(response.context.get("post").author, self.post.author)
        self.assertEqual(response.context.get("post").group, self.post.group)

    def test_create_edit_show_correct_context(self):
        """Шаблон create_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на страницах с выбранной группой"""
        form_fields = {
            reverse("posts:index"): Post.objects.get(group=self.post.group),
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                "posts:profile", kwargs={"username": self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный Пост с группой не попап в чужую группу."""
        form_fields = {
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertNotIn(expected, form_field)

    def test_index_caches(self):
        """Тестирование кэша главной страницы."""
        new_post = Post.objects.create(
            author=PostPagesTest.user,
            text='Этот пост создан быть удаленным)',
            group=PostPagesTest.group
        )
        response_1 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_1 = response_1.content
        new_post.delete()
        response_2 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_2 = response_2.content
        self.assertEqual(response_content_1, response_content_2)
        cache.clear()
        response_3 = self.authorized_client.get(
            reverse('posts:index')
        )
        response_content_3 = response_3.content
        self.assertNotEqual(response_content_2, response_content_3)

    def test_follow(self):
        """Тестирование подписки на автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='Kurva')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        follow = Follow.objects.last()
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author, new_author)
        self.assertEqual(follow.user, PostPagesTest.user)

    def test_unfollow(self):
        """Тестирование отписки от автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='Kurva')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow)

    def test_following_posts(self):
        """Тестирование появления поста автора в ленте подписчика."""
        new_user = User.objects.create(username='Kurva')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': PostPagesTest.user.username}
            )
        )
        response_follow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_follow = response_follow.context
        self.post_exist(context_follow)

    def test_unfollowing_posts(self):
        """Тестирование отсутствия поста автора у нового пользователя."""
        new_user = User.objects.create(username='Kurva')
        authorized_client = Client()
        authorized_client.force_login(new_user)
        response_unfollow = authorized_client.get(
            reverse('posts:follow_index')
        )
        context_unfollow = response_unfollow.context
        self.assertEqual(len(context_unfollow['page_obj']), 0)
