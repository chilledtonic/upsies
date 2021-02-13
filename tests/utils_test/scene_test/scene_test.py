from unittest.mock import Mock, call

import pytest

from upsies import errors
from upsies.utils import scene


# FIXME: The AsyncMock class from Python 3.8 is missing __await__(), making it
# not a subclass of typing.Awaitable.
class AsyncMock(Mock):
    def __call__(self, *args, **kwargs):
        async def coro(_sup=super()):
            return _sup.__call__(*args, **kwargs)
        return coro()


def test_scenedbs(mocker):
    existing_scenedbs = (Mock(), Mock(), Mock())
    submodules_mock = mocker.patch('upsies.utils.scene.submodules')
    subclasses_mock = mocker.patch('upsies.utils.scene.subclasses', return_value=existing_scenedbs)
    assert scene.scenedbs() == existing_scenedbs
    assert submodules_mock.call_args_list == [call('upsies.utils.scene')]
    assert subclasses_mock.call_args_list == [call(scene.SceneDbApiBase, submodules_mock.return_value)]


def test_scenedb_returns_ClientApiBase_instance(mocker):
    existing_scenedbs = (Mock(), Mock(), Mock())
    existing_scenedbs[0].configure_mock(name='foo')
    existing_scenedbs[1].configure_mock(name='bar')
    existing_scenedbs[2].configure_mock(name='baz')
    mocker.patch('upsies.utils.scene.scenedbs', return_value=existing_scenedbs)
    assert scene.scenedb('bar', x=123) is existing_scenedbs[1].return_value
    assert existing_scenedbs[1].call_args_list == [call(x=123)]

def test_scenedb_fails_to_find_scenedb(mocker):
    existing_scenedbs = (Mock(), Mock(), Mock())
    existing_scenedbs[0].configure_mock(name='foo')
    existing_scenedbs[1].configure_mock(name='bar')
    existing_scenedbs[2].configure_mock(name='baz')
    mocker.patch('upsies.utils.scene.scenedbs', return_value=existing_scenedbs)
    with pytest.raises(ValueError, match='^Unsupported scene release database: bam$'):
        scene.scenedb('bam', x=123)
    for c in existing_scenedbs:
        assert c.call_args_list == []
