#!/usr/bin/env python3
"""RAR archive filter for Recoll.

This version uses the 7-Zip command-line program (7z) to list and extract
archive members, instead of the python rarfile/unrar modules. 7z can read
RAR (including RAR5) archives, and is already bundled with the Windows
distribution, so no separate unrar binary or python module is needed.

7z is located through rclexecm.which(), which searches the filters directory
first, so dropping 7z.exe into Share/filters is enough.

The archive is decompressed ONCE to a temporary directory (not once per
member): extracting a member at a time would re-open/re-scan the archive for
every member and buffer each member fully in memory. Members are then read from
disk, and members larger than the configured maxmembersize are skipped without
being read.
"""

# Copyright (C) 2004-2025 J.F.Dockes
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sys
import os
import shutil
import posixpath
import subprocess

import rclexecm
from archivextract import ArchiveExtractor

# Locate the 7z program. rclexecm.which() searches the filter directory first,
# so the bundled Share/filters/7z.exe is found without a system install.
sevenz = rclexecm.which("7z")
if not sevenz:
    print("RECFILTERROR HELPERNOTFOUND 7z")
    sys.exit(1)


class RarExtractor(ArchiveExtractor):
    def __init__(self, em):
        self.filename = None
        self.names = []
        self.sizes = {}
        self.tmpdir = None
        self.extracted = False
        super().__init__(em)

    ###### File type handler api, used by rclexecm ---------->
    def openfile(self, params):
        self.filename = params["filename"]
        self.currentindex = -1
        self.extracted = False
        self.namefilter.setforlocation(self.filename)
        try:
            self.names, self.sizes = self._listnames(self.filename)
            self.namelistlen = len(self.names)
            return True
        except Exception as err:
            self.em.rclog("openfile: failed: [%s]" % err)
            return False

    def _listnames(self, fn):
        """Return (names, sizes) for the non-directory members, parsed from the
        '7z l -slt' technical listing output."""
        out = subprocess.check_output(
            [sevenz, "l", "-slt", "-ba", fn],
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        names = []
        sizes = {}
        cur = {}
        for raw in out.split(b"\n"):
            line = raw.rstrip(b"\r")
            if line == b"":
                self._addname(cur, names, sizes)
                cur = {}
                continue
            key, sep, val = line.partition(b" = ")
            if sep:
                cur[key] = val
        self._addname(cur, names, sizes)
        return names, sizes

    @staticmethod
    def _isdir(cur):
        if cur.get(b"Folder", b"") == b"+":
            return True
        return cur.get(b"Attributes", b"")[:1] == b"D"

    def _addname(self, cur, names, sizes):
        path = cur.get(b"Path")
        if path is None or self._isdir(cur):
            return
        name = path.decode("utf-8", "replace")
        names.append(name)
        try:
            sizes[name] = int(cur.get(b"Size", b"0") or b"0")
        except ValueError:
            sizes[name] = 0

    def getname(self, index):
        return self.names[index]

    def _ensure_extracted(self):
        """Decompress the whole archive to a temp dir, once. Best effort: the
        return code is ignored so that a single bad/unreadable member does not
        abort extraction of the others. stdin=DEVNULL makes a password prompt on
        an encrypted archive fail fast instead of blocking forever."""
        if self.extracted:
            return
        if self.tmpdir is None:
            self.tmpdir = rclexecm.SafeTmpDir("rclrar")
        dest = self.tmpdir.getpath()
        self._cleartmp(dest)
        subprocess.run(
            [sevenz, "x", "-y", "-o" + dest, self.filename],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.extracted = True

    @staticmethod
    def _cleartmp(d):
        # SafeTmpDir.vacuumdir() only removes top-level files; extracted
        # members may live in subdirectories, so clear recursively to avoid
        # accumulating them across the many archives one filter process handles.
        for fn in os.listdir(d):
            p = os.path.join(d, fn)
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p, True)
                else:
                    os.unlink(p)
            except OSError:
                pass

    def _memberpath(self, member):
        parts = member.replace("\\", "/").split("/")
        return os.path.join(self.tmpdir.getpath(), *parts)

    def extractone(self, ipath):
        # ipath may be str (from getname) or bytes (from getipath round-trip).
        member = ipath.decode("utf-8", "replace") if isinstance(ipath, bytes) else ipath
        docdata = b""
        ok = False
        try:
            if self.sizes.get(member, 0) > self.em.maxmembersize:
                self.em.rclog("extractone: [%s] over maxmembersize, skipped" % member)
                ok = True
            else:
                self._ensure_extracted()
                with open(self._memberpath(member), "rb") as f:
                    docdata = f.read()
                ok = True
        except Exception as err:
            self.em.rclog("extractone: failed: [%s]" % err)

        iseof = rclexecm.RclExecM.noteof
        if self.currentindex >= self.namelistlen - 1:
            iseof = rclexecm.RclExecM.eofnext
        self.em.setfield("filename", posixpath.basename(member))
        return (ok, docdata, rclexecm.makebytes(ipath), iseof)

    def closefile(self):
        if self.extracted and self.tmpdir is not None:
            self._cleartmp(self.tmpdir.getpath())

    # getipath from ArchiveExtractor
    # getnext from ArchiveExtractor


# Main program: create protocol handler and extractor and run them
proto = rclexecm.RclExecM()
extract = RarExtractor(proto)
rclexecm.main(proto, extract)
