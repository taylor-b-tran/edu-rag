import sys, os

sys.path.insert(0, os.path.abspath("."))

# The test suite runs without Postgres, so the demo accounts in
# fixtures/sample_responses.json are the only credential store available to it.
# Logging in with them is refused unless this is set, which keeps those
# committed passwords from working on a deployed instance.
os.environ.setdefault("PAEDIA_ALLOW_FIXTURE_AUTH", "1")
