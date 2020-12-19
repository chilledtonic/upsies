import os
from pathlib import Path
from unittest.mock import call, patch

import pytest

from upsies import __project_name__, errors
from upsies.utils import fs


def test_assert_file_readable_with_directory(tmp_path):
    with pytest.raises(errors.ContentError, match=rf'^{tmp_path}: Is a directory$'):
        fs.assert_file_readable(tmp_path)

def test_assert_file_readable_with_nonexisting_file(tmp_path):
    path = tmp_path / 'foo'
    with pytest.raises(errors.ContentError, match=rf'^{path}: No such file or directory$'):
        fs.assert_file_readable(path)

def test_assert_file_readable_with_unreadable_file(tmp_path):
    path = tmp_path / 'foo'
    path.write_text('bar')
    os.chmod(path, mode=0o000)
    try:
        with pytest.raises(errors.ContentError, match=rf'^{path}: Permission denied$'):
            fs.assert_file_readable(path)
    finally:
        os.chmod(path, mode=0o700)


def test_assert_dir_usable_with_file(tmp_path):
    path = tmp_path / 'foo'
    path.write_text('asdf')
    with pytest.raises(errors.ContentError, match=rf'^{path}: Not a directory$'):
        fs.assert_dir_usable(path)

def test_assert_dir_usable_with_nonexisting_directory(tmp_path):
    path = tmp_path / 'foo'
    with pytest.raises(errors.ContentError, match=rf'^{path}: Not a directory$'):
        fs.assert_dir_usable(path)

def test_assert_dir_usable_with_unreadable_directory(tmp_path):
    path = tmp_path / 'foo'
    path.mkdir()
    os.chmod(path, mode=0o333)
    try:
        with pytest.raises(errors.ContentError, match=rf'^{path}: Not readable$'):
            fs.assert_dir_usable(path)
    finally:
        os.chmod(path, mode=0o700)

def test_assert_dir_usable_with_unwritable_directory(tmp_path):
    path = tmp_path / 'foo'
    path.mkdir()
    os.chmod(path, mode=0o555)
    try:
        with pytest.raises(errors.ContentError, match=rf'^{path}: Not writable$'):
            fs.assert_dir_usable(path)
    finally:
        os.chmod(path, mode=0o700)

def test_assert_dir_usable_with_unexecutable_directory(tmp_path):
    path = tmp_path / 'foo'
    path.mkdir()
    os.chmod(path, mode=0o666)
    try:
        with pytest.raises(errors.ContentError, match=rf'^{path}: Not executable$'):
            fs.assert_dir_usable(path)
    finally:
        os.chmod(path, mode=0o700)


@patch('upsies.utils.fs.assert_dir_usable')
@patch('tempfile.mkdtemp')
def test_tmpdir_creates_our_temporary_directory(mkdtemp_mock, assert_dir_usable_mock, tmp_path):
    fs.tmpdir.cache_clear()
    mkdtemp_dir = tmp_path / 'undesired_directory_name'
    mkdtemp_dir.mkdir()
    mkdtemp_mock.return_value = str(mkdtemp_dir)
    dirpath = fs.tmpdir()
    assert dirpath == str(tmp_path / __project_name__)
    assert mkdtemp_mock.call_args_list == [call()]
    assert assert_dir_usable_mock.call_args_list == [call(dirpath)]

@patch('upsies.utils.fs.assert_dir_usable')
@patch('tempfile.mkdtemp')
def test_tmpdir_handles_existing_path(mkdtemp_mock, assert_dir_usable_mock, tmp_path):
    fs.tmpdir.cache_clear()
    mkdtemp_dir = tmp_path / 'undesired_directory_name'
    mkdtemp_dir.mkdir()
    existing_tmpdir = tmp_path / __project_name__
    existing_tmpdir.mkdir()
    mkdtemp_mock.return_value = str(mkdtemp_dir)
    dirpath = fs.tmpdir()
    assert dirpath == str(tmp_path / __project_name__)
    assert mkdtemp_mock.call_args_list == [call()]
    assert assert_dir_usable_mock.call_args_list == [call(dirpath)]

@patch('tempfile.mkdtemp')
def test_tmpdir_removes_redundant_temp_dir(mkdtemp_mock, tmp_path):
    fs.tmpdir.cache_clear()
    mkdtemp_dir = tmp_path / 'undesired_directory_name'
    mkdtemp_dir.mkdir()
    existing_tmpdir = tmp_path / __project_name__
    existing_tmpdir.mkdir()
    mkdtemp_mock.return_value = str(mkdtemp_dir)
    fs.tmpdir()
    assert not os.path.exists(mkdtemp_mock.return_value)


projectdir_test_cases = (
    ('path/to/foo', 'foo.upsies'),
    ('path/to/foo/', 'foo.upsies'),
    ('path/to//foo/', 'foo.upsies'),
    ('path/to//foo//', 'foo.upsies'),
    (None, '.'),
)

