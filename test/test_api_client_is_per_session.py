"""The API client, and the JWT on it, must not be shared between browsers.

`get_api_client()` was
decorated with `@st.cache_resource`, which by design returns one object to
every session the Streamlit server is running -- and `PaediaAPIClient` keeps
the signed-in user's token on the instance. One cached client therefore meant
one token for everybody: the most recent login owned every other tab's
requests, and one person signing out revoked them all.

Nothing on screen looks wrong when this happens. Each browser still shows its
own name in the sidebar, because `st.session_state.user` really is
per-session; only the credential actually sent to the API is shared. The bug
is invisible to any test, manual or automated, that drives one session at a
time -- which is every test this suite had, and why it went unnoticed.

So these tests drive two. Streamlit gives each browser session its own
`st.session_state` mapping and reruns the script against it; swapping that
mapping is what "another browser" means here, and it is the smallest thing
that reproduces the fault. Restoring `@st.cache_resource`, or rebinding `api`
to a single client at import, turns them red.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_STREAMLIT_DIR = Path(__file__).resolve().parents[1] / "apps" / "streamlit"
sys.path.insert(0, str(_STREAMLIT_DIR))


class _RecordingRequests:
    """Stands in for `requests` so no test here touches the network.

    clear_auth() posts to /api/auth/logout, which is the behaviour the
    sign-out test is about; the calls are recorded so it can assert *whose*
    token was revoked.
    """

    def __init__(self):
        self.posts: list[tuple[str, dict]] = []

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        self.posts.append((url, headers or {}))

        class _Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"status": "ok"}

        return _Resp()


@pytest.fixture(scope="module")
def main():
    """main.py imports outside a Streamlit runtime; it only warns."""
    import main as main_module
    return main_module


@pytest.fixture
def browser(main, monkeypatch):
    """Hands out independent `st.session_state` mappings.

    Each one stands for a separate browser session against the same server
    process. `switch()` is the moment control passes from one session's
    script run to the other's.
    """
    sessions: dict[str, dict] = {}

    def switch(name: str) -> dict:
        state = sessions.setdefault(name, {})
        monkeypatch.setattr(main.st, "session_state", state)
        return state

    return switch


@pytest.fixture
def no_network(main, monkeypatch):
    import api_client

    recorder = _RecordingRequests()
    monkeypatch.setattr(api_client, "requests", recorder)
    # _check_api() short-circuits on the cached flag, so nothing reaches the
    # recorder's missing .get either.
    return recorder


def _client_for(main, browser, name, token=None):
    browser(name)
    client = main.get_api_client()
    client._api_available = True  # skip the health probe; no network in tests
    if token is not None:
        client._jwt_token = token
    return client


# --- the fault itself --------------------------------------------------

def test_two_browsers_do_not_share_a_client(main, browser):
    a = _client_for(main, browser, "alice")
    b = _client_for(main, browser, "bob")
    assert a is not b


def test_a_token_set_in_one_browser_is_not_visible_in_the_other(main, browser):
    """The exact failure, in one assertion.

    Alice signs in, then Bob's browser loads the app. Before the fix Bob's
    client *was* Alice's client, so this read her token -- and every request
    Bob's tab made from then on was made as Alice.
    """
    _client_for(main, browser, "alice", token="alice-token")

    bob = _client_for(main, browser, "bob")
    assert bob._jwt_token is None


def test_the_second_login_does_not_take_over_the_first_browser(main, browser):
    """The same fault from the other side, which is the damaging direction.

    Alice is already signed in and working. Bob signs in afterwards. Alice's
    session must still be Alice's -- previously the later login overwrote the
    single shared token and Alice's next question went to the API as Bob.
    """
    alice = _client_for(main, browser, "alice", token="alice-token")
    _client_for(main, browser, "bob", token="bob-token")

    browser("alice")
    assert main.get_api_client() is alice
    assert alice._jwt_token == "alice-token"


def test_signing_out_of_one_browser_leaves_the_other_signed_in(main, browser, no_network):
    """Sign-out revokes a token server-side (see PaediaAPIClient.clear_auth).

    With one shared client that revocation applied to whichever token the
    object happened to be holding, so Bob signing out could log Alice out of
    a session he had no connection to.
    """
    alice = _client_for(main, browser, "alice", token="alice-token")
    bob = _client_for(main, browser, "bob", token="bob-token")

    browser("bob")
    bob.clear_auth()

    assert bob._jwt_token is None
    assert alice._jwt_token == "alice-token"

    revoked = [headers.get("Authorization") for _, headers in no_network.posts]
    assert revoked == ["Bearer bob-token"], "sign-out revoked the wrong token"


# --- the shape of the fix, so it is not undone by accident -------------

def test_one_browser_keeps_the_same_client_across_reruns(main, browser):
    """Per-session, not per-run.

    Streamlit reruns the whole script on every interaction. A client rebuilt
    each time would drop the token on the first click after signing in, and
    re-probe /api/health on every keystroke.
    """
    first = _client_for(main, browser, "alice", token="alice-token")
    browser("alice")
    assert main.get_api_client() is first
    assert main.get_api_client()._jwt_token == "alice-token"


def test_get_api_client_is_not_a_cached_resource(main):
    """`@st.cache_resource` is what caused this; refuse it explicitly.

    Streamlit's cache decorators expose a `.clear()` on the wrapped function,
    which a plain function does not have. Asserting on the absence is a
    structural guard: it fails the moment the decorator comes back, without
    waiting for a two-browser test to notice the consequence.
    """
    assert not hasattr(main.get_api_client, "clear"), (
        "get_api_client is cached again -- st.cache_resource is shared by "
        "every browser session, and the client holds a JWT"
    )


def test_the_module_level_api_name_resolves_per_session(main, browser):
    """`api` must stay a lookup, not a client captured at import.

    Module globals are shared by every ScriptRunner thread, so
    `api = get_api_client()` at import would hand all sessions one object
    again -- and with concurrent reruns, hand a session whichever object was
    bound last. Callers use `api.<x>` in ~36 places; keeping the indirection
    there is what makes those call sites safe.
    """
    from api_client import PaediaAPIClient

    assert not isinstance(main.api, PaediaAPIClient)

    _client_for(main, browser, "alice", token="alice-token")
    browser("bob")
    main.get_api_client()._api_available = True

    assert main.api._jwt_token is None, "api resolved to another session's client"

    browser("alice")
    assert main.api._jwt_token == "alice-token"
