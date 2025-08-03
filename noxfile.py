"""Run tests with nox."""

from __future__ import annotations

import nox
from nox import Session


@nox.session(python=["3.9", "3.10", "3.11", "3.12", "3.13"])
def tests(session: Session) -> None:
    """Run the test suite with minimal dependencies."""
    session.install("-e", ".")
    session.run("pytest")