@pytest.mark.parametrize('content_path, exp_path', projectdir_test_cases)
@patch('upsies.utils.fs.assert_dir_usable')
def test_projectdir_does_not_exist(assert_dir_usable_mock, tmp_path, content_path, exp_path):
    fs.projectdir.cache_clear()
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        path = fs.projectdir(content_path)
        assert path == exp_path
        assert os.path.exists(path)
        assert os.access(path, os.R_OK | os.W_OK | os.X_OK)
    finally:
        os.chdir(cwd)

@pytest.mark.parametrize('content_path, exp_path', projectdir_test_cases)
@patch('upsies.utils.fs.assert_dir_usable')
def test_projectdir_exists(assert_dir_usable_mock, tmp_path, content_path, exp_path):
    fs.projectdir.cache_clear()
    cwd = os.getcwd()
    os.chdir(tmp_path)
    if exp_path != '.':
        os.mkdir(exp_path)
    assert os.path.exists(tmp_path / exp_path)
    try:
        path = fs.projectdir(content_path)
        assert path == exp_path
        assert os.path.exists(path)
        assert os.access(path, os.R_OK | os.W_OK | os.X_OK)
    finally:
        os.rmdir(tmp_path / exp_path)
        os.chdir(cwd)


def test_basename():
    import pathlib
    assert fs.basename('a/b/c') == 'c'
    assert fs.basename('a/b/c/') == 'c'
    assert fs.basename('a/b/c///') == 'c'
    assert fs.basename('a/b/c//d/') == 'd'
    assert fs.basename(pathlib.Path('a/b/c//d/')) == 'd'


def test_dirname():
    import pathlib
    assert fs.dirname('a/b/c') == 'a/b'
    assert fs.dirname('a/b/c/') == 'a/b'
    assert fs.dirname('a/b/c///') == 'a/b'
    assert fs.dirname('a/b/c//d/') == 'a/b/c'
    assert fs.dirname(pathlib.Path('a/b/c//d/')) == 'a/b/c'


def test_sanitize_path_on_unix(mocker):
    mocker.patch('upsies.utils.fs.os_family', return_value='unix')
    assert fs.sanitize_filename('foo/bar/baz') == 'foo_bar_baz'

def test_sanitize_path_on_windows(mocker):
    mocker.patch('upsies.utils.fs.os_family', return_value='windows')
    assert fs.sanitize_filename('foo<bar>baz :a"b/c \\1|2?3*4.txt') == 'foo_bar_baz _a_b_c _1_2_3_4.txt'


def test_file_extension():
    assert fs.file_extension('Something.x264-GRP.mkv') == 'mkv'
    assert fs.file_extension('Something.x264-GRP.mp4') == 'mp4'
    assert fs.file_extension('Something') == ''


def test_file_extension_gets_Path_object():
    assert fs.file_extension(Path('some/path') / 'to' / 'file.mkv') == 'mkv'


def test_file_list_recurses_into_subdirectories(tmp_path):
    (tmp_path / 'a.txt').write_bytes(b'foo')
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'b.txt').write_bytes(b'foo')
    (tmp_path / 'a' / 'b').mkdir()
    (tmp_path / 'a' / 'b' / 'b.txt').write_bytes(b'foo')
    (tmp_path / 'a' / 'b' / 'c').mkdir()
    (tmp_path / 'a' / 'b' / 'c' / 'c.txt').write_bytes(b'foo')
    assert fs.file_list(tmp_path) == (
        str((tmp_path / 'a.txt')),
        str((tmp_path / 'a' / 'b.txt')),
        str((tmp_path / 'a' / 'b' / 'b.txt')),
        str((tmp_path / 'a' / 'b' / 'c' / 'c.txt')),
    )

def test_file_list_sorts_files_naturally(tmp_path):
    (tmp_path / '3' / '500').mkdir(parents=True)
    (tmp_path / '3' / '500' / '1000.txt').write_bytes(b'foo')
    (tmp_path / '20').mkdir()
    (tmp_path / '20' / '9.txt').write_bytes(b'foo')
    (tmp_path / '20' / '10.txt').write_bytes(b'foo')
    (tmp_path / '20' / '99').mkdir()
    (tmp_path / '20' / '99' / '4.txt').write_bytes(b'foo')
    (tmp_path / '20' / '99' / '0001000.txt').write_bytes(b'foo')
    (tmp_path / '20' / '100').mkdir()
    (tmp_path / '20' / '100' / '7.txt').write_bytes(b'foo')
    (tmp_path / '20' / '100' / '300.txt').write_bytes(b'foo')
    assert fs.file_list(tmp_path) == (
        str((tmp_path / '3' / '500' / '1000.txt')),
        str((tmp_path / '20' / '9.txt')),
        str((tmp_path / '20' / '10.txt')),
        str((tmp_path / '20' / '99' / '4.txt')),
        str((tmp_path / '20' / '99' / '0001000.txt')),
        str((tmp_path / '20' / '100' / '7.txt')),
        str((tmp_path / '20' / '100' / '300.txt')),
    )

