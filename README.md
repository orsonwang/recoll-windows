# Recoll

Recoll is a desktop full-text search tool. It finds keywords inside
documents as well as file names. 

* Versions are available for Linux and MS Windows.
* A WEB front-end with preview and download features can replace or
  supplement the GUI for remote use. 
* It can search most document formats. You may need external applications
  for text extraction. 
* It can reach any storage place: files, archive members, email
  attachments, transparently handling decompression. 
* One click will open the document inside a native editor or display an
  even quicker text preview. 
* The software is free, open source, and licensed under the GPL.

For more detail, see the [features page on the web site](https://www.recoll.org/pages/features.html) or
the [online documentation](https://www.recoll.org/pages/documentation.html). 

Most distributions feature prebuilt packages for Recoll, but if you need them, [the instructions for
building and installing are here](https://www.recoll.org/usermanual/usermanual.html#RCL.INSTALL.BUILDING).

## About this fork

This is a fork of [upstream Recoll](https://framagit.org/medoc92/recoll)
focused on a Windows (MSVC) build, with a few additions on top of the
original sources:

### Windows (MSVC 2022) build

The Windows build uses the qmake `.pro` files (Qt Creator shadow-build
layout), **not** meson — `meson.build` has no Windows path.

* **Toolchain:** Qt 6.8.2 (`msvc2022_64`) + Visual Studio 2022 Build Tools
  (MSVC 14.4x). Build each project by loading `vcvars64.bat` and running
  `qmake -spec win32-msvc` then `nmake release` in a shadow build dir.
* **Dependencies** (zlib, win-iconv, libxml2, libxslt, Xapian) are built
  separately into a `recolldeps/msvc/` tree that the `.pro` files reference
  through the `RECOLLDEPS` variable.
* **libmagic is disabled on Windows** (`ENABLE_LIBMAGIC` is undefined in
  `src/common/autoconfig-win.h`): it is impractical to build with MSVC and
  is only a last-resort MIME detector. MIME detection falls back to the
  extension map plus the configured `file` command.
* **Text rendering:** on Windows the app defaults `QT_QPA_PLATFORM` to
  `windows:fontengine=freetype` (Qt 6's DirectWrite engine renders without
  antialiasing under RDP / no GPU), and the bundled stylesheet sets an
  explicit CJK-friendly font family.
* **Archive filters:** `.7z` and `.rar` members are extracted with a bundled
  `7z.exe` (no `py7zr` / `rarfile` / `unrar` dependency).

The result is a portable set of binaries (`recoll.exe` GUI plus
`recollindex` / `recollq` / helpers) that can be shipped together with the
Qt runtime, the dependency DLLs, and a `Share/` tree of filters and data.

### Traditional Chinese (zh_TW / 台灣正體) UI

Upstream ships only Simplified Chinese. This fork adds a Taiwan Traditional
Chinese translation (`src/qtgui/i18n/recoll_zh_TW.ts`), selectable from
**Preferences → GUI configuration → Chinese (Traditional)**. As with the
other languages, the `.qm` is produced at build time with `lrelease`.

### User-friendly MIME type names in results

The result list and the optional *MIME type* table column previously showed
the raw MIME type (e.g. `application/pdf`). They now show a localized,
human-readable name instead (e.g. *PDF document* / *PDF 文件*), driven by a
translatable table in `src/qtgui/guiutils.cpp` with `image/`, `audio/` and
`video/` family fallbacks and a final fallback to the raw MIME type for
unlisted types. The command-line tools (`recollq`) intentionally keep the
raw MIME type.
