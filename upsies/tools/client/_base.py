import abc

from ... import errors


class ClientApiBase(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self):
        """Name of the BitTorrent client"""
        pass

    @abc.abstractmethod
    def add_torrent(self, torrent_path, download_path):
        """
        Add torrent to client

        :param str torrent_path: Path to torrent file
        :param str download_path: Path to the file(s) of the torrent

        :raise TorrentError: if adding `torrent_path` fails

        :return: ID of the added torrent in the client or `None`
        """
        pass

    @staticmethod
    def read_torrent_file(torrent_path):
        """
        Return bytes from torrent file

        :param str torrent_path: Path to torrent file

        :raise TorrentError: if reading from `torrent_path` fails
        """
        try:
            with open(torrent_path, 'rb') as f:
                return f.read()
        except OSError as e:
            raise errors.TorrentError(f'{torrent_path}: {e.strerror}')
