"""@file __init__.py
@brief Plugin contract check categories (manifest, structure, permissions, security, integration).
"""

from . import (
    code_structure_tests,
    integration_tests,
    manifest_tests,
    permission_tests,
    security_tests,
)

CATEGORIES = {
    "manifest": manifest_tests.run,
    "structure": code_structure_tests.run,
    "permissions": permission_tests.run,
    "security": security_tests.run,
    "integration": integration_tests.run,
}
