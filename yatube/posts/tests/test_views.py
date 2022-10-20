import shutil
import tempfile
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from ..models import Post, Group, User, Follow
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache


User = get_user_model()
TEST_POST_OFFSET = settings.POSTS_PER_PAGE - 1
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# Для сохранения media-файлов в тестах будет использоваться
# временная папка TEMP_MEDIA_ROOT, а потом мы ее удалим
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

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
        cache.clear()
        # # Создаем неавторизованный клиент
        self.guest_client = Client()
        # # Создаем авторизованый клиент
        self.user = PostViewTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары reverse(name):"имя_html_шаблона"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
                'posts/create_post.html',
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """в Шаблон index, group_list, profile  передан созданный пост."""
        """ пост находится первым на странице"""
        templates_pages_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user.username})
        }
        for reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][0]
                self.assertEqual(first_object, self.post)

    def test_newpost_isnot_in_notgroup(self):
        """ проверка на то что новый пост не попал в другие группы"""
        """ и не отображается на странице другого пользователя"""
        new_group = Group.objects.create(
            title='new_group',
            slug='new_group',
            description='new group for test'
        )
        new_user = User.objects.create_user(username='new_user')
        user_test = Client()
        user_test.force_login(new_user)
        templates_pages_names = {
            reverse('posts:group_list', kwargs={'slug': new_group.slug}),
            reverse('posts:profile',
                    kwargs={'username': new_user.username})
        }
        for reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj']
                self.assertNotIn(self.post, first_object)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        first_object = response.context['post']
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author.posts.count(),
                         self.post.author.posts.count())

    def test_create_for_edit_show_correct_context(self):
        """Шаблон post_create для редактирования поста ."""
        response_list = (
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for response_test in response_list:
            response = self.authorized_client.get(response_test)
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get(
                        'form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_index_page_show_correct_context(self):
        """в Шаблон index, group_list, profile  передан созданный пост."""
        """ пост находится первым на странице"""
        templates_pages_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user.username})
        }

        for reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][0]
                self.assertEqual(first_object, self.post)

    def test_error404_page(self):
        response = self.guest_client.get('/nonexist-page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.user = User.objects.create_user(username='user-test')
        cls.group = Group.objects.create(
            title='Заголовок для тестовой группы',
            slug='slug_test',
            description='Тестовое описание')
        cls.post = []
        for num_post in range(TEST_POST_OFFSET + settings.POSTS_PER_PAGE):
            cls.post.append(
                Post.objects.create(
                    text=f'Тестовый пост + {num_post}',
                    author=cls.user,
                    group=cls.group
                )
            )

    def setUp(self):
        # # Создаем неавторизованный клиент
        self.guest_client = Client()
        # # Создаем авторизованый клиент
        self.user = PaginatorViewsTest.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_paginators(self):
        list_namespace = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        }
        for reverse_name in list_namespace:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                # Проверка: количество постов на первой странице равно
                # POSTS_PER_PAGE=10.
                self.assertEqual(len(response.context['page_obj']),
                                 settings.POSTS_PER_PAGE)

    def test_second_page_paginators(self):
        list_namespace = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username})
        }
        for reverse_name in list_namespace:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name + '?page=2')
                # Проверка: количество постов на второй странице равно
                # POSTS_PER_PAGE=10.
                self.assertEqual(len(response.context['page_obj']),
                                 TEST_POST_OFFSET)


class ImageInPostView(TestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache.clear()
        cls.user = User.objects.create_user(username='test_user')
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
        cls.group = Group.objects.create(
            title='тестовый заголовок',
            slug='test-slug',
            description='тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )

    def setUp(self):
        # # Создаем авторизованый клиент
        self.user = ImageInPostView.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_image_in_context_testcase(self):
        templates_pages_names = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': self.user.username})
        }

        for reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                first_object = response.context['page_obj'][0]
                self.assertEqual(first_object, self.post)
                self.assertEqual(first_object.image, self.post.image)


class CacheTests(TestCase):
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
        self.user = CacheTests.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_cache_view(self):
        """Тест кэширования страницы index.html"""
        one_page = self.authorized_client.get(reverse('posts:index'))
        post_edit = Post.objects.get(id=1)
        post_edit.text = 'меняю текст'
        post_edit.save()
        two_page = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(one_page.content, two_page.content)
        cache.clear()
        three_page = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(one_page.content, three_page.content)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
        )

    def setUp(self):
        self.guest_client = Client()
        self.follower = User.objects.create_user(username='follower')
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)
        self.user = FollowTest.user
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_follow_view(self):
        follow_count = Follow.objects.count()
        self.follower_client.get(reverse('posts:profile_follow',
                                 kwargs={'username': self.user.username}))
        self.assertEqual(Follow.objects.all().count(), follow_count+1)

    def test_unfollow(self):
        self.follower_client.get(reverse('posts:profile_follow',
                                 kwargs={'username': self.user.username}))
        self.follower_client.get(reverse('posts:profile_unfollow',
                                 kwargs={'username': self.user.username}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_follow_guest(self):
        response = self.guest_client.get(reverse('posts:profile_follow',
                                         kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 302)

    def test_follow_author(self):
        response = self.author_client.get(reverse('posts:profile_follow',
                                          kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 302)

