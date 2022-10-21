from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from ..models import Post, Group
from django.core.cache import cache

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='тестовый заголовок',
            slug='test-slug',
            description='тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        # # Создаем неавторизованный клиент
        self.guest_client = Client()
        cache.clear()
        # # Создаем авторизованый клиент автор
        self.user = PostURLTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_ne_author = User.objects.create_user(username='noname')
        self.ne_author = Client()
        self.ne_author.force_login(self.user_ne_author)

    def test_pages_uses_url_all_users(self):
        """Главная страница, страница группы, страница поста,"""
        """профайл пользователя доступны всем """
        path_names = {
            'index': '/',
            'group_page': f'/group/{self.group.slug}/',
            'profile-user': f'/profile/{self.user.username}/',
            'post-id': f'/posts/{self.post.id}/',
            'author': '/about/author/',
            'tech': '/about/tech/',
        }

        for template, address in path_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, 200)

    def test_pages_authorized_users(self):
        path_names = {
            'post-edit': f'/posts/{self.post.id}/edit/',
            'post-create': '/create/',
            'follow_index': '/follow/'
        }

        for template, address in path_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, 200)

    def test_not_page_all_users(self):
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_page_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_page_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_post_edit_guest_user(self):
        path_names = {
            'post_edit': f'/posts/{self.post.id}/edit/',
            'post_create': '/create/',
            'follow_index': '/follow/',
            'add_comment': f'/posts/{self.post.id}/edit/'
        }
        for template, address in path_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, 302)

    def test_post_edit_ne_author_users(self):
        response = self.ne_author.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, 302)
