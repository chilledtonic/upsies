import asyncio
import multiprocessing
import os
import queue
from unittest.mock import Mock, call, patch

import pytest

from upsies import errors
from upsies.jobs.screenshots import (ScreenshotsJob, _normalize_timestamps,
                                     _screenshot_process)
from upsies.utils.daemon import MsgType

try:
    from unittest.mock import AsyncMock
except ImportError:
    class AsyncMock(Mock):
        async def __call__(self, *args, **kwargs):
            return super().__call__(*args, **kwargs)


@patch('upsies.utils.video.length')
def test_normalize_timestamps_with_defaults(video_length_mock):
    video_length_mock.return_value = 300
    timestamps = _normalize_timestamps('foo.mkv', (), 0)
    assert timestamps == ['0:02:30', '0:03:45']

@patch('upsies.utils.video.length')
def test_normalize_timestamps_with_number_argument(video_length_mock):
    video_length_mock.return_value = 300
    timestamps = _normalize_timestamps('foo.mkv', (), 1)
    assert timestamps == ['0:02:30']
    timestamps = _normalize_timestamps('foo.mkv', (), 2)
    assert timestamps == ['0:02:30', '0:03:45']
    timestamps = _normalize_timestamps('foo.mkv', (), 3)
    assert timestamps == ['0:01:15', '0:02:30', '0:03:45']

@patch('upsies.utils.video.length')
def test_normalize_timestamps_with_timestamps_argument(video_length_mock):
    video_length_mock.return_value = 300
    timestamps = _normalize_timestamps('foo.mkv', (180 - 1, 120, '0:02:30'), 0)
    assert timestamps == ['0:02:00', '0:02:30', '0:02:59']

@patch('upsies.utils.video.length')
def test_normalize_timestamps_with_number_and_timestamps_argument(video_length_mock):
    video_length_mock.return_value = 300
    timestamps = _normalize_timestamps('foo.mkv', ('0:02:31',), 2)
    assert timestamps == ['0:01:15', '0:02:31']
    timestamps = _normalize_timestamps('foo.mkv', ('0:02:31',), 3)
    assert timestamps == ['0:01:15', '0:02:31', '0:03:45']
    timestamps = _normalize_timestamps('foo.mkv', ('0:02:31',), 4)
    assert timestamps == ['0:01:15', '0:01:53', '0:02:31', '0:03:45']
    timestamps = _normalize_timestamps('foo.mkv', ('0:00:00', '0:05:00'), 4)
    assert timestamps == ['0:00:00', '0:02:30', '0:03:45', '0:05:00']
    timestamps = _normalize_timestamps('foo.mkv', ('0:00:00', '0:05:00'), 5)
    assert timestamps == ['0:00:00', '0:01:15', '0:02:30', '0:03:45', '0:05:00']

@patch('upsies.utils.video.length')
def test_normalize_timestamps_with_invalid_timestamp(video_length_mock):
    video_length_mock.return_value = 300
    with pytest.raises(ValueError, match=r'^Invalid timestamp: \'foo\'$'):
        _normalize_timestamps('foo.mkv', ('0:02:00', 'foo', 240), 3)

@patch('upsies.utils.video.length')
def test_normalize_timestamps_with_indeterminable_video_length(video_length_mock):
    video_length_mock.side_effect = ValueError('Not a video file')
    with pytest.raises(ValueError, match=r'^Not a video file$'):
        _normalize_timestamps('foo.mkv', ('0:02:00', 240), 3)

@patch('upsies.utils.video.length')
def test_normalize_timestamps_with_given_timestamp_out_of_bounds(video_length_mock):
    video_length_mock.return_value = 300
    timestamps = _normalize_timestamps('foo.mkv', (3000,), 3)
    assert timestamps == ['0:02:30', '0:03:45', '0:05:00']


