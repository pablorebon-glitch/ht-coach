from __future__ import annotations

import json
import os
from pathlib import Path


def write_text_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp_path, path)


def write_json_atomic(path, data, **dump_kwargs):
    defaults = {
        "indent": 2,
        "ensure_ascii": False,
    }
    defaults.update(dump_kwargs)
    write_text_atomic(path, json.dumps(data, **defaults))

