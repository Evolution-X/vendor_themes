#!/usr/bin/env python3
# SPDX-FileCopyrightText: Evolution X Project
# SPDX-License-Identifier: Apache-2.0
"""
Builds bootanimation/bootanimation.json for the Settings boot animation picker.

Run from the repo root:  python3 bootanimation/gen_bootanimation_json.py
Every bootanimation_<id>.zip in bootanimation/ becomes an entry, so <id> must be lower case
letters, digits and '_' (it is the persist.sys.bootanim.name of the style). The label is taken
from bootanimation.json when the entry already exists, so labels can be edited by hand, and
otherwise from the id. A <id>.png next to the zip is the preview; when it is missing it is made
from a frame of the zip (needs Pillow). Zips must be STORED (no compression), as bootanimation
requires, and must stay under the 100 MB limit of a GitHub file.
"""
import hashlib
import io
import json
import os
import re
import sys
import zipfile

DIR = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(DIR, "bootanimation.json")
MAX_BYTES = 100 * 1024 * 1024
PREVIEW_PX = 320
ID = re.compile(r"^[a-z0-9_]+$")
FRAME = re.compile(r"\.(png|jpg|jpeg)$", re.I)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_preview(zip_path, out_path):
    """Saves the middle frame of the part with the most frames, scaled down."""
    try:
        from PIL import Image
    except ImportError:
        print(f"  Pillow is missing, no preview for {os.path.basename(zip_path)}")
        return False
    with zipfile.ZipFile(zip_path) as z:
        parts = {}
        for name in z.namelist():
            if FRAME.search(name) and "/" in name:
                parts.setdefault(name.split("/")[0], []).append(name)
        if not parts:
            return False
        frames = sorted(max(parts.values(), key=len))
        data = z.read(frames[len(frames) // 2])
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    img.thumbnail((PREVIEW_PX, PREVIEW_PX))
    img.save(out_path, optimize=True)
    return True


def main():
    names = {}
    if os.path.isfile(INDEX):
        with open(INDEX) as f:
            names = {e["id"]: e.get("name") for e in json.load(f).get("bootanimations", [])}

    entries = []
    for file in sorted(os.listdir(DIR)):
        m = re.match(r"^bootanimation_(.+)\.zip$", file)
        if not m:
            continue
        id_ = m.group(1)
        path = os.path.join(DIR, file)
        size = os.path.getsize(path)
        if not ID.match(id_) or id_ in ("default", "custom"):
            sys.exit(f"{file}: the id must be lower case letters, digits and '_', "
                     "and not 'default' or 'custom'")
        if size > MAX_BYTES:
            sys.exit(f"{file}: {size} bytes is over the 100 MiB limit")
        with open(path, "rb") as f:
            if f.read(7) == b"version":
                sys.exit(f"{file}: is a Git LFS pointer; raw.githubusercontent.com won't serve it")
        with zipfile.ZipFile(path) as z:
            if "desc.txt" not in z.namelist():
                sys.exit(f"{file}: has no desc.txt")
            if any(i.compress_type != zipfile.ZIP_STORED for i in z.infolist()):
                sys.exit(f"{file}: must be STORED, bootanimation can't read compressed zips")
        preview = id_ + ".png"
        if not os.path.isfile(os.path.join(DIR, preview)):
            if not make_preview(path, os.path.join(DIR, preview)):
                preview = None
        entry = {
            "id": id_,
            "name": names.get(id_) or id_.replace("_", " ").title(),
            "file": file,
            "size": size,
            "sha256": sha256(path),
        }
        if preview:
            entry["preview"] = preview
        entries.append(entry)

    with open(INDEX, "w") as f:
        json.dump({"version": 1, "bootanimations": entries}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(entries)} entries to {INDEX}")


main()
