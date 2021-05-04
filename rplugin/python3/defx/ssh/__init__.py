from __future__ import annotations
import typing
from pathlib import PurePosixPath
import subprocess
import stat
import shlex


class SSHAttributes():
    def __init__(self):
        self.st_mode = None
        self.st_ino = None
        self.st_dev = None
        self.st_nlink = None
        self.st_uid = None
        self.st_gid = None
        self.st_size = None
        self.st_atime = None
        self.st_mtime = None
        self.st_ctime = None
        self.filename: str = ''

    @classmethod
    def from_str(cls, st_str):
        attr = cls()
        sl = shlex.split(st_str)
        attr.st_mode = sl[0]
        attr.st_ino = sl[1]
        attr.st_dev = sl[2]
        attr.st_nlink = sl[3]
        attr.st_uid = sl[4]
        attr.st_gid = sl[5]
        attr.st_size = sl[6]
        attr.st_atime = sl[7]
        attr.st_mtime = sl[8]
        attr.st_ctime = sl[9]
        attr.filename = sl[10]
        return attr


class SSHClient:
    def __init__(self):
        self.username: str = None
        self.hostname: str = None

    def request(self, cmd: typing.List[str]):
        cmd_base = ['ssh', '{}{}{}'.format(
            self.username, '@' if self.username else '',
            self.hostname)]
        cmd_base.extend(cmd)
        output = subprocess.run(cmd_base, stdout=subprocess.PIPE)
        return output.stdout.decode().strip().split('\n')


class SSHPath(PurePosixPath):
    def __new__(cls, client: SSHClient, path: str,
                stat: SSHAttributes = None):
        self = super().__new__(cls, path)
        self.client: SSHClient = client
        self.path: str = path
        self._stat = stat
        return self

    def __eq__(self, other):
        return self.__str__() == str(other)

    def __str__(self):
        return self.path

    def copy(self, dest: SSHPath) -> None:
        fl = self.client.open(self.path)
        self.client.putfo(fl, str(dest))

    def copy_recursive(self, dest: SSHPath) -> None:
        if self.is_file():
            self.copy(dest)
        else:
            dest.mkdir()
            for f in self.iterdir():
                new_dest = dest.joinpath(f.name)
                f.copy_recursive(new_dest)

    def exists(self):
        try:
            return bool(self.stat())
        except FileNotFoundError:
            return False

    def is_dir(self) -> bool:
        return not self.is_file()

    def is_file(self) -> bool:
        mode = self.stat().st_mode
        return stat.S_ISREG(mode)

    def is_symlink(self) -> bool:
        mode = self.stat().st_mode
        return stat.S_ISLNK(mode)

    def iterdir(self) -> typing.Iterable(SSHPath):
        files = self.client.request(['ls -A {}'.format(str(self))])
        files_quoted = [shlex.quote(str(self.joinpath(f))) for f in files]
        stat_cmd = ['stat', "--format='%f %i %d %h %u %g %s %X %Y %Z %N'"]
        stat_cmd.extend(files_quoted)
        stat_str = self.client.request(stat_cmd)
        for s in stat_str:
            st = SSHAttributes.from_str(s)
            yield SSHPath(self.client, st.filename, st)

    def joinpath(self, name: str):
        # use native?
        sep = '' if self.path == '/' else '/'
        new_path = self.path + sep + name
        return SSHPath(self.client, new_path)

    def mkdir(self, parents=False, exist_ok=False):
        # TODO: mkdir recursively
        self.client.mkdir(self.path)

    @ property
    def parent(self):
        if self.path == '/':
            return self
        parts = self.path.split('/')
        new_path = '/'.join(parts[:-1])
        return SSHPath(self.client, new_path)

    def relative_to(self, other) -> SSHPath:
        return self

    def rename(self, new: SSHPath) -> SSHPath:
        self.client.rename(self.path, new.path)

    def resolve(self) -> SSHPath:
        client = self.client
        new_path = client.normalize(self.path)
        return SSHPath(client, new_path)

    def rmdir(self):
        """
        Remove directory. Directory must be empty.
        """
        self.client.rmdir(self.path)

    def rmdir_recursive(self):
        if self.is_file():
            self.unlink()
        else:
            for f in self.iterdir():
                f.rmdir_recursive()
            self.rmdir()

    def stat(self) -> SSHAttributes:
        if self._stat:
            return self._stat
        else:
            stat_cmd = ['stat', "--format='%f %i %d %h %u %g %s %X %Y %Z %N'",
                        str(self)]
            stat_str = self.client.request(stat_cmd)[0]
            return SSHAttributes.from_str(stat_str)

    def touch(self, exist_ok=True):
        self.client.open(self.path, mode='x')

    def unlink(self, missing_ok=False):
        self.client.unlink(self.path)


if __name__ == '__main__':
    client = SSHClient()
    client.username = 'denjo'
    client.hostname = 'localhost'
    p = SSHPath(client, '/home/denjo/work/test')
    for f in p.iterdir():
        print(f, f.stat().st_mode)
