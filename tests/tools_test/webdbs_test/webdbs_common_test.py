import asyncio

import pytest

from upsies.tools import webdbs


def test_Query_title():
    with pytest.raises(TypeError):
        webdbs.Query()
    assert webdbs.Query('The Title').title == 'The Title'

def test_Query_year():
    assert webdbs.Query('The Title', year='2000').year == '2000'
    assert webdbs.Query('The Title', year=2000).year == '2000'
    with pytest.raises(ValueError, match=r'^Invalid year: 1000$'):
        webdbs.Query('The Title', year=1000)
    with pytest.raises(ValueError, match=r'^Invalid year: 3000$'):
        webdbs.Query('The Title', year=3000)
    with pytest.raises(ValueError, match=r'invalid literal for int\(\)'):
        webdbs.Query('The Title', year=2000.5)

def test_Query_type():
    assert webdbs.Query('The Title', type='movie').type == 'movie'
    assert webdbs.Query('The Title', type='series').type == 'series'
    assert webdbs.Query('The Title', type='Series').type == 'series'
    with pytest.raises(ValueError, match=r'^Invalid type: foo$'):
        webdbs.Query('The Title', type='foo')

@pytest.mark.parametrize(
    argnames=('string', 'exp_query'),
    argvalues=(
        ('The Title', webdbs.Query('The Title', type=None, year=None)),
        ('The Title type:movie', webdbs.Query('The Title', type='movie', year=None)),
        ('The Title type:series', webdbs.Query('The Title', type='series', year=None)),
        ('The Title year:2000', webdbs.Query('The Title', type=None, year='2000')),
        ('The Title year:2003', webdbs.Query('The Title', type=None, year='2003')),
        ('The Title type:movie year:2000', webdbs.Query('The Title', type='movie', year='2000')),
        ('The Title type:series year:2003', webdbs.Query('The Title', type='series', year='2003')),
        ('The Title type:film', webdbs.Query('The Title', type='movie')),
        ('The Title type:tv', webdbs.Query('The Title', type='series')),
        ('The Title type:show', webdbs.Query('The Title', type='series')),
        ('The Title type:tvshow', webdbs.Query('The Title', type='series')),
        ('The Title type:episode', webdbs.Query('The Title', type='series')),
    ),
)
def test_Query_from_string(string, exp_query):
    assert webdbs.Query.from_string(string) == exp_query

@pytest.mark.parametrize(
    argnames=('string', 'exp_query'),
    argvalues=(
        ('The Title type:foo', webdbs.Query('The Title type:foo', type=None, year=None)),
        ('The Title year:bar', webdbs.Query('The Title year:bar', type=None, year=None)),
    ),
)
def test_Query_from_string_with_unknown_value(string, exp_query):
    assert webdbs.Query.from_string(string) == exp_query

@pytest.mark.parametrize(
    argnames=('path', 'exp_query'),
    argvalues=(
        ('path/to/The Title', webdbs.Query('The Title', type='movie', year=None)),
        ('path/to/The Title 2015', webdbs.Query('The Title', type='movie', year='2015')),
        ('path/to/The Title S04', webdbs.Query('The Title', type='series', year=None)),
        ('path/to/The Title 2015 S04', webdbs.Query('The Title', type='series', year='2015')),
    ),
)
def test_Query_from_path(path, exp_query):
    assert webdbs.Query.from_path(path) == exp_query

@pytest.mark.parametrize(
    argnames=('a', 'b'),
    argvalues=(
        (webdbs.Query('The Title'), webdbs.Query('The Title')),
        (webdbs.Query('The Title'), webdbs.Query('the title')),
        (webdbs.Query('The Title'), webdbs.Query('the title ')),
        (webdbs.Query('The Title'), webdbs.Query(' the title')),
        (webdbs.Query('The Title'), webdbs.Query(' the title ')),
        (webdbs.Query('The Title'), webdbs.Query('the  title')),
        (webdbs.Query('The Title'), webdbs.Query('the  title ')),
        (webdbs.Query('The Title'), webdbs.Query(' the title')),
        (webdbs.Query('The Title', year='2000'), webdbs.Query('The Title', year='2000')),
        (webdbs.Query('The Title', type='movie'), webdbs.Query('The Title', type='movie')),
        (webdbs.Query('The Title', type='series'), webdbs.Query('The Title', type='series')),
        (webdbs.Query('The Title', type='series', year=2000), webdbs.Query('The Title', type='series', year=2000)),
    ),
    ids=lambda value: str(value),
)
def test_Query_equality(a, b):
    assert a == b
    assert b == a

@pytest.mark.parametrize(
    argnames=('a', 'b'),
    argvalues=(
        (webdbs.Query('The Title'), webdbs.Query('The Title 2')),
        (webdbs.Query('The Title', year='2000'), webdbs.Query('The Title', year='2001')),
        (webdbs.Query('The Title', type='movie'), webdbs.Query('The Title', type='series')),
        (webdbs.Query('The Title', type='series'), webdbs.Query('The Title', type='movie')),
        (webdbs.Query('The Title', type='series', year=2000), webdbs.Query('The Title', type='movie', year=2000)),
        (webdbs.Query('The Title', type='series', year=2000), webdbs.Query('The Title', type='series', year=2001)),
        (webdbs.Query('The Title', type='series', year=2000), webdbs.Query('The Title', type='movie', year=2001)),
    ),
    ids=lambda value: str(value),
)
def test_Query_inequality(a, b):
    assert a != b
    assert b != a

