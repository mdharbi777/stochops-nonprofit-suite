app_name = "stochops_nonprofit"
app_title = "Stochops Nonprofit"
app_publisher = "STOCHOPS"
app_description = "Nonprofit Operations Suite for Saudi charities"
app_email = "mohd.s.alharbi@gmail.com"
app_license = "Proprietary"  # الرخصة معلّقة — ليست مفتوحة المصدر (انظر LICENSE)

# خطوات ما بعد التثبيت: الأدوار + الإشعارات + حقل الجمعية على المستخدم (idempotent)
after_install = "stochops_nonprofit.setup.install.after_install"
# يُعاد تشغيلها بعد كل ترقية (migrate) فتُنشأ الأدوار/الإشعارات الجديدة تلقائياً (idempotent)
after_migrate = "stochops_nonprofit.setup.install.after_install"

# ===== عزل متعدّد الجمعيات (multi-tenancy) =====
permission_query_conditions = {
    "Committee": "stochops_nonprofit.multitenancy.committee_query",
    "Meeting": "stochops_nonprofit.multitenancy.meeting_query",
    "Decision": "stochops_nonprofit.multitenancy.decision_query",
    "Initiative": "stochops_nonprofit.multitenancy.initiative_query",
    "Initiative Task": "stochops_nonprofit.multitenancy.initiative_task_query",
    "Beneficiary": "stochops_nonprofit.multitenancy.beneficiary_query",
    "Assistance Request": "stochops_nonprofit.multitenancy.assistance_request_query",
    "Donor": "stochops_nonprofit.multitenancy.donor_query",
    "Donation": "stochops_nonprofit.multitenancy.donation_query",
    "Grant": "stochops_nonprofit.multitenancy.grant_query",
    "Expense Request": "stochops_nonprofit.multitenancy.expense_request_query",
    "Compliance Obligation": "stochops_nonprofit.multitenancy.compliance_obligation_query",
    "Personnel": "stochops_nonprofit.multitenancy.personnel_query",
    "Contract": "stochops_nonprofit.multitenancy.contract_query",
    "Procurement Request": "stochops_nonprofit.multitenancy.procurement_request_query",
    "AI Run Log": "stochops_nonprofit.multitenancy.ai_run_log_query",
    "Processing Activity Record": "stochops_nonprofit.multitenancy.processing_activity_record_query",
    "Sensitive Access Log": "stochops_nonprofit.multitenancy.sensitive_access_log_query",
    "Consent Record": "stochops_nonprofit.multitenancy.consent_record_query",
    "Privacy Rights Request": "stochops_nonprofit.multitenancy.privacy_rights_request_query",
    "Privacy Impact Assessment": "stochops_nonprofit.multitenancy.privacy_impact_assessment_query",
    "Disclosure Request": "stochops_nonprofit.multitenancy.disclosure_request_query",
    "Legal Hold": "stochops_nonprofit.multitenancy.legal_hold_query",
    "Security Incident": "stochops_nonprofit.multitenancy.security_incident_query",
    "Charity": "stochops_nonprofit.multitenancy.charity_query",
}

has_permission = {
    "Committee": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Meeting": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Decision": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Initiative": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Initiative Task": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Beneficiary": "stochops_nonprofit.multitenancy.has_case_permission",
    "Assistance Request": "stochops_nonprofit.multitenancy.has_case_permission",
    "Donor": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Donation": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Grant": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Expense Request": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Compliance Obligation": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Personnel": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Contract": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Procurement Request": "stochops_nonprofit.multitenancy.has_charity_permission",
    "AI Run Log": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Processing Activity Record": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Sensitive Access Log": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Consent Record": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Privacy Rights Request": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Privacy Impact Assessment": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Disclosure Request": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Legal Hold": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Security Incident": "stochops_nonprofit.multitenancy.has_charity_permission",
    "Charity": "stochops_nonprofit.multitenancy.has_charity_doc_permission",
}

doc_events = {
    "Committee": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Meeting": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Decision": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Initiative": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Initiative Task": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Beneficiary": {"before_insert": "stochops_nonprofit.multitenancy.set_charity_case"},
    "Assistance Request": {"before_insert": "stochops_nonprofit.multitenancy.set_charity_case"},
    "Donor": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Donation": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Grant": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Expense Request": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Compliance Obligation": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Personnel": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Contract": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Procurement Request": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "AI Run Log": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Processing Activity Record": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Sensitive Access Log": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Consent Record": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Privacy Rights Request": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Privacy Impact Assessment": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Disclosure Request": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Legal Hold": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
    "Security Incident": {"before_insert": "stochops_nonprofit.multitenancy.set_charity"},
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "stochops_nonprofit",
# 		"logo": "/assets/stochops_nonprofit/logo.png",
# 		"title": "Stochops Nonprofit",
# 		"route": "/stochops_nonprofit",
# 		"has_permission": "stochops_nonprofit.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/stochops_nonprofit/css/stochops_nonprofit.css"
# app_include_js = "/assets/stochops_nonprofit/js/stochops_nonprofit.js"

# include js, css files in header of web template
# web_include_css = "/assets/stochops_nonprofit/css/stochops_nonprofit.css"
# web_include_js = "/assets/stochops_nonprofit/js/stochops_nonprofit.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "stochops_nonprofit/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "stochops_nonprofit/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# بعد الدخول: وجّه مستخدمي الجمعية إلى الواجهة المحوكمة /nos بدل /app
on_session_creation = "stochops_nonprofit.session.route_charity_users_to_nos"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "stochops_nonprofit.utils.jinja_methods",
# 	"filters": "stochops_nonprofit.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "stochops_nonprofit.install.before_install"
# after_install = "stochops_nonprofit.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "stochops_nonprofit.uninstall.before_uninstall"
# after_uninstall = "stochops_nonprofit.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "stochops_nonprofit.utils.before_app_install"
# after_app_install = "stochops_nonprofit.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "stochops_nonprofit.utils.before_app_uninstall"
# after_app_uninstall = "stochops_nonprofit.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "stochops_nonprofit.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "stochops_nonprofit.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "stochops_nonprofit.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["stochops_nonprofit.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"stochops_nonprofit.tasks.all"
# 	],
# 	"daily": [
# 		"stochops_nonprofit.tasks.daily"
# 	],
# 	"hourly": [
# 		"stochops_nonprofit.tasks.hourly"
# 	],
# 	"weekly": [
# 		"stochops_nonprofit.tasks.weekly"
# 	],
# 	"monthly": [
# 		"stochops_nonprofit.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "stochops_nonprofit.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "stochops_nonprofit.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "stochops_nonprofit.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["stochops_nonprofit.utils.before_request"]
# after_request = ["stochops_nonprofit.utils.after_request"]

# Job Events
# ----------
# before_job = ["stochops_nonprofit.utils.before_job"]
# after_job = ["stochops_nonprofit.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"stochops_nonprofit.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

