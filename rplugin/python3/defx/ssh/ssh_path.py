from __future__ import annotations
import typing
from pathlib import PurePosixPath
import stat
import re


class SSHAttributes():
    pass


class SSHPath(PurePosixPath):
    def __new__(cls, path: str):
        self = super().__new__(cls, path)
        self.path: str = path
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
        for f in self.client.listdir_attr(self.path):
            yield self.joinpath(f.filename)

    def joinpath(self, name: str):
        sep = '' if self.path == '/' else '/'
        new_path = self.path + sep + name
        return SSHPath(self.client, new_path, stat)

    def mkdir(self, parents=False, exist_ok=False):
        # TODO: mkdir recursively
        self.client.mkdir(self.path)

    @property
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
            return self.client.stat(self.path)

    def touch(self, exist_ok=True):
        self.client.open(self.path, mode='x')

    def unlink(self, missing_ok=False):
        self.client.unlink(self.path)
