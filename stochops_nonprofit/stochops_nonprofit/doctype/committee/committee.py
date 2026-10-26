from frappe.model.document import Document

from stochops_nonprofit.governance import guard_transition

# آلة حالات اللجنة: أرشفة قابلة للاستعادة (نشطة ⇄ مؤرشفة).
STATUS_FLOW = {"نشطة": {"مؤرشفة"}, "مؤرشفة": {"نشطة"}}


class Committee(Document):
    def validate(self):
        guard_transition(self, STATUS_FLOW)
