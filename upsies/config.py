import configparser
from os.path import exists as _path_exists

from . import errors

import logging  # isort:skip
_log = logging.getLogger(__name__)


class Config:
    """
    Combine multiple INI-style configuration files into nested dictionaries

    Each top-level dictionary maps section names to sections (the configuration
    stored in one file). Each section maps section names from that file (which
    are subsections in this representation) to dictionaries that map option
    names to values.

    List values are stored with "\n" as a separator between list items.

    :param dict defaults: Nested directory structure as described above with
        default values filled in
    :param str files: Mapping of section names to file paths

    :raises ConfigError: if reading or parsing a file fails
    """
    def __init__(self, defaults, **files):
        self._defaults = defaults
        self._files = {}
        self._cfg = {}
        for section, filepath in files.items():
            self.read(section, filepath)

    def read(self, section, filepath, ignore_missing=False):
        """
        Read `filepath` and make its contents available as `section`

        :raises ConfigError: if reading or parsing a file fails
        """
        if ignore_missing and not _path_exists(filepath):
            self._cfg[section] = {}
            self._files[section] = filepath
        else:
            try:
                with open(filepath, 'r') as f:
                    string = f.read()
            except OSError as e:
                raise errors.ConfigError(f'{filepath}: {e.strerror}')
            else:
                cfg = self._parse(section, string, filepath)
                cfg = self._validate(section, cfg, filepath)
                self._cfg[section] = self._apply_defaults(section, cfg)
                self._files[section] = filepath

    def defaults(self, section):
        """
        Return the defaults for `section`

        :raises ValueError: if `section` does not exist
        """
        try:
            return self._defaults[section]
        except KeyError:
            raise ValueError(f'No such section: {section}')

    def _parse(self, section, string, filepath):
        cfg = configparser.ConfigParser(
            default_section=None,
            interpolation=None,
        )
        try:
            cfg.read_string(string, source=filepath)
        except configparser.MissingSectionHeaderError as e:
            raise errors.ConfigError(f'{filepath}: Line {e.lineno}: Option outside of section: {e.line.strip()}')
        except configparser.ParsingError as e:
            lineno, msg = e.errors[0]
            raise errors.ConfigError(f'{filepath}: Line {lineno}: Invalid syntax: {msg}')
        except configparser.DuplicateSectionError as e:
            raise errors.ConfigError(f'{filepath}: Line {e.lineno}: Duplicate section: {e.section}')
        except configparser.DuplicateOptionError as e:
            raise errors.ConfigError(f'{filepath}: Line {e.lineno}: Duplicate option: {e.option}')
        except configparser.Error as e:
            raise errors.ConfigError(f'{filepath}: {e}')
        else:
            # Make normal dictionary from ConfigParser instance
            # https://stackoverflow.com/a/28990982
            cfg = {s : dict(cfg.items(s))
                   for s in cfg.sections()}

            # Line breaks are interpreted as list separators
            for section in cfg.values():
                for key in section:
                    if '\n' in section[key]:
                        section[key] = [item for item in section[key].split('\n') if item]

            return cfg

    def _validate(self, section, cfg, filepath):
        if section not in self._defaults:
            raise errors.ConfigError(f'Unknown section: {section}')

        defaults = self.defaults(section)
        for subsect in cfg:
            if subsect not in defaults:
                raise errors.ConfigError(f'{filepath}: Unknown section: {subsect}')
            for option in cfg[subsect]:
                if option not in defaults[subsect]:
                    raise errors.ConfigError(
                        f'{filepath}: {subsect}: Unknown option: {option}')

        return cfg

    def _apply_defaults(self, section, cfg):
        defaults = self.defaults(section)
        for subsect in defaults:
            if subsect not in cfg:
                cfg[subsect] = defaults[subsect]
            else:
                for option in defaults[subsect]:
                    if option not in cfg[subsect]:
                        cfg[subsect][option] = defaults[subsect][option]
        return cfg

    def __getitem__(self, key):
        return self._cfg[key]
