"""خطوات ما بعد التثبيت — تُستدعى من hooks.after_install (idempotent)."""
from stochops_nonprofit.multitenancy import ensure_user_charity_field
from stochops_nonprofit.setup.localization import ensure_arabic
from stochops_nonprofit.setup.notifications import ensure_notifications
from stochops_nonprofit.setup.roles import ensure_roles


def after_install():
    ensure_roles()
    ensure_user_charity_field()
    ensure_notifications()
    ensure_arabic()
