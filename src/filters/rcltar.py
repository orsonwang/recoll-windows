#!/usr/bin/env python3

# Tar-file filter for Recoll
# Thanks to Recoll user Martin Ziegler
# This is a modified version of /usr/share/recoll/filters/rclzip.py
# It works not only for tar-files, but automatically for gzipped and
# bzipped tar-files at well.

import os
import sys
from typing import List
import posixpath

import rclexecm
from archivextract import ArchiveExtractor

try:
    import tarfile
except:
    print("RECFILTERROR HELPERNOTFOUND python3:tarfile")
    sys.exit(1)


class TarExtractor(ArchiveExtractor):
    def __init__(self, em: rclexecm.RclExecM) -> None:
        super().__init__(em)

    def extractone(self, ipath: bytes) -> tuple[bool, bytes, bytes, int]:
        docdata = b""
        try:
            info = self.tar.getmember(ipath)
            if info.size > self.em.maxmembersize:
                # skip
                docdata = b""
                self.em.rclog(f"extractone: entry {ipath!r} size {info.size} too big")
                docdata = b""  # raise TarError("Member too big")
            else:
                f = self.tar.extractfile(ipath)
                if f:
                    docdata = f.read()
                else:
                    docdata = b""
            self.em.setfield("filename", posixpath.basename(ipath))
            self.em.setfield("modificationdate", str(info.mtime))
            ok = True
        except Exception as err:
            self.em.rclog(f"Exception: {err}")
            ok = False
        iseof = rclexecm.RclExecM.noteof
        if self.currentindex >= self.namelistlen - 1:
            iseof = rclexecm.RclExecM.eofnext
        # We use fsencode, not makebytes, to convert to bytes. The latter would fail if the ipath
        # was actually binary, because it tries to encode to utf-8 but python3 had used fsdecode for
        # converting to str, and the result is not encodable to utf-8 (get: "surrogates
        # not allowed). We use fsdecode in getipath to revert the process.
        return (ok, docdata, os.fsencode(ipath), iseof)

    def closefile(self):
        self.tar = None
        self.namen = []

    def openfile(self, params):
        self.currentindex = -1
        filename = params["filename"]
        self.namefilter.setforlocation(filename)
        try:
            self.tar = tarfile.open(name=filename, mode="r")
            self.namelistlen = len(self.tar.getmembers())
            return True
        except:
            return False

    def getipath(self, params):
        ipath = os.fsdecode(params["ipath"])
        ok, data, ipath, eof = self.extractone(ipath)
        if ok:
            return (ok, data, ipath, eof)
        try:
            ipath = ipath.decode("utf-8")
            return self.extractone(ipath)
        except Exception as err:
            return (ok, data, ipath, eof)

    def getname(self, index):
        return self.tar.getmembers()[index].name 
    # getnext from ArchiveExtractor


proto = rclexecm.RclExecM()
extract = TarExtractor(proto)
rclexecm.main(proto, extract)
