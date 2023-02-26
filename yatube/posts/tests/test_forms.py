import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    """Создаем тестовые посты, группу и форму."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Kurva')
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-descrip'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='old-text',
            group=cls.group
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.picture = 'posts/small.gif'

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        """Создаем клиент зарегистрированного пользователя."""
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        URL_CREATE = reverse('posts:post_create')
        URL_PROFILE = reverse(
            'posts:profile', kwargs={'username': PostFormTests.user.username}
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый пост',
            'group': PostFormTests.group.pk,
            'image': self.uploaded
        }
        response = self.authorized_client.post(
            URL_CREATE,
            data=form_data,
            follow=True
        )
        post = Post.objects.first()
        self.assertRedirects(response, URL_PROFILE)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(
            post.group, PostFormTests.group
        )
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, PostFormTests.user)
        self.assertEqual(post.image, self.picture)

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        URL_EDIT = reverse(
            'posts:post_edit', kwargs={'post_id': PostFormTests.post.pk}
        )
        URL_DETAIL = reverse(
            'posts:post_detail', kwargs={'post_id': PostFormTests.post.pk}
        )
        # тест работает только когда картинка под функцией
        # не понимаю, почему в первом случае работает?
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
        form_data = {
            'text': 'Измененный старый пост',
            'group': PostFormTests.group.pk,
            'image': uploaded
        }
        response = self.authorized_client.post(
            URL_EDIT,
            data=form_data,
            follow=True
        )
        post = Post.objects.get(pk=PostFormTests.post.pk)
        self.assertRedirects(response, URL_DETAIL)
        self.assertEqual(
            post.text,
            form_data['text']
        )
        self.assertEqual(
            post.group.pk,
            form_data['group']
        )

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        URL_COMMENT = reverse(
            'posts:add_comment', kwargs={'post_id': PostFormTests.post.pk}
        )
        URL_DETAIL = reverse(
            'posts:post_detail', kwargs={'post_id': PostFormTests.post.pk}
        )
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Новый остроумный комментарий'
        }
        response = self.authorized_client.post(
            URL_COMMENT,
            data=form_data,
            follow=True
        )
        comment = Comment.objects.first()
        self.assertRedirects(response, URL_DETAIL)
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.post, PostFormTests.post)
        self.assertEqual(comment.author, PostFormTests.user)
