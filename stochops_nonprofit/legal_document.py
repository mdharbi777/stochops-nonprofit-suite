"""Convenience whitelisted endpoints for the public Legal Center.

The front-end (nos/legal-view.js) calls `stochops_nonprofit.legal_document.*`;
these thin wrappers delegate to the DocType controller so the short, stable
path keeps working for guests.
"""

import frappe

from stochops_nonprofit.stochops_nonprofit.doctype.legal_document.legal_document import (
    get_published as _get_published,
)
from stochops_nonprofit.stochops_nonprofit.doctype.legal_document.legal_document import (
    list_published as _list_published,
)


@frappe.whitelist(allow_guest=True)
def list_published(language="ar"):
    return _list_published(language=language)


@frappe.whitelist(allow_guest=True)
def get_published(slug, language="ar"):
    return _get_published(slug=slug, language=language)
