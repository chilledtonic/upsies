import abc
import asyncio
import json
import os

from .. import errors

import logging  # isort:skip
_log = logging.getLogger(__name__)


class JobBase(abc.ABC):
    """
    Base class for all jobs

    :param str homedir: Directory that is used to store files
    :param str ignore_cache: Whether cached output and previously created files
        should not be re-used
    :param bool quiet: Whether to hide this job's output

    Any additional keyword arguments are passed on to :meth:`initialize`.
    """

    @property
    @abc.abstractmethod
    def name(self):
        """Internal name (e.g. for the cache file name)"""
        pass

    @property
    @abc.abstractmethod
    def label(self):
        """User-facing name"""
        pass

    @property
    def homedir(self):
        """
        Directory that is used to store files

        Cached output is stored in a subdirectory called ".output".
        """
        return self._homedir

    @property
    def ignore_cache(self):
        """Whether cached output and previously created files should not be re-used"""
        return self._ignore_cache

    @property
    def quiet(self):
        """Whether to hide this job's output"""
        return self._quiet

    def __init__(self, *, homedir, ignore_cache, quiet=False, **kwargs):
        self._homedir = str(homedir)
        self._ignore_cache = bool(ignore_cache)
        self._quiet = bool(quiet)
        self._exception = None
        self._errors = []
        self._output = []
        self._output_callbacks = []
        self._error_callbacks = []
        self._finished_callbacks = []
        self._finished_event = asyncio.Event()
        self._kwargs = kwargs
        self.initialize(**kwargs)

    @abc.abstractmethod
    def initialize(self):
        """
        Called by :meth:`__init__` with additional keyword arguments

        This method should handle its arguments and return quickly.
        """
        pass

    @abc.abstractmethod
    def execute(self):
        """Do work, e.g. request user input or start background threads"""
        pass

    def start(self):
        """
        Called by the main entry point when this job is executed

        If there is cached output available, load it and mark this job as
        finished. Otherwise, call :meth:`execute`.
        """
        _log.debug('Running %r', self)
        self._read_output_cache()
        if self.output:
            _log.debug('Job was already done previously: %r', self)
            self._finished_event.set()
            for output in self.output:
                for cb in self._output_callbacks:
                    cb(output)
            for cb in self._finished_callbacks:
                cb(self)
        else:
            _log.debug('Executing %r', self)
            self.execute()

    async def wait(self):
        """
        Wait for this job to finish

        This method must be called. :attr:`is_finished` must be `False` before
        this method returns and `True` afterwards.

        It must be safe to call this method multiple times simultaneously.

        :raise: Any exceptions given to :meth:`exception`
        """
        await self._finished_event.wait()
        if self._exception is not None:
            raise self._exception

    def finish(self):
        """Mark this job as finished and unblock :meth:`wait`"""
        if not self.is_finished:
            self._finished_event.set()
            for cb in self._finished_callbacks:
                cb(self)
            self._write_output_cache()

    def on_finished(self, callback):
        """
        Call `callback` when job is finished

        :param callable callback: Callable that takes an instance of this class
            as a positional argument

        `callback` is called when :meth:`finish` is called and when cached
        output is read (i.e. :meth:`executed` is never called).
        """
        assert callable(callback)
        self._finished_callbacks.append(callback)

    @property
    def is_finished(self):
        """Whether this job is done"""
        return self._finished_event.is_set()

    @property
    def exit_code(self):
        """`0` if job was successful, `> 0` otherwise"""
        if self.is_finished:
            if not self.output or self.errors or self._exception:
                return 1
            else:
                return 0

    @property
    def output(self):
        """Result of this job as a sequence of strings"""
        return tuple(self._output)

    def send(self, output, if_not_finished=False):
        """
        Append `output` to :attr:`output`

        :param bool if_not_finished: Ignore this call if :attr:`is_finished` is
            True (`RuntimeError` is raised otherwise)
        """
        if not self.is_finished:
            if output:
                output_str = str(output)
                self._output.append(output_str)
                for cb in self._output_callbacks:
                    cb(output_str)
        else:
            if not if_not_finished:
                raise RuntimeError('send() called on finished job')

    def on_output(self, callback):
        """
        Call `callback` with output

        :param callable callback: Callable that takes an instance of this class
            as a positional argument

        `callback` is called when :meth:`send` is called and when cached output
        is read (i.e. :meth:`executed` is never called).
        """
        assert callable(callback)
        self._output_callbacks.append(callback)

    def pipe_input(self, value):
        """
        Called by :class:`Pipe` on the receiving job for each output from sending
        job
        """
        raise NotImplementedError(f'pipe_input() is not implemented in {type(self).__name__}')

    def pipe_closed(self):
        """
        Called by :class:`Pipe` on the receiving job when the sending job is
        finished
        """
        raise NotImplementedError(f'pipe_closed() is not implemented in {type(self).__name__}')

    @property
    def errors(self):
        """Sequence of reported errors (strings or exceptions)"""
        return tuple(self._errors)

    def error(self, error, if_not_finished=False):
        """
        Append `error` to :attr:`errors`

        :param bool if_not_finished: Ignore this call if :attr:`is_finished` is
            True
        """
        if not self.is_finished:
            self._errors.append(error)
            for cb in self._error_callbacks:
                cb(error)
        else:
            if not if_not_finished:
                raise RuntimeError('error() called on finished job')

    def on_error(self, callback):
        """
        Call `callback` with error

        :param callable callback: Callable that takes the argument given to
            :meth:`error`
        """
        assert callable(callback)
        self._error_callbacks.append(callback)

    def exception(self, exception):
        """
        Set exception to raise in :meth:`wait`

        :param Exception exception: Exception instance
        """
        if not self.is_finished:
            import traceback
            _log.debug(''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__)))
            self._exception = exception
        else:
            raise RuntimeError('exception() called on finished job')

    @property
    def info(self):
        """
        Additional information that is only displayed in the UI and not part of the
        job's result
        """
        return ''

    def _write_output_cache(self):
        """
        Store :attr:`output` in :attr:`cache_file`

        The base class implementation stores output as JSON. Child classes may
        want to use other formats.

        :raise RuntimeError: if :attr:`output` is not JSON-encodable or
            :attr:`cache_file` is not writable
        """
        if self.output and self.exit_code == 0 and self.cache_file:
            _log.debug('Writing output cache: %r: %r', self.cache_file, self.output)
            try:
                output_string = json.dumps(self.output)
            except (ValueError, TypeError) as e:
                raise RuntimeError(f'Unable to encode output as JSON: {self.output!r}: {e}')
            else:
                try:
                    with open(self.cache_file, 'w') as f:
                        f.write(output_string)
                        f.write('\n')
                except OSError as e:
                    raise RuntimeError(f'Unable to write cache {self.cache_file}: {e}')

    def _read_output_cache(self):
        """
        Set :attr:`output` to data stored in :attr:`cache_file`

        :raise RuntimeError: if :attr:`cache_file` exists and is unreadable or
            unparsable
        """
        if not self._ignore_cache and self.cache_file and os.path.exists(self.cache_file):
            _log.debug('Reading output cache: %r', self.cache_file)
            try:
                with open(self.cache_file, 'r') as f:
                    content = f.read()
            except OSError as e:
                raise RuntimeError(f'Unable to read cache {self.cache_file}: {e}')
            else:
                try:
                    self._output = json.loads(content)
                except (ValueError, TypeError) as e:
                    raise RuntimeError(f'Unable to decode JSON: {content!r}: {e}')

    @property
    def cache_directory(self):
        """
        Path to directory that stores cache files

        The directory is created if it doesn't exist.

        :raise PermissionError: if directory creation fails
        """
        path = os.path.join(self.homedir, '.output')
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except OSError as e:
                if getattr(e, 'strerror', None):
                    raise errors.PermissionError(f'{path}: {e.strerror}')
                else:
                    raise errors.PermissionError(f'{path}: Unable to create directory')
        return path

    @property
    def cache_file(self):
        """
        File path in :attr:`cache_directory` to store cached :attr:`output` in

        It is important that the file name is unique for each output. By
        default, this is achieved by including the keyword arguments for
        :meth:`initialize`. See :attr:`ScreenshotsJob.cache_file` for a
        different implementation.

        If this property returns a falsy value, no cache file is read or
        written.
        """
        if self._kwargs:
            def string_value(v):
                v = str(v)
                # Use same cache file for absolute and relative paths
                if os.path.exists(v):
                    v = os.path.realpath(v)
                return v

            kwargs_str_max_len = 250 - len(self.name) - len('..json')
            kwargs_str = ','.join(f'{k}={string_value(v)}'
                                  for k, v in self._kwargs.items())
            if len(kwargs_str) > kwargs_str_max_len:
                kwargs_str = ''.join((
                    kwargs_str[:int(kwargs_str_max_len / 2 - 1)],
                    '…',
                    kwargs_str[-int(kwargs_str_max_len / 2 - 1):],
                ))
            filename = f'{self.name}.{kwargs_str}.json'
        else:
            filename = f'{self.name}.json'
        filename = filename.replace("/", "_")
        assert len(filename) < 250
        return os.path.join(self.cache_directory, filename)
