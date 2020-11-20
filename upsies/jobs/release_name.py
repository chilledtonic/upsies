import asyncio

from ..tools import release_name
from . import JobBase

import logging  # isort:skip
_log = logging.getLogger(__name__)


class ReleaseNameJob(JobBase):
    name = 'release-name'
    label = 'Release Name'

    @property
    def release_name(self):
        """:class:`ReleaseName` instance"""
        return self._release_name

    def initialize(self, content_path):
        self._release_name = release_name.ReleaseName(content_path)
        self.signal.add('release_name_updated')

    def execute(self):
        pass

    def release_name_selected(self, name):
        """
        Must be called by the UI when the user accepts the release name

        :param str name: Release name as accepted by the user
        """
        if name:
            self.send(name)
        self.finish()

    def fetch_info(self, *args, **kwargs):
        """
        Synchronous wrapper around :meth:`ReleaseName.fetch_info` that emits the
        `release_name_updated` signal after the release name is updated

        All arguments are passed on to :meth:`ReleaseName.fetch_info`.
        """
        task = asyncio.ensure_future(
            self.release_name.fetch_info(*args, **kwargs),
        )

        def fetch_info_done(task):
            exc = task.exception()
            if exc:
                self.exception(exc)
            else:
                self.handle_release_name_update()

        task.add_done_callback(fetch_info_done)

    def handle_release_name_update(self):
        self.signal.emit('release_name_updated', self.release_name)