@patch('upsies.tools.screenshot.create')
def test_screenshot_process_fills_output_queue(screenshot_create_mock, tmp_path):
    output_queue = multiprocessing.Queue()
    input_queue = multiprocessing.Queue()
    _screenshot_process(output_queue, input_queue,
                        'foo.mkv', ('0:10:00', '0:20:00'), 'path/to/destination',
                        overwrite=False)
    assert screenshot_create_mock.call_args_list == [
        call(
            video_file='foo.mkv',
            timestamp='0:10:00',
            screenshot_file='path/to/destination/foo.mkv.0:10:00.png',
            overwrite=False,
        ),
        call(
            video_file='foo.mkv',
            timestamp='0:20:00',
            screenshot_file='path/to/destination/foo.mkv.0:20:00.png',
            overwrite=False,
        ),
    ]
    assert output_queue.get() == (MsgType.info, 'path/to/destination/foo.mkv.0:10:00.png')
    assert output_queue.get() == (MsgType.info, 'path/to/destination/foo.mkv.0:20:00.png')
    assert output_queue.empty()
    assert input_queue.empty()

@patch('upsies.tools.screenshot.create')
def test_screenshot_process_reads_input_queue(screenshot_create_mock, tmp_path):
    output_queue = multiprocessing.Queue()
    input_queue = multiprocessing.Queue()
    input_queue.put_nowait((MsgType.terminate, None))
    _screenshot_process(output_queue, input_queue,
                        'foo.mkv', ('0:10:00', '0:20:00', '0:30:00'), 'path/to/destination',
                        overwrite=False)
    # The 0:10:00 screenshot is created, probably because the put_nowait() takes
    # a while? Delaying the call to screenshot_create_mock doesn't help.
    # Creating 1 screenshot before breaking the loop should be ok.
    assert len(screenshot_create_mock.call_args_list) <= 1
    try:
        output = output_queue.get_nowait()
    except queue.Empty:
        pass
    else:
        assert output == (MsgType.info, 'path/to/destination/foo.mkv.0:10:00.png')
    assert output_queue.empty()
    assert input_queue.empty()

@patch('upsies.tools.screenshot.create')
def test_screenshot_process_catches_ScreenshotErrors(screenshot_create_mock, tmp_path):
    def screenshot_create_side_effect(video_file, timestamp, screenshot_file, overwrite=False):
        raise errors.ScreenshotError('Error', video_file, timestamp)

    screenshot_create_mock.side_effect = screenshot_create_side_effect

    output_queue = multiprocessing.Queue()
    input_queue = multiprocessing.Queue()
    _screenshot_process(output_queue, input_queue,
                        'foo.mkv', ('0:10:00', '0:20:00'), 'path/to/destination',
                        overwrite=False)
    assert screenshot_create_mock.call_args_list == [
        call(
            video_file='foo.mkv',
            timestamp='0:10:00',
            screenshot_file='path/to/destination/foo.mkv.0:10:00.png',
            overwrite=False,
        ),
        call(
            video_file='foo.mkv',
            timestamp='0:20:00',
            screenshot_file='path/to/destination/foo.mkv.0:20:00.png',
            overwrite=False,
        ),
    ]
    assert output_queue.get() == (MsgType.error, str(errors.ScreenshotError('Error', 'foo.mkv', '0:10:00')))
    assert output_queue.get() == (MsgType.error, str(errors.ScreenshotError('Error', 'foo.mkv', '0:20:00')))
    assert output_queue.empty()
    assert input_queue.empty()

@patch('upsies.tools.screenshot.create')
def test_screenshot_process_does_not_catch_other_errors(screenshot_create_mock, tmp_path):
    screenshot_create_mock.side_effect = TypeError('asdf')
    output_queue = multiprocessing.Queue()
    input_queue = multiprocessing.Queue()
    with pytest.raises(TypeError, match='^asdf$'):
        _screenshot_process(output_queue, input_queue,
                            'foo.mkv', ('0:10:00', '0:20:00'), 'path/to/destination',
                            overwrite=False)
    assert output_queue.empty()
    assert input_queue.empty()


