"""The README must document an API that actually exists.

The second example in the published README began

    from tiny_callback import Callback, sleep

`tiny_callback` exports `Callback`, `EventEmitter`, `deferred`, `emit`,
`on`, `once` -- there is no `sleep`, and the example never used it. It was
a copy-paste leftover, and because no test ever executed the README, every
reader who ran that block got an ImportError on the import line.
"""

from __future__ import annotations

import importlib
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(HERE, "README.md")
BLOCK = re.compile(r"```python\n(.*?)```", re.S)
IMPORT_LINE = re.compile(r"^from\s+([\w.]+)\s+import\s+(.+)$", re.M)


def _blocks():
    if not os.path.exists(README):
        pytest.skip("no README.md")
    with open(README, encoding="utf-8") as fh:
        return BLOCK.findall(fh.read())


def _compiles(block):
    try:
        compile(block, "<readme>", "exec")
        return True
    except SyntaxError:
        pass
    indented = "".join(
        "    " + line if line.strip() else line for line in block.splitlines(True)
    )
    try:
        compile("async def _probe():\n" + indented, "<readme>", "exec")
        return True
    except SyntaxError:
        return False


def _import_lines():
    for i, block in enumerate(_blocks()):
        for match in IMPORT_LINE.finditer(block):
            names = []
            for raw in match.group(2).split(","):
                name = raw.strip().split(" as ")[0].strip()
                if name and name.isidentifier():
                    names.append(name)
            if names:
                yield i, match.group(1), names


def test_readme_python_blocks_compile():
    for i, block in enumerate(_blocks()):
        assert _compiles(block), "README block %d does not compile" % i


def test_every_readme_import_resolves():
    sys.path.insert(0, HERE)
    problems = []
    for block, module, names in _import_lines():
        try:
            mod = importlib.import_module(module)
        except Exception as exc:
            problems.append("block %d: cannot import %s (%s)" % (block, module, exc))
            continue
        missing = [n for n in names if not hasattr(mod, n)]
        if missing:
            problems.append("block %d: %s has no %s" % (block, module, ", ".join(missing)))
    assert not problems, "README documents a non-existent API:\n  " + "\n  ".join(problems)


def test_readme_does_not_import_sleep():
    """Regression: `sleep` was never part of this API."""
    offenders = [
        b for b, module, names in _import_lines()
        if module == "tiny_callback" and "sleep" in names
    ]
    assert not offenders, (
        "README imports `sleep` from tiny_callback, which does not export it. "
        "The export list is: Callback, EventEmitter, deferred, emit, on, once. "
        "Offending block(s): %s" % offenders
    )
