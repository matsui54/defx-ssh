import re
from pathlib import Path
import site
import typing
from urllib.parse import urlparse

from pynvim import Nvim

from defx.util import error
from defx.context import Context
from defx.base.source import Base

site.addsitedir(str(Path(__file__).parent.parent))
from ssh import SSHPath, SSHClient  # noqa: E402


class Source(Base):
    def __init__(self, vim: Nvim) -> None:
        super().__init__(vim)
        self.name = 'ssh'

        self.client: SSHClient = SSHClient()

        from kind.ssh import Kind
        self.kind: Kind = Kind(self.vim, self)

        self.vars = {
            'root': None,
        }

    def init_client(self, hostname, username) -> None:
        pass

    def get_root_candidate(
            self, context: Context, path: Path
    ) -> typing.Dict[str, typing.Any]:
        self.vim.call('defx#util#print_message', str(path))
        path_str = self._parse_arg(str(path))
        path = SSHPath(self.client, path_str)
        word = str(path)
        if word[-1:] != '/':
            word += '/'
        if self.vars['root']:
            word = self.vim.call(self.vars['root'], str(path))
        word = word.replace('\n', '\\n')
        return {
            'word': word,
            'is_directory': True,
            'action__path': path,
        }

    def gather_candidates(
            self, context: Context, path: Path
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        path_str = self._parse_arg(str(path))
        path = SSHPath(self.client, path_str)

        candidates = []
        for f in path.iterdir():
            candidates.append({
                'word': f.name,
                'is_directory': f.is_dir(),
                'action__path': f,
            })
        return candidates

    def _parse_arg(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.username:
            self.client.username = parsed.username
        if parsed.hostname:
            self.client.hostname = parsed.hostname
        return parsed.path
