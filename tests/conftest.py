"""Shared pytest setup.

Redirect scheduler output to a throw-away directory *before* ``unitime_app.config`` is imported,
so running the suite never adds files to the project's real ``generated_outputs/`` folder.
An explicit ``UNITIME_GEN_DIR`` set by the caller is respected.
"""
import os
import tempfile

os.environ.setdefault("UNITIME_GEN_DIR", tempfile.mkdtemp(prefix="unitime_test_outputs_"))
