import os
import sys

sys.path.insert(0, os.path.abspath("."))

# Point the database somewhere that cannot resolve, so APIState starts in its
# no-database mode no matter where the suite runs.
#
# This is not only about determinism. Run inside the api container the suite
# reached the live Postgres and wrote to it: the E2E tests left behind twenty-odd
# "Temporary Test Course" and "T06 E2E Regression Course" rows, plus their
# uploaded documents, in the database the team actually uses. It also made
# results depend on the environment - the same test passed in CI and failed in
# the container once the demo passwords were rotated.
os.environ["POSTGRES_HOST"] = "postgres-disabled-during-tests.invalid"

# With no database, the demo accounts in fixtures/sample_responses.json are the
# only credential store, and logging in with them is refused unless this is set.
# That keeps those committed passwords from working on a deployed instance.
os.environ.setdefault("PAEDIA_ALLOW_FIXTURE_AUTH", "1")
