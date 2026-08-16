"""Alpha 0.6.7 HF-02, Part 19: no raw enums or technical keys in the UI.
Scans every static `t("...")` call across the codebase and confirms each
key resolves in both `es.json` and `en.json`. Dynamically-built keys
(string concatenation/f-strings) aren't statically discoverable this way
and are excluded by construction -- their own call sites should be checked
individually when touched.
"""
import glob
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_catalog(lang):
    path = REPO_ROOT / "resources" / "i18n" / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lookup(catalog, key):
    value = catalog
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return True


def _scan_static_t_calls():
    files = glob.glob(str(REPO_ROOT / "ht_coach_app" / "**" / "*.py"), recursive=True)
    files += glob.glob(str(REPO_ROOT / "engine" / "**" / "*.py"), recursive=True)
    calls = []
    for file_path in files:
        if "__pycache__" in file_path:
            continue
        text = Path(file_path).read_text(encoding="utf-8")
        if "localization import" not in text and "localization.t(" not in text:
            continue
        for match in re.finditer(
            r'(?<![a-zA-Z0-9_.])t\(\s*["\']([a-zA-Z0-9_.]+)["\']', text
        ):
            key = match.group(1)
            if key.endswith("."):
                # A dynamically-built key via string concatenation,
                # e.g. t("prefix." + variable) -- the regex only sees
                # the static prefix, which is not a real lookup key by
                # itself. Verify these individually at their call site
                # instead of here.
                continue
            calls.append((file_path, key))
    return calls


def test_every_static_localization_key_resolves_in_both_languages():
    es = _load_catalog("es")
    en = _load_catalog("en")
    calls = _scan_static_t_calls()
    assert len(calls) > 500

    missing = [
        (file_path, key, lang)
        for file_path, key in calls
        for lang, catalog in (("es", es), ("en", en))
        if not _lookup(catalog, key)
    ]
    assert missing == []


def test_es_and_en_catalogs_have_identical_key_sets():
    def flatten(d, prefix=""):
        keys = set()
        for k, v in d.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys |= flatten(v, full)
            else:
                keys.add(full)
        return keys

    es_keys = flatten(_load_catalog("es"))
    en_keys = flatten(_load_catalog("en"))
    assert es_keys == en_keys


def test_no_snake_case_or_screaming_case_values_in_catalogs():
    def flatten_values(d):
        values = []
        for v in d.values():
            if isinstance(v, dict):
                values.extend(flatten_values(v))
            elif isinstance(v, str):
                values.append(v)
        return values

    for lang in ("es", "en"):
        catalog = _load_catalog(lang)
        for value in flatten_values(catalog):
            if re.fullmatch(r"[a-z_]+", value) and "_" in value:
                assert False, f"[{lang}] suspicious snake_case value: {value!r}"
            if re.fullmatch(r"[A-Z_]+", value) and "_" in value:
                assert False, f"[{lang}] suspicious SCREAMING_CASE value: {value!r}"
