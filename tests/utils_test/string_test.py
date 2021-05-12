import pytest

from upsies.utils import string


def test_pretty_bytes():
    assert string.pretty_bytes(1023) == '1023 B'
    assert string.pretty_bytes(1024) == '1.00 KiB'
    assert string.pretty_bytes(1024 + 1024 / 2) == '1.50 KiB'
    assert string.pretty_bytes((1024**2) - 102.4) == '1023.90 KiB'
    assert string.pretty_bytes(1024**2) == '1.00 MiB'
    assert string.pretty_bytes((1024**3) * 123) == '123.00 GiB'
    assert string.pretty_bytes((1024**4) * 456) == '456.00 TiB'
    assert string.pretty_bytes((1024**5) * 456) == '456.00 PiB'


@pytest.mark.parametrize(
    argnames='ratings, exp_string',
    argvalues=(
        ((-0.0, -0.1, -10.5), '☆☆☆☆☆☆☆☆☆☆'),
        ((0, 0.1, 0.2, 0.3), '☆☆☆☆☆☆☆☆☆☆'), ((0.4, 0.5, 0.6), '⯪☆☆☆☆☆☆☆☆☆'), ((0.7, 0.8, 0.9), '★☆☆☆☆☆☆☆☆☆'),
        ((1, 1.1, 1.2, 1.3), '★☆☆☆☆☆☆☆☆☆'), ((1.4, 1.5, 1.6), '★⯪☆☆☆☆☆☆☆☆'), ((1.7, 1.8, 1.9), '★★☆☆☆☆☆☆☆☆'),
        ((2, 2.1, 2.2, 2.3), '★★☆☆☆☆☆☆☆☆'), ((2.4, 2.5, 2.6), '★★⯪☆☆☆☆☆☆☆'), ((2.7, 2.8, 2.9), '★★★☆☆☆☆☆☆☆'),
        ((3, 3.1, 3.2, 3.3), '★★★☆☆☆☆☆☆☆'), ((3.4, 3.5, 3.6), '★★★⯪☆☆☆☆☆☆'), ((3.7, 3.8, 3.9), '★★★★☆☆☆☆☆☆'),
        ((4, 4.1, 4.2, 4.3), '★★★★☆☆☆☆☆☆'), ((4.4, 4.5, 4.6), '★★★★⯪☆☆☆☆☆'), ((4.7, 4.8, 4.9), '★★★★★☆☆☆☆☆'),
        ((5, 5.1, 5.2, 5.3), '★★★★★☆☆☆☆☆'), ((5.4, 5.5, 5.6), '★★★★★⯪☆☆☆☆'), ((5.7, 5.8, 5.9), '★★★★★★☆☆☆☆'),
        ((6, 6.1, 6.2, 6.3), '★★★★★★☆☆☆☆'), ((6.4, 6.5, 6.6), '★★★★★★⯪☆☆☆'), ((6.7, 6.8, 6.9), '★★★★★★★☆☆☆'),
        ((7, 7.1, 7.2, 7.3), '★★★★★★★☆☆☆'), ((7.4, 7.5, 7.6), '★★★★★★★⯪☆☆'), ((7.7, 7.8, 7.9), '★★★★★★★★☆☆'),
        ((8, 8.1, 8.2, 8.3), '★★★★★★★★☆☆'), ((8.4, 8.5, 8.6), '★★★★★★★★⯪☆'), ((8.7, 8.8, 8.9), '★★★★★★★★★☆'),
        ((9, 9.1, 9.2, 9.3), '★★★★★★★★★☆'), ((9.4, 9.5, 9.6), '★★★★★★★★★⯪'), ((9.7, 9.8, 9.9), '★★★★★★★★★★'),
        ((10, 10.1, 10.5, 12), '★★★★★★★★★★'),
    ),
)
def test_star_rating(ratings, exp_string):
    for rating in ratings:
        assert string.star_rating(rating) == exp_string


def test_remove_prefix():
    assert string.remove_prefix('com.domain.www', 'com.') == 'domain.www'
    assert string.remove_prefix('com.domain.www', 'moc.') == 'com.domain.www'


def test_remove_suffix():
    assert string.remove_suffix('www.domain.com', '.com') == 'www.domain'
    assert string.remove_suffix('www.domain.com', '.moc') == 'www.domain.com'
