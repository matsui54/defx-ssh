from pathlib import Path
from pynvim import Nvim
import site

from defx.action import ActionAttr
from defx.kind.file import Kind as Base
from defx.base.kind import action
from defx.clipboard import ClipboardAction
from defx.context import Context
from defx.defx import Defx
from defx.view import View

site.addsitedir(str(Path(__file__).parent.parent))
from ssh import SSHPath, SSHClient  # noqa: E402


class Kind(Base):

    def __init__(self, vim: Nvim, source) -> None:
        self.vim = vim
        self.name = 'ssh'
        self._source = source

    @property
    def client(self) -> SSHClient:
        return self._source.client

    def is_readable(self, path: SSHPath) -> bool:
        pass

    def get_home(self) -> SSHPath:
        return SSHPath(self.client, self.client.normalize('.'))

    def path_maker(self, path: str) -> SSHPath:
        return SSHPath(self.client, path)

    def rmtree(self, path: SSHPath) -> None:
        path.rmdir_recursive()

    def get_buffer_name(self, path: str) -> str:
        # TODO: return 'sftp://{}@{}'
        pass

    def paste(self, view: View, src: SSHPath, dest: SSHPath,
              cwd: str) -> None:
        action = view._clipboard.action
        if view._clipboard.source_name == 'file':
            if action == ClipboardAction.COPY:
                self._put_recursive(src, dest, self.client)
            elif action == ClipboardAction.MOVE:
                pass
            elif action == ClipboardAction.LINK:
                pass
            view._vim.command('redraw')

        if action == ClipboardAction.COPY:
            if src.is_dir():
                src.copy_recursive(dest)
            else:
                src.copy(dest)
        elif action == ClipboardAction.MOVE:
            src.rename(dest)

            # Check rename
            # TODO: add prefix
            if not src.is_dir():
                view._vim.call('defx#util#buffer_rename',
                               view._vim.call('bufnr', str(src)), str(dest))
        elif action == ClipboardAction.LINK:
            # Create the symbolic link to dest
            # dest.symlink_to(src, target_is_directory=src.is_dir())
            pass

    @action(name='copy')
    def _copy(self, view: View, defx: Defx, context: Context) -> None:
        super()._copy(view, defx, context)

        def copy_to_local(path: str, dest: str):
            client = defx._source.client
            self._copy_recursive(SSHPath(client, path), Path(dest), client)
        view._clipboard.paster = copy_to_local

    @action(name='remove_trash', attr=ActionAttr.REDRAW)
    def _remove_trash(self, view: View, defx: Defx, context: Context) -> None:
        view.print_msg('remove_trash is not supported')

    def _copy_recursive(self, path: SSHPath, dest: Path, client) -> None:
        """ copy remote files to the local host """
        if path.is_file():
            client.get(str(path), str(dest))
        else:
            dest.mkdir(parents=True)
            for f in path.iterdir():
                new_dest = dest.joinpath(f.name)
                self._copy_recursive(f, new_dest, client)

    def _put_recursive(self, path: Path, dest: SSHPath,
                       client: SSHClient) -> None:
        ''' copy local files to the remote host '''
        if path.is_file():
            client.put(str(path), str(dest))
        else:
            dest.mkdir()
            for f in path.iterdir():
                new_dest = dest.joinpath(f.name)
                self._put_recursive(f, new_dest, client)