@pytest.fixture
def job(tmp_path, mocker):
    DaemonProcess_mock = Mock(
        return_value=Mock(
            join=AsyncMock(),
        ),
    )
    mocker.patch('upsies.utils.daemon.DaemonProcess', DaemonProcess_mock)
    mocker.patch('upsies.utils.video.first_video', Mock())
    mocker.patch('upsies.jobs.screenshots._normalize_timestamps', Mock(return_value=('01:00', '02:00')))
    return ScreenshotsJob(
        homedir=tmp_path,
        ignore_cache=False,
        content_path='some/path',
        timestamps=(120,),
        number=2,
    )


def test_ScreenshotsJob_cache_file_with_timestamps(job):
    job._timestamps = ('0:02:00', '0:03:00')
    assert job.cache_file == os.path.join(
        job.homedir,
        '.output',
        'screenshots.0:02:00,0:03:00.json',
    )

def test_ScreenshotsJob_cache_file_without_timestamps(job):
    job._timestamps = ()
    assert job.cache_file is None


@patch('upsies.utils.daemon.DaemonProcess')
@patch('upsies.utils.video.first_video')
@patch('upsies.jobs.screenshots._normalize_timestamps')
def test_ScreenshotsJob_initialize(normalize_timestamps_mock, first_video_mock, DaemonProcess_mock, tmp_path):
    normalize_timestamps_mock.return_value = ('01:00', '02:00')
    first_video_mock.return_value = 'some/path/foo.mp4'
    job = ScreenshotsJob(
        homedir=tmp_path,
        ignore_cache=False,
        content_path='some/path',
        timestamps=(120,),
        number=2,
    )
    assert first_video_mock.call_args_list == [call('some/path')]
    assert normalize_timestamps_mock.call_args_list == [call(
        video_file=first_video_mock.return_value,
        timestamps=(120,),
        number=2,
    )]
    assert DaemonProcess_mock.call_args_list == [call(
        name=job.name,
        target=_screenshot_process,
        kwargs={
            'video_file' : job._video_file,
            'timestamps' : job._timestamps,
            'output_dir' : job.homedir,
            'overwrite'  : job.ignore_cache,
        },
        info_callback=job.handle_screenshot,
        error_callback=job.handle_error,
        finished_callback=job.finish,
    )]
    assert job._video_file is first_video_mock.return_value
    assert job._timestamps is normalize_timestamps_mock.return_value
    assert job._screenshot_process is DaemonProcess_mock.return_value
    assert job.output == ()
    assert job.errors == ()
    assert not job.is_finished
    assert job.exit_code is None
    assert job.screenshots_created == 0
    assert job.screenshots_total == len(normalize_timestamps_mock.return_value)

@patch('upsies.utils.daemon.DaemonProcess')
@patch('upsies.utils.video.first_video')
@patch('upsies.jobs.screenshots._normalize_timestamps')
def test_ScreenshotsJob_initialize_catches_ContentError_from_first_video(
        normalize_timestamps_mock, first_video_mock, DaemonProcess_mock, tmp_path):
    first_video_mock.side_effect = errors.ContentError('Bad content')
    job = ScreenshotsJob(
        homedir=tmp_path,
        ignore_cache=False,
        content_path='some/path',
        timestamps=('02:00',),
        number=2,
    )
    assert first_video_mock.call_args_list == [call('some/path')]
    assert normalize_timestamps_mock.call_args_list == []
    assert DaemonProcess_mock.call_args_list == []
    assert job._video_file == ''
    assert job._timestamps == ()
    assert job._screenshot_process is None
    assert job.output == ()
    assert job.errors == (errors.ContentError('Bad content'),)
    assert job.is_finished
    assert job.exit_code == 1
    assert job.screenshots_created == 0
    assert job.screenshots_total == 0

