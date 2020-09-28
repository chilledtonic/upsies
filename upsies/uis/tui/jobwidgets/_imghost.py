from prompt_toolkit.application import get_app

from ....utils import cache
from .. import widgets
from . import _base

import logging  # isort:skip
_log = logging.getLogger(__name__)


class ImageHostJobWidget(_base.JobWidgetBase):
    def setup(self):
        self._upload_progress = widgets.ProgressBar()
        self.job.on_image_url(self.handle_image_url)
        self.job.on_uploads_finished(lambda _: get_app().invalidate())

    def activate(self):
        pass

    def handle_image_url(self, url):
        if self.job.images_total > 0:
            self._upload_progress.percent = self.job.images_uploaded / self.job.images_total * 100
            get_app().invalidate()

    @cache.property
    def runtime_widget(self):
        return self._upload_progress
