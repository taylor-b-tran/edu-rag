"""The member list on the Admin Dashboard must leave room for its button.

Each member row is a Streamlit column layout whose last column holds the
"Remove" button. With the shares [3, 3, 2, 1] that column took 11% of the row,
so the word broke into "Remov / e" (one letter per line when the window was
narrow). The same defect had been fixed in the document table
(`_document_table_ratio`) and was missed here.

Source-level guard: every column layout in render_course_management whose
shares are given as a list must give its last column at least 20% of the row.
At a 900 px window the row has about 430 px and the button needs about 90 of
them. The ratio may be a literal list or a module-level constant. The "Enrol"
button in the add-member row broke the same way and is held to the same rule.
"""
from __future__ import annotations

import ast
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "apps" / "streamlit" / "main.py"
MIN_LAST_SHARE = 0.20

TREE = ast.parse(MAIN.read_text(encoding="utf-8"))


def _module_constants():
    consts = {}
    for node in TREE.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                consts[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                pass
    return consts


def _function(name):
    for node in ast.walk(TREE):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in main.py")


def _column_ratios(func):
    consts = _module_constants()
    ratios = []
    for node in ast.walk(func):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "columns" and node.args):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Name):
            value = consts.get(arg.id)
        else:
            try:
                value = ast.literal_eval(arg)
            except ValueError:
                value = None
        if isinstance(value, list) and value:
            ratios.append((node.lineno, value))
    return ratios


def test_every_column_layout_in_the_course_manager_leaves_room_for_its_last_column():
    ratios = _column_ratios(_function("render_course_management"))
    assert ratios, "expected the member list to declare its column shares"
    narrow = [(line, r) for line, r in ratios if r[-1] / sum(r) < MIN_LAST_SHARE]
    assert not narrow, f"last column under {MIN_LAST_SHARE:.0%} of the row: {narrow}"


def test_the_remove_button_keeps_its_key_and_fills_its_column():
    src = MAIN.read_text(encoding="utf-8")
    assert 'key=f"rm_{code}_{m.get(\'email\')}"' in src
    func = _function("render_course_management")
    for node in ast.walk(func):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "button" and node.args
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == "Remove"):
            kw = {k.arg: k.value for k in node.keywords}
            assert isinstance(kw.get("use_container_width"), ast.Constant) and kw["use_container_width"].value is True
            return
    raise AssertionError("Remove button not found")
