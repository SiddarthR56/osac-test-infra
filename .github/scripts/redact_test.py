#!/usr/bin/env python3
"""Regression tests for redact.py (run: python3 .github/scripts/redact_test.py)."""
from __future__ import annotations

import base64
import json
import pathlib
import sys
import tempfile

# Import sibling module without requiring package install.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import redact  # noqa: E402


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_apply_ranges_single_pass() -> None:
    data = b"aaaSECRETbbbSECRETccc"
    ranges = [(3, 9), (12, 18)]
    out = redact.apply_ranges(data, ranges)
    _assert(out == b"aaa[REDACTED]bbb[REDACTED]ccc", f"unexpected: {out!r}")


def test_short_quoted_b64_when_path_unresolved() -> None:
    """16-39-char quoted b64 must wipe even when File path does not resolve."""
    # 24-byte secret -> 32-char std base64 (between 16 and 39).
    secret = b"ABCDEFGHIJKLMNOPQRSTUVWX"
    encoded = base64.b64encode(secret)
    _assert(16 <= len(encoded) <= 39, f"fixture length {len(encoded)} not in 16-39")

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        target = root / "app.log"
        # Secret only inside quoted base64; no cleartext copy.
        target.write_bytes(b'payload="' + encoded + b'"\n')

        findings = [
            {
                "Secret": secret.decode("ascii"),
                # Unresolvable path: no column wipe; encoded-field path only.
                "File": "/scan/missing/does-not-exist.log",
                "StartLine": 1,
                "EndLine": 1,
                "StartColumn": 1,
                "EndColumn": 10,
            }
        ]
        findings_path = root / "findings.json"
        findings_path.write_text(json.dumps(findings))

        redact.redact_tree(findings, root)
        published = target.read_bytes()
        _assert(encoded not in published, f"encoded blob still present: {published!r}")
        _assert(secret not in published, f"secret still present: {published!r}")
        _assert(b"[REDACTED]" in published, f"marker missing: {published!r}")


def test_unquoted_token_b64_when_path_unresolved() -> None:
    """Unquoted token=<b64> must wipe when File path does not resolve."""
    secret = b"ABCDEFGHIJKLMNOPQRSTUVWX"
    encoded = base64.b64encode(secret)
    _assert(16 <= len(encoded) <= 39, f"fixture length {len(encoded)} not in 16-39")

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        target = root / "app.log"
        # Unquoted assignment; no cleartext secret copy.
        target.write_bytes(b"token=" + encoded + b"\n")

        findings = [
            {
                "Secret": secret.decode("ascii"),
                "File": "/scan/missing/does-not-exist.log",
                "StartLine": 1,
                "EndLine": 1,
                "StartColumn": 1,
                "EndColumn": 10,
            }
        ]
        (root / "findings.json").write_text(json.dumps(findings))

        redact.redact_tree(findings, root)
        published = target.read_bytes()
        _assert(encoded not in published, f"encoded blob still present: {published!r}")
        _assert(secret not in published, f"secret still present: {published!r}")
        _assert(b"[REDACTED]" in published, f"marker missing: {published!r}")
        _assert(
            published.startswith(b"token=[REDACTED]"),
            f"assignment prefix lost: {published!r}",
        )


def test_resolve_path_rejects_traversal() -> None:
    """File fields with .. or symlink escape must not resolve outside root."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / "redacted"
        root.mkdir()
        (root / "ok.log").write_text("inside\n")
        outside = pathlib.Path(tmp) / "outside.log"
        outside.write_text("SECRET\n")
        # Symlink under redacted_dir pointing outside.
        link = root / "escape.log"
        link.symlink_to(outside)

        _assert(
            redact.resolve_path(root, "/scan/../outside.log") is None,
            "expected .. traversal to be rejected",
        )
        _assert(
            redact.resolve_path(root, "/scan/escape.log") is None,
            "expected symlink escape to be rejected",
        )
        _assert(
            redact.resolve_path(root, "/scan/ok.log") == root / "ok.log",
            "expected in-tree path to resolve",
        )


def main() -> None:
    test_apply_ranges_single_pass()
    test_short_quoted_b64_when_path_unresolved()
    test_unquoted_token_b64_when_path_unresolved()
    test_resolve_path_rejects_traversal()
    print("redact_test.py: ok")



if __name__ == "__main__":
    main()