@pytest.mark.parametrize(
    argnames=('query', 'exp_string'),
    argvalues=(
        (webdbs.Query('The Title', type=None, year=None), 'The Title'),
        (webdbs.Query('The Title', type='movie', year=None), 'The Title type:movie'),
        (webdbs.Query('The Title', type='series', year=None), 'The Title type:series'),
        (webdbs.Query('The Title', type='movie', year='2010'), 'The Title year:2010 type:movie'),
    ),
    ids=lambda value: str(value),
)
def test_Query_as_string(query, exp_string):
    assert str(query) == exp_string


@pytest.mark.parametrize(
    argnames=('query', 'exp_repr'),
    argvalues=(
        (webdbs.Query('The Title', type=None, year=None), "Query(title='The Title')"),
        (webdbs.Query('The Title', type='movie', year=None), "Query(title='The Title', type='movie')"),
        (webdbs.Query('The Title', type=None, year='1999'), "Query(title='The Title', year='1999')"),
        (webdbs.Query('The Title', type='series', year='1999'), "Query(title='The Title', year='1999', type='series')"),
    ),
    ids=lambda value: str(value),
)
def test_Query_as_repr(query, exp_repr):
    assert repr(query) == exp_repr


@pytest.mark.asyncio
async def test_gather_preserves_affiliation():
    async def foo(id):
        await asyncio.sleep(0.1)
        return f'{id}:foo'

    async def bar(id):
        return f'{id}:bar'

    assert await webdbs.gather('123', foo, bar) == {
        'foo' : '123:foo',
        'bar' : '123:bar',
    }


def test_SearchResult_with_all_info():
    info = {
        'id' : '123',
        'url' : 'http://foo.bar/123',
        'type' : 'movie',
        'year' : '2000',
        'title' : 'Foo',
        'title_original' : 'Le Foo',
        'title_english' : 'Fucking Foo',
        'keywords' : ('foo', 'some bar'),
        'cast' : ('This Guy', 'That Dude'),
        'summary' : 'I dunno.',
        'country' : 'Antarctica',
    }
    sr = webdbs.SearchResult(**info)
    for k, v in info.items():
        assert getattr(sr, k) == v

def test_SearchResult_with_only_mandatory_info():
    info = {
        'id' : '123',
        'url' : 'http://foo.bar/123',
        'type' : 'movie',
        'year' : '2000',
        'title' : 'Foo',
    }
    sr = webdbs.SearchResult(**info)
    for k, v in info.items():
        assert getattr(sr, k) == v

def test_SearchResult_with_lacking_mandatory_info():
    info = {
        'id' : '123',
        'url' : 'http://foo.bar/123',
        'type' : 'movie',
        'year' : '2000',
        'title' : 'Foo',
    }
    for k in info:
        info_ = info.copy()
        del info_[k]
        with pytest.raises(TypeError, match=rf'missing 1 required keyword-only argument: {k!r}'):
            webdbs.SearchResult(**info_)

def test_SearchResult_with_valid_type():
    info = {
        'id' : '123',
        'url' : 'http://foo.bar/123',
        'year' : '2000',
        'title' : 'Foo',
    }
    for type in ('movie', 'series', 'episode', ''):
        sr = webdbs.SearchResult(type=type, **info)
        assert sr.type == type

def test_SearchResult_with_invalid_type():
    info = {
        'id' : '123',
        'url' : 'http://foo.bar/123',
        'year' : '2000',
        'title' : 'Foo',
    }
    for type in ('foo', 'bar', 'baz', None):
        with pytest.raises(ValueError, match=rf'Invalid type: {type!r}'):
            webdbs.SearchResult(type=type, **info)


print(webdbs)
print(dir(webdbs))
movie_webdbs = {webdbs.imdb, webdbs.tmdb}
series_webdbs = {webdbs.imdb, webdbs.tvmaze, webdbs.tmdb}
all_webdbs = movie_webdbs | series_webdbs

@pytest.mark.asyncio
@pytest.mark.parametrize('db', all_webdbs, ids=(db.label for db in all_webdbs))
async def test_search_returns_SearchResults(db, store_response):
    results = await db.search(webdbs.Query('Star Wars'))
    for r in results:
        assert isinstance(r, webdbs.SearchResult)

@pytest.mark.asyncio
@pytest.mark.parametrize('db', all_webdbs, ids=(db.label for db in all_webdbs))
async def test_search_for_specific_year(db, store_response):
    results = await db.search(webdbs.Query('Star Wars Clone Wars', year=2008))
    assert results[0].year == '2008'
    results = await db.search(webdbs.Query('Star Wars Clone Wars', year=2003))
    assert results[0].year == '2003'

@pytest.mark.asyncio
@pytest.mark.parametrize('db', movie_webdbs, ids=(db.label for db in movie_webdbs))
async def test_search_for_movie(db, store_response):
    results = await db.search(webdbs.Query('Star Wars', type='movie'))
    assert results[0].type == 'movie'

@pytest.mark.asyncio
@pytest.mark.parametrize('db', series_webdbs, ids=(db.label for db in series_webdbs))
async def test_search_for_series(db, store_response):
    results = await db.search(webdbs.Query('Star Wars', type='series'))
    assert results[0].type == 'series'


expected_coroutine_functions = (
    'search', 'gather', 'summary', 'title_english', 'title_original', 'year',
)
expected_strings = ('label', '_url_base')

@pytest.mark.asyncio
@pytest.mark.parametrize('db', all_webdbs, ids=(db.label for db in all_webdbs))
async def test_mandatory_module_attributes(db, store_response):
    for attr in expected_coroutine_functions:
        assert hasattr(db, attr)
        assert asyncio.iscoroutinefunction(getattr(db, attr))

    for attr in expected_strings:
        assert hasattr(db, attr)
        assert isinstance(getattr(db, attr), str)
