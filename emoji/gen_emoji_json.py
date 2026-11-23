#!/usr/bin/env python3
# SPDX-FileCopyrightText: crDroid Android Project
# SPDX-License-Identifier: Apache-2.0
"""
Builds emoji/emoji.json for the Settings emoji picker.

Run from the repo root:  python3 emoji/gen_emoji_json.py
Every .ttf/.otf in emoji/ becomes an entry. The label is the file name with underscores as
spaces ("Apple_iOS_26.ttf" -> "Apple iOS 26"). A PNG or JPG with the same base name is used
as the preview image. Names already in emoji.json are kept, so labels can be edited by hand.
"""
import hashlib
import json
import os
import re
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(DIR, "emoji.json")
MAX_BYTES = 128 * 1024 * 1024
SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    names = {}
    if os.path.isfile(INDEX):
        with open(INDEX) as f:
            names = {e["file"]: e.get("name") for e in json.load(f).get("emoji", [])}

    entries = []
    for file in sorted(os.listdir(DIR)):
        base, ext = os.path.splitext(file)
        if ext.lower() not in (".ttf", ".otf"):
            continue
        path = os.path.join(DIR, file)
        size = os.path.getsize(path)
        if not SAFE.match(file) or file.startswith("."):
            sys.exit(f"{file}: use only letters, digits, '.', '_' and '-' in the name")
        if size > MAX_BYTES:
            sys.exit(f"{file}: {size} bytes is over the 128 MiB limit")
        with open(path, "rb") as f:
            if f.read(7) == b"version":
                sys.exit(f"{file}: is a Git LFS pointer; raw.githubusercontent.com won't serve it")
        preview = next((base + e for e in (".png", ".jpg", ".jpeg")
                        if os.path.isfile(os.path.join(DIR, base + e))), None)
        entry = {
            "id": base.lower(),
            "name": names.get(file) or base.replace("_", " "),
            "file": file,
            "size": size,
            "sha256": sha256(path),
        }
        if preview:
            entry["preview"] = preview
        entries.append(entry)

    with open(INDEX, "w") as f:
        json.dump({"version": 1, "emoji": entries}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(entries)} entries to {INDEX}")


if __name__ == "__main__":
    main()
