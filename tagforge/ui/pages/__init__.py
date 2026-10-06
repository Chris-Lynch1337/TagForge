"""Importing this package registers every @ui.page route.

Add a new screen: create the module, then import it here.
"""
from tagforge.ui.pages import (  # noqa: F401
    browser,
    csv_import,
    editor,
    maintenance,
    tag_list_report,
    validation_report,
)
