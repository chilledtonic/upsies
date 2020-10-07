import base64
import json

from ... import errors
from ...utils import LazyModule
from . import ClientApiBase

import logging  # isort:skip
_log = logging.getLogger(__name__)

aiohttp = LazyModule(module='aiohttp', namespace=globals())


DEFAULT_URL = 'http://localhost:9091/transmission/rpc'
AUTH_ERROR_CODE = 401
CSRF_ERROR_CODE = 409
CSRF_HEADER = 'X-Transmission-Session-Id'


class ClientApi(ClientApiBase):
    """
    RPC for Transmission daemon

    https://github.com/transmission/transmission/blob/master/extras/rpc-spec.txt
    """

    name = 'transmission'

    def __init__(self, username='', password='', url=None):
        self._username = username
        self._password = password
        self._url = url or DEFAULT_URL
        self._headers = {'content-type': 'application/json'}

    async def _request(self, data):
        if self._username or self._password:
            auth = aiohttp.BasicAuth(self._username,
                                     self._password,
                                     encoding='utf-8')
        else:
            auth = None

        session_cm = aiohttp.ClientSession(
            auth=auth,
            headers=self._headers,
        )
        async with session_cm as session:
            try:
                request = await session.post(url=self._url, data=data)
            except aiohttp.ClientConnectionError:
                raise errors.TorrentError(f'{self._url}: Failed to connect')
            except aiohttp.ClientError as e:
                raise errors.TorrentError(f'{self._url}: {e}')

        if request.status == CSRF_ERROR_CODE:
            # Send request again with CSRF header
            self._headers[CSRF_HEADER] = request.headers[CSRF_HEADER]
            return await self._request(data)
        elif request.status == AUTH_ERROR_CODE:
            raise errors.TorrentError('Authentication failed')

        try:
            return await request.json()
        except aiohttp.ClientResponseError:
            text = await request.text()
            raise errors.TorrentError(f'Malformed JSON response: {text}')

    async def add_torrent(self, torrent_path, download_path=None):
        torrent_data = str(
            base64.b64encode(self.read_torrent_file(torrent_path)),
            encoding='ascii',
        )
        request = {
            'method' : 'torrent-add',
            'arguments' : {
                'metainfo': torrent_data,
            },
        }
        if download_path:
            request['arguments']['download-dir'] = str(download_path)

        response = await self._request(json.dumps(request))
        arguments = response.get('arguments', {})
        if 'torrent-added' in arguments:
            return arguments['torrent-added']['id']
        elif 'torrent-duplicate' in arguments:
            return arguments['torrent-duplicate']['id']
        elif 'result' in response:
            raise errors.TorrentError(str(response['result']).capitalize())
        else:
            raise errors.TorrentError('Adding failed for unknown reason')
