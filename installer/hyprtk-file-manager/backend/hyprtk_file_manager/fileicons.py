"""File-type icons resolved against the active icon theme (Papirus-friendly).

Files are typed with GIO's shared-mime-info database and mapped to the
freedesktop icon names that icon themes such as Papirus ship under
``mimetypes/``.  Candidates are checked against the active theme so a missing
specific icon falls through to the next generic one instead of a blank icon.
"""

from __future__ import annotations

import mimetypes
import os
from functools import lru_cache
from pathlib import Path

try:
    import gi

    gi.require_version("Gio", "2.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gio, GLib, Gtk

    _THEME = Gtk.IconTheme.get_default()
except Exception:  # pragma: no cover - PyGObject is a runtime dependency
    Gio = GLib = Gtk = None
    _THEME = None

FILE_FALLBACK = "text-x-generic"
DIR_FALLBACK = "folder"
LINK_FALLBACK = "emblem-symbolic-link"

MAJOR_FALLBACK = {
    "image": "image-x-generic",
    "audio": "audio-x-generic",
    "video": "video-x-generic",
    "font": "font-x-generic",
    "model": "image-x-generic",
    "text": "text-x-generic",
    "message": "text-x-generic",
    "multipart": "package-x-generic",
}

EXT_ICONS = {
    # source code where the MIME guess is wrong or Papirus has a better match
    "ts": "text-x-javascript",
    "tsx": "text-x-javascript",
    "mts": "text-x-javascript",
    "cts": "text-x-javascript",
    "r": "text-x-r",
    "mod": "text-x-generic",
    # packages / archives
    "jar": "application-x-java-archive",
    "war": "application-x-java-archive",
    "ear": "application-x-java-archive",
    "whl": "application-x-archive",
    "egg": "application-x-archive",
    "crate": "application-x-archive",
    "gem": "application-x-archive",
    "ipa": "application-x-archive",
    "crx": "application-x-archive",
    "snap": "package-x-generic",
    "alpm": "application-x-archive",
    "xbps": "application-x-archive",
    # fonts
    "otf": "font-otf",
    "otc": "font-collection",
    "eot": "font-x-generic",
    # config / data
    "conf": "text-x-generic",
    "ini": "text-x-generic",
    "cfg": "text-x-generic",
    "cnf": "text-x-generic",
    "rc": "text-x-generic",
    "env": "text-x-generic",
    "properties": "text-x-generic",
    "lock": "text-x-generic",
    "swp": "text-x-generic",
    "swo": "text-x-generic",
    "tmp": "text-x-generic",
    "sqlite": "application-vnd.sqlite3",
    "sqlite3": "application-vnd.sqlite3",
    "db": "application-vnd.sqlite3",
    "db3": "application-vnd.sqlite3",
    # 3D models
    "fbx": "model-stl",
    "obj": "model-stl",
    "3mf": "model-stl",
    "step": "model-stl",
    "stp": "model-stl",
    "iges": "model-stl",
    "igs": "model-stl",
    "glb": "model-stl",
    "gltf": "model-stl",
    # certificates / keys
    "pem": "application-x-pem-file",
    "key": "application-x-pem-key",
    "crt": "application-pkix-cert",
    "cer": "application-pkix-cert",
    "der": "application-pkix-cert",
    "p12": "application-x-pkcs12",
    "pfx": "application-x-pkcs12",
    "pub": "application-pgp-keys",
    "asc": "application-pgp-signature",
    # binaries
    "so": "application-x-sharedlib",
    "dylib": "application-x-sharedlib",
    "dll": "application-x-sharedlib",
    "o": "application-x-object",
    "ko": "application-x-object",
    "run": "application-x-executable",
    "bin": "application-x-executable",
    # virtual machines
    "ovf": "application-x-virtualbox-ova",
}

NAME_ICONS = {
    "makefile": "text-x-makefile",
    "gnumakefile": "text-x-makefile",
    "cmakelists.txt": "text-x-cmake",
    "meson.build": "text-x-meson",
    "meson_options.txt": "text-x-meson",
    "readme": "text-x-readme",
    "readme.md": "text-x-readme",
    "readme.txt": "text-x-readme",
    "readme.rst": "text-x-readme",
    "license": "text-x-copying",
    "licence": "text-x-copying",
    "copying": "text-x-copying",
    "copyright": "text-x-copying",
    "notice": "text-x-copying",
    "changelog": "text-x-changelog",
    "changes": "text-x-changelog",
    "history": "text-x-changelog",
    "news": "text-x-changelog",
    "install": "text-x-install",
    "install.md": "text-x-install",
    "install.txt": "text-x-install",
    "pkgbuild": "text-x-rpm-spec",
    "dockerfile": "text-x-generic",
    "containerfile": "text-x-generic",
    ".bashrc": "text-x-shellscript",
    ".bash_profile": "text-x-shellscript",
    ".bash_login": "text-x-shellscript",
    ".zshrc": "text-x-shellscript",
    ".zprofile": "text-x-shellscript",
    ".zshenv": "text-x-shellscript",
    ".zlogin": "text-x-shellscript",
    ".xinitrc": "text-x-script",
    ".xsession": "text-x-script",
}

DIR_NAME_ICONS = {
    ".git": "folder-git",
    ".github": "folder-github",
    ".gitlab": "folder-gitlab",
    ".docker": "folder-docker",
    "docker": "folder-docker",
    "node_modules": "folder-code",
    ".venv": "folder-code",
    "venv": "folder-code",
    "projects": "folder-projects",
    "development": "folder-development",
    "code": "folder-code",
    "desktop": "folder-desktop",
    "documents": "folder-documents",
    "download": "folder-download",
    "downloads": "folder-download",
    "music": "folder-music",
    "pictures": "folder-pictures",
    "videos": "folder-videos",
    "templates": "folder-templates",
    "public": "folder-publicshare",
    "publicshare": "folder-publicshare",
    "dropbox": "folder-dropbox",
    "google drive": "folder-google-drive",
    "googledrive": "folder-google-drive",
    "onedrive": "folder-onedrive",
    "nextcloud": "folder-nextcloud",
    "owncloud": "folder-owncloud",
    "mega": "folder-mega",
    "pcloud": "folder-pcloud",
    "syncthing": "folder-syncthing",
    "sync": "folder-syncthing",
    "steam": "folder-steam",
    "snap": "folder-snap",
    "torrents": "folder-torrent",
    "torrent": "folder-torrent",
    "virtualbox vms": "folder-vbox",
    ".virtualbox": "folder-vbox",
    "vmware": "folder-vmware",
    ".wine": "folder-wine",
    "wine": "folder-wine",
    ".android": "folder-android",
    "games": "folder-games",
    "books": "folder-books",
    "ebooks": "folder-books",
    "notes": "folder-notes",
}

SNIFF_EXTENSIONS = {"ts", "key"}
SNIFF_LIMIT = 512


@lru_cache(maxsize=4096)
def _has_icon(name: str) -> bool:
    if not name:
        return False
    if _THEME is None:
        return True
    try:
        return bool(_THEME.has_icon(name))
    except Exception:
        return False


def _resolve(candidates) -> str | None:
    for name in candidates:
        if _has_icon(name):
            return name
    return None


@lru_cache(maxsize=2048)
def _icons_for_mime(mime: str):
    if Gio is None:
        return ()
    try:
        icon = Gio.content_type_get_icon(mime)
        names = icon.get_names() if hasattr(icon, "get_names") else []
    except Exception:
        return ()
    return tuple(names)


@lru_cache(maxsize=2048)
def _icon_for_mime(mime: str) -> str:
    resolved = _resolve(_icons_for_mime(mime))
    if resolved:
        return resolved
    generic = MAJOR_FALLBACK.get((mime or "").split("/")[0])
    if generic and _has_icon(generic):
        return generic
    return FILE_FALLBACK


def _guess_mime(name: str, path: str | None, executable: bool) -> str:
    if Gio is not None:
        try:
            mime = Gio.content_type_guess(name, None)[0] or ""
        except Exception:
            mime = ""
    else:
        mime = mimetypes.guess_type(name)[0] or ""
    if mime and mime != "application/octet-stream":
        return mime
    if path:
        data = _read_head(path)
        if data:
            try:
                mime = Gio.content_type_guess(name, data)[0] or mime
            except Exception:
                pass
    if mime in ("", "application/octet-stream") and executable:
        return "application/x-executable"
    return mime or "application/octet-stream"


def _read_head(path: str) -> bytes:
    try:
        with open(path, "rb") as handle:
            return handle.read(SNIFF_LIMIT)
    except OSError:
        return b""


def _sniff_icon(ext: str, path: str | None) -> str | None:
    if not path or ext not in SNIFF_EXTENSIONS:
        return None
    head = _read_head(path)
    if not head:
        return None
    if ext == "ts":
        upper = head.upper()
        if b"<!DOCTYPE TS" in upper or b"<TS " in upper:
            return _resolve(("text-vnd.trolltech.linguist",)) or FILE_FALLBACK
        return _resolve((EXT_ICONS["ts"],)) or FILE_FALLBACK
    if ext == "key" and b"-----BEGIN" in head:
        return _resolve((EXT_ICONS["key"],)) or FILE_FALLBACK
    return None


@lru_cache(maxsize=1)
def _special_dirs() -> dict[str, str]:
    if GLib is None:
        return {}
    mapping = {
        GLib.UserDirectory.DIRECTORY_DESKTOP: "folder-desktop",
        GLib.UserDirectory.DIRECTORY_DOCUMENTS: "folder-documents",
        GLib.UserDirectory.DIRECTORY_DOWNLOAD: "folder-download",
        GLib.UserDirectory.DIRECTORY_MUSIC: "folder-music",
        GLib.UserDirectory.DIRECTORY_PICTURES: "folder-pictures",
        GLib.UserDirectory.DIRECTORY_VIDEOS: "folder-videos",
        GLib.UserDirectory.DIRECTORY_PUBLIC_SHARE: "folder-publicshare",
        GLib.UserDirectory.DIRECTORY_TEMPLATES: "folder-templates",
    }
    found = {}
    for kind, icon in mapping.items():
        directory = GLib.get_user_special_dir(kind)
        if directory:
            found[os.path.normpath(directory)] = icon
    return found


def _dir_icon(name: str, path: str | None) -> str:
    if path:
        icon = _special_dirs().get(os.path.normpath(path))
        if icon:
            return _resolve((icon,)) or DIR_FALLBACK
    icon = DIR_NAME_ICONS.get(name.lower())
    if icon:
        return _resolve((icon,)) or DIR_FALLBACK
    return _resolve((DIR_FALLBACK,)) or DIR_FALLBACK


def _extension(name: str) -> str:
    base = Path(name).name
    if base.startswith(".") and base.count(".") == 1:
        return ""
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[1].lower()


@lru_cache(maxsize=512)
def _preview_kind_for_extension(ext: str) -> str:
    if not ext:
        return ""
    if Gio is not None:
        try:
            mime = Gio.content_type_guess("file." + ext, None)[0] or ""
        except Exception:
            mime = ""
    else:
        mime = mimetypes.guess_type("file." + ext)[0] or ""
    major = mime.split("/")[0]
    if major == "image":
        return "image"
    if major == "video":
        return "video"
    if mime == "application/pdf":
        return "pdf"
    return ""


def preview_kind(name: str) -> str:
    return _preview_kind_for_extension(_extension(name))


def icon_for(
    name: str,
    is_dir: bool,
    is_link: bool,
    path: str | None = None,
    executable: bool = False,
) -> str:
    if is_dir:
        return _dir_icon(name, path)
    if is_link:
        return _resolve(("inode-symlink",)) or LINK_FALLBACK
    exact = NAME_ICONS.get(name.lower())
    if exact:
        return _resolve((exact,)) or FILE_FALLBACK
    ext = _extension(name)
    sniffed = _sniff_icon(ext, path)
    if sniffed:
        return sniffed
    override = EXT_ICONS.get(ext)
    if override:
        resolved = _resolve((override,))
        if resolved:
            return resolved
    return _icon_for_mime(_guess_mime(name, path, executable))
