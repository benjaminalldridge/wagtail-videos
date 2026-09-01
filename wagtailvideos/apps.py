from django.apps import AppConfig
from django.core.checks import register

from . import get_transcoder_backend


class WagtailVideosApp(AppConfig):
    name = "wagtailvideos"
    label = "wagtailvideos"
    verbose_name = "Wagtail Videos"
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        from wagtail.permissions import register_permission_policy

        from wagtailvideos import get_video_model
        from wagtailvideos.permissions import permission_policy
        from wagtailvideos.signals import register_signal_handlers

        register_permission_policy(get_video_model(), permission_policy)
        register_signal_handlers()

        backend = get_transcoder_backend()
        for check in backend.get_system_checks():
            register(check)
