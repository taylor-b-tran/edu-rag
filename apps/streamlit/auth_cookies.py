"""First-party session-cookie transport without a legacy component iframe."""
import streamlit as st


_WRITE_JS = """
export default function(component) {
  const { data, parentElement, setStateValue } = component;
  const marker = parentElement.querySelector('span');
  if (!data || !data.id || marker.dataset.operation === data.id) return;
  marker.dataset.operation = data.id;
  const name = 'paedia_session';
  const value = data.value === null ? '' : encodeURIComponent(data.value);
  const expiry = data.value === null ? new Date(0) : new Date(data.expires);
  const secure = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = name + '=' + value + '; Path=/; SameSite=Strict; Expires=' + expiry.toUTCString() + secure;
  const saved = document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith(name + '='));
  const ok = data.value === null ? !saved : saved === name + '=' + value;
  setStateValue('result', { id: data.id, ok });
}
"""


@st.cache_resource
def _cookie_writer():
    return st.components.v2.component(
        "paedia_session_cookie", html="<span></span>", js=_WRITE_JS)


def _cookie_changed():
    """A component acknowledgement requests one normal Streamlit rerun."""


class AuthCookies:
    def __init__(self, st_api):
        self.st = st_api

    def get(self, name):
        # Initial-request cookies do not change during a Streamlit session.
        # An explicit local override prevents restoring that stale snapshot
        # after logout or a rejected credential, until the next full reload.
        if "_auth_cookie_override" in self.st.session_state:
            return self.st.session_state["_auth_cookie_override"]
        return self.st.context.cookies.get(name)

    def set(self, name, value, *, expires, same_site):
        self._write(value, expires.isoformat())

    def remove(self, name):
        self._write(None, None)

    def _write(self, value, expires):
        revision = self.st.session_state["_auth_cookie_revision"]
        response = _cookie_writer()(
            data={"id": revision, "value": value, "expires": expires},
            key="paedia_session_cookie_writer", height=0,
            default={"result": None}, on_result_change=_cookie_changed)
        result = response.result
        if isinstance(result, dict) and result.get("id") == revision:
            self.st.session_state.pop("_auth_cookie_write", None)
            self.st.session_state["_auth_cookie_write_failed"] = not result.get("ok", False)