def test_file_list_filters_by_extensions(tmp_path):
    (tmp_path / 'bar.jpg').write_bytes(b'foo')
    (tmp_path / 'foo.txt').write_bytes(b'foo')
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'a1.txt').write_bytes(b'foo')
    (tmp_path / 'a' / 'a2.jpg').write_bytes(b'foo')
    (tmp_path / 'a' / 'b').mkdir()
    (tmp_path / 'a' / 'b' / 'b1.JPG').write_bytes(b'foo')
    (tmp_path / 'a' / 'b' / 'b2.TXT').write_bytes(b'foo')
    (tmp_path / 'a' / 'b' / 'c').mkdir()
    (tmp_path / 'a' / 'b' / 'c' / 'c1.Txt').write_bytes(b'foo')
    (tmp_path / 'a' / 'b' / 'c' / 'c2.jPG').write_bytes(b'foo')
    (tmp_path / 'a' / 'b' / 'c' / 'd').mkdir()
    (tmp_path / 'a' / 'b' / 'c' / 'd' / 'd1.txt').write_bytes(b'foo')
    (tmp_path / 'a' / 'b' / 'c' / 'd' / 'd2.txt').write_bytes(b'foo')
    assert fs.file_list(tmp_path, extensions=('jpg',)) == (
        str((tmp_path / 'a' / 'a2.jpg')),
        str((tmp_path / 'a' / 'b' / 'b1.JPG')),
        str((tmp_path / 'a' / 'b' / 'c' / 'c2.jPG')),
        str((tmp_path / 'bar.jpg')),
    )
    assert fs.file_list(tmp_path, extensions=('TXT',)) == (
        str((tmp_path / 'a' / 'a1.txt')),
        str((tmp_path / 'a' / 'b' / 'b2.TXT')),
        str((tmp_path / 'a' / 'b' / 'c' / 'c1.Txt')),
        str((tmp_path / 'a' / 'b' / 'c' / 'd' / 'd1.txt')),
        str((tmp_path / 'a' / 'b' / 'c' / 'd' / 'd2.txt')),
        str((tmp_path / 'foo.txt')),
    )
    assert fs.file_list(tmp_path, extensions=('jpg', 'txt')) == (
        str((tmp_path / 'a' / 'a1.txt')),
        str((tmp_path / 'a' / 'a2.jpg')),
        str((tmp_path / 'a' / 'b' / 'b1.JPG')),
        str((tmp_path / 'a' / 'b' / 'b2.TXT')),
        str((tmp_path / 'a' / 'b' / 'c' / 'c1.Txt')),
        str((tmp_path / 'a' / 'b' / 'c' / 'c2.jPG')),
        str((tmp_path / 'a' / 'b' / 'c' / 'd' / 'd1.txt')),
        str((tmp_path / 'a' / 'b' / 'c' / 'd' / 'd2.txt')),
        str((tmp_path / 'bar.jpg')),
        str((tmp_path / 'foo.txt')),
    )

def test_file_list_if_path_is_matching_nondirectory(tmp_path):
    path = tmp_path / 'foo.txt'
    path.write_bytes(b'foo')
    assert fs.file_list(path, extensions=('txt',)) == (str(path),)

def test_file_list_if_path_is_nonmatching_nondirectory(tmp_path):
    path = tmp_path / 'foo.txt'
    path.write_bytes(b'foo')
    assert fs.file_list(path, extensions=('png',)) == ()

def test_file_list_with_unreadable_subdirectory(tmp_path):
    (tmp_path / 'foo').write_bytes(b'foo')
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'a.txt').write_bytes(b'foo')
    (tmp_path / 'a' / 'b').mkdir()
    (tmp_path / 'a' / 'b' / 'b.txt').write_bytes(b'foo')
    os.chmod(tmp_path / 'a' / 'b', 0o000)
    try:
        assert fs.file_list(tmp_path) == (
            str((tmp_path / 'a' / 'a.txt')),
            str((tmp_path / 'foo')),
        )
    finally:
        os.chmod(tmp_path / 'a' / 'b', 0o700)


def test_file_tree():
    tree = (
        ('root', (
            ('sub1', (
                ('foo', 123),
                ('sub2', (
                    ('sub3', (
                        ('sub4', (
                            ('bar', 456),
                        )),
                    )),
                )),
                ('baz', 789),
            )),
        )),
    )

    assert fs.file_tree(tree) == '''
root
└─sub1
  ├─foo (123 B)
  ├─sub2
  │ └─sub3
  │   └─sub4
  │     └─bar (456 B)
  └─baz (789 B)
'''.strip()