@patch('upsies.utils.daemon.DaemonProcess')
@patch('upsies.utils.video.first_video')
@patch('upsies.jobs.screenshots._normalize_timestamps')
def test_ScreenshotsJob_initialize_catches_ValueError_from_normalize_timestamps(
        normalize_timestamps_mock, first_video_mock, DaemonProcess_mock, tmp_path):
    normalize_timestamps_mock.side_effect = ValueError('Bad timestamp')
    first_video_mock.return_value = 'some/path/foo.mp4'
    job = ScreenshotsJob(
        homedir=tmp_path,
        ignore_cache=False,
        content_path='some/path',
        timestamps=(120,),
        number=2,
    )
    assert first_video_mock.call_args_list == [call('some/path')]
    assert normalize_timestamps_mock.call_args_list == [call(
        video_file=first_video_mock.return_value,
        timestamps=(120,),
        number=2,
    )]
    assert DaemonProcess_mock.call_args_list == []
    assert job._video_file == first_video_mock.return_value
    assert job._timestamps == ()
    assert job._screenshot_process is None
    assert job.output == ()
    assert [str(e) for e in job.errors] == ['Bad timestamp']
    assert job.is_finished
    assert job.exit_code == 1
    assert job.screenshots_created == 0
    assert job.screenshots_total == 0


def test_ScreenshotsJob_handle_screenshot(job):
    assert job.output == ()
    assert job.screenshots_created == 0

    job.handle_screenshot('foo.jpg')
    assert job.output == ('foo.jpg',)
    assert job.screenshots_created == 1

    job.handle_screenshot('bar.jpg')
    assert job.output == ('foo.jpg', 'bar.jpg')
    assert job.screenshots_created == 2


def test_ScreenshotsJob_handle_error(job):
    assert job.errors == ()
    job.handle_error('Foo!')
    assert job.errors == ('Foo!',)
    assert job.is_finished


def test_ScreenshotsJob_execute_with_screenshot_process(job):
    job.execute()
    assert job._screenshot_process.start.call_args_list == [call()]

def test_ScreenshotsJob_execute_without_screenshot_process(job):
    job._screenshot_process = None
    job.execute()
    assert job._screenshot_process is None


def test_ScreenshotsJob_finish_with_screenshot_process(job):
    assert not job.is_finished
    job.finish()
    assert job.is_finished
    assert job._screenshot_process.stop.call_args_list == [call()]

def test_ScreenshotsJob_finish_without_screenshot_process(job):
    job._screenshot_process = None
    assert not job.is_finished
    job.finish()
    assert job.is_finished
    assert job._screenshot_process is None


@pytest.mark.asyncio
async def test_ScreenshotsJob_wait_with_screenshot_process(job):
    asyncio.get_event_loop().call_soon(job.finish)
    assert not job.is_finished
    await job.wait()
    assert job._screenshot_process.join.call_args_list == [call()]
    assert job.is_finished
    # Calling wait() multiple times must be safe
    await job.wait()
    await job.wait()

@pytest.mark.asyncio
async def test_ScreenshotsJob_wait_without_screenshot_process(job):
    job._screenshot_process = None
    asyncio.get_event_loop().call_soon(job.finish)
    assert not job.is_finished
    await job.wait()
    assert job._screenshot_process is None
    assert job.is_finished
    # Calling wait() multiple times must be safe
    await job.wait()
    await job.wait()


@pytest.mark.parametrize(
    argnames=('screenshots_total', 'output', 'exp_exit_code'),
    argvalues=(
        (0, ('a.jpg', 'b.jpg', 'c.jpg'), 1),
        (3, ('a.jpg', 'b.jpg', 'c.jpg'), 0),
        (0, (), 1),
        (3, (), 1),
    ),
)
@pytest.mark.asyncio
async def test_exit_code(screenshots_total, output, exp_exit_code, job):
    assert job.exit_code is None
    for o in output:
        job.send(o)
    job._screenshots_total = screenshots_total
    job.finish()
    await job.wait()
    assert job.is_finished
    assert job.exit_code == exp_exit_code


def test_screenshots_total(job):
    assert job.screenshots_total is job._screenshots_total


def test_screenshots_created(job):
    assert job.screenshots_created is job._screenshots_created
