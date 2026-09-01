from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTests
from wagtail.test.utils.form_data import nested_form_data, streamfield

from tests.app.models import TestPage
from tests.utils import create_test_video_file
from wagtailvideos.models import Video


class TestVideoBlock(WagtailPageTests):
    def setUp(self):
        super().setUp()
        self.root_page = Page.objects.get(pk=1)
        self.video = Video.objects.create(
            title="Test Video",
            file=create_test_video_file()
        )

    def test_block_admin(self):
        self.assertCanCreate(self.root_page, TestPage, nested_form_data({
            'title': 'VideoPage',
            'video_streamfield': streamfield([
                ('video', self.video.id)
            ])
        }))

    def test_block_basic_render(self):
        page = self.root_page.add_child(instance=TestPage(
            title='Test',
            slug='vidtest',
            video_streamfield=[
                ('video', self.video)
            ]
        ))
        Site.objects.create(
            hostname='localhost', port=8080, root_page=page,
            site_name='Test Site', is_default_site=True
        )
        response = self.client.get(page.full_url)

        self.assertContains(response, self.video.video_tag(attrs={"controls": True}))

    def test_page_background_colour_is_rendered(self):
        """A page persists its chosen background rather than deriving it at render time."""
        page = self.root_page.add_child(instance=TestPage(
            title="Coloured page",
            slug="coloured-page",
            page_background_colour="#336699",
        ))
        Site.objects.create(
            hostname="example.com",
            port=80,
            root_page=page,
            site_name="Example site",
            is_default_site=True,
        )

        response = self.client.get(page.full_url)

        self.assertContains(response, 'style="background-color: #336699"')
