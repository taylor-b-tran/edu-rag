"""The Sign Up form puts one field on each line, like Sign In.

Password and Confirm Password used to sit side by side in two narrow columns.
At that width Streamlit's "Press Enter to submit form" hint printed over the
Password field's eye icon, and the form looked different from Sign In, which
has one full-width field per line.

Source-level guard in the style of test_member_row_layout.py.
"""
from __future__ import annotations

import ast
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "apps" / "streamlit" / "main.py"
SRC = MAIN.read_text(encoding="utf-8")
TREE = ast.parse(SRC)


def _signup_form_body():
    for node in ast.walk(TREE):
        if isinstance(node, ast.With):
            for item in node.items:
                call = item.context_expr
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "form" and call.args
                        and isinstance(call.args[0], ast.Constant)
                        and call.args[0].value == "signup_form"):
                    return node
    raise AssertionError("signup_form not found in main.py")


def test_signup_form_has_no_column_layout():
    form = _signup_form_body()
    columns = [
        n.lineno for n in ast.walk(form)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "columns"
    ]
    assert not columns, f"the sign-up form lays fields out in columns (line {columns})"


def test_signup_fields_and_their_order_are_unchanged():
    # Guards against "fixing" the layout by dropping or reordering a field.
    form = ast.get_source_segment(SRC, _signup_form_body())
    keys = ["signup_email", "signup_username", "signup_password", "signup_confirm", "signup_role"]
    positions = [form.index(f'key="{k}"') for k in keys]
    assert positions == sorted(positions)
    assert 'type="password"' in form and form.count('type="password"') == 2
