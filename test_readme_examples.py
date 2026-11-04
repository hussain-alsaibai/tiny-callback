"""Every python block in the README must at least parse.

Added 2026-11-04. The README shipped three examples that could not run:

- ``.finally(cleanup)`` -- ``finally`` is a reserved keyword in Python, so
  the method is ``finally_fn``. The README's own copy said so in the
  docstring and contradicted itself in its examples.
- ``lambda (users, products, orders): ...`` -- Python has no tuple lambda
  parameters.

A doc example that cannot be parsed is a doc example that is wrong.
"""
import io
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

README = pathlib.Path(__file__).resolve().parent / "README.md"
BLOCK = re.compile(r"```python\n(.*?)```", re.S)


def _blocks():
    text = io.open(README, encoding="utf-8").read()
    return BLOCK.findall(text)


def test_readme_has_python_examples():
    assert _blocks(), "the README should carry at least one python example"


@pytest.mark.parametrize("block", _blocks())
def test_readme_example_parses(block):
    """Each block must compile. A block that cannot parse cannot be copy-pasted."""
    try:
        compile(block, "README.md", "exec")
    except SyntaxError as exc:
        pytest.fail(f"README example does not parse: {exc.msg} (line {exc.lineno})")


def test_finally_is_documented_with_its_real_name():
    """The README must not tell readers to call a method that cannot exist."""
    import tiny_callback

    assert hasattr(tiny_callback.Callback, "finally_fn"), "finally_fn should exist"
    assert not hasattr(tiny_callback.Callback, "finally"), (
        "'finally' is a reserved keyword and cannot be a method name; "
        "the README must not reference .finally()"
    )
    text = io.open(README, encoding="utf-8").read()
    assert ".finally(" not in text, "README still references the impossible .finally()"
