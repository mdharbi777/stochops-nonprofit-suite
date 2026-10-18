"""خطوات ما بعد التثبيت — تُستدعى من hooks.after_install (idempotent)."""
from stochops_nonprofit.setup.notifications import ensure_notifications
from stochops_nonprofit.setup.roles import ensure_roles


def after_install():
    ensure_roles()
    ensure_notifications()
