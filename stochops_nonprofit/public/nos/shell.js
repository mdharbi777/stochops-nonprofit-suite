/* هيكل منصة الفاضل الموحّد (P1): قائمة جانبية نصية (بلا رموز تعبيرية) تعكس دور المستخدم،
   وشريط علوي موحّد مع مسار تنقّل. الأدوار من الخادم عبر stochops_nonprofit.nav.get_my_context.
   الصلاحيات الفعلية مفروضة على الخادم؛ القائمة تُخفي ما لا يحقّ عرضه فقط. */
(function () {
  "use strict";

  var NAV = [
    { items: [["لوحة التحكم", "/nos/console"]] },
    { sec: "المستفيدون", items: [["المستفيدون", "/nos/beneficiaries"], ["طلبات المساعدة", "/nos/assistance"]] },
    { sec: "الموارد والمالية", items: [["المتبرعون", "/nos/donors"], ["المنح", "/nos/grants"], ["المصروفات", "/nos/expenses"], ["المشتريات", "/nos/procurement"]] },
    { sec: "الحوكمة", items: [["اللجان", "/nos/committees"], ["الاجتماعات", "/nos/meetings"], ["القرارات", "/nos/decisions"], ["المبادرات", "/nos/initiatives"], ["المهام", "/nos/tasks"], ["الالتزامات الحكومية", "/nos/compliance"]] },
    { sec: "الموارد البشرية", items: [["الموظفون والعقود", "/nos/personnel"]] },
    { sec: "التقارير والتحليلات", items: [["التقارير", "/nos/reports"], ["المساعد الذكي", "/nos/ai"]] },
    { sec: "الخصوصية وحماية البيانات", items: [["الخصوصية", "/nos/privacy"], ["حقوق الأفراد", "/nos/rights"], ["الإفصاح والمشاركة", "/nos/disclosures"], ["الحوادث والاحتفاظ", "/nos/incidents"]] },
    { sec: "الإدارة", items: [["ملف الجمعية", "/nos/profile"], ["إدارة الحسابات", "/nos/accounts"], ["إعدادات الجمعية", "/nos/settings"], ["مكتبة الامتثال", "/nos/templates"], ["الاتفاقيات والإقرارات", "/nos/agreements"], ["طلبات الاستفادة (المشغّل)", "/nos/applications"], ["الدليل", "/nos/guide"]] }
  ];
  var FULL_ROLES = ["Nonprofit Admin", "System Manager", "Administrator"];
  var OPERATOR_ROLES = ["System Manager", "Stochops Admin", "Administrator"];
  var ADMIN_ONLY = ["/nos/profile", "/nos/accounts", "/nos/settings", "/nos/agreements"];
  var OPERATOR_ONLY = ["/nos/applications"];
  var COORD = {
    "Committee Coordinator": ["/nos/console", "/nos/committees", "/nos/meetings", "/nos/decisions", "/nos/initiatives", "/nos/tasks", "/nos/compliance", "/nos/reports", "/nos/templates", "/nos/guide"],
    "Program Coordinator": ["/nos/console", "/nos/beneficiaries", "/nos/assistance", "/nos/donors", "/nos/grants", "/nos/initiatives", "/nos/tasks", "/nos/reports", "/nos/templates", "/nos/guide"]
  };

  function rolesList() { return (window.NOS_CTX && window.NOS_CTX.roles) || null; }
  function isAdmin() { var r = rolesList(); return r ? r.some(function (x) { return FULL_ROLES.indexOf(x) >= 0; }) : true; }
  function isOperator() { var r = rolesList(); return r ? r.some(function (x) { return OPERATOR_ROLES.indexOf(x) >= 0; }) : true; }
  function canSee(path) {
    var r = rolesList();
    if (!r) return true;                                       // الأدوار غير محمّلة بعد → أظهر الكل (الوصول الفعلي على الخادم)
    // ملاحظة: get_roles يُضمّن "Guest" و"All" لكل مستخدم، فلا نعتمدهما لتمييز الزائر الفعلي.
    if (OPERATOR_ONLY.indexOf(path) >= 0) return isOperator();
    if (ADMIN_ONLY.indexOf(path) >= 0) return isAdmin();
    if (isAdmin()) return true;
    if (r.indexOf("Executive Viewer") >= 0) return true;
    if (path === "/nos/templates") return true;               // مكتبة الامتثال متاحة لكل حسابات الجمعية
    var allowed = {};
    r.forEach(function (x) { var m = COORD[x]; if (m) m.forEach(function (p) { allowed[p] = 1; }); });
    return !!allowed[path];
  }

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function cookie(k) { var m = document.cookie.match("(^|;)\\s*" + k + "\\s*=\\s*([^;]+)"); return m ? decodeURIComponent(m.pop()) : ""; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]; }); }
  function currentPath() { var p = location.pathname.replace(/\/+$/, ""); return (p === "/nos" || p === "") ? "/nos/console" : p; }
  function label(path) { for (var g = 0; g < NAV.length; g++) for (var i = 0; i < NAV[g].items.length; i++) if (NAV[g].items[i][1] === path) return NAV[g].items[i][0]; return "منصة الفاضل"; }

  function build() {
    if (document.querySelector(".nos-sidebar")) return;
    var path = currentPath();
    document.body.classList.add("nos-app");
    document.querySelectorAll(".topbar").forEach(function (t) { t.style.display = "none"; });

    var sb = el("aside", "nos-sidebar");
    sb.appendChild(el("div", "nos-sb-brand", '<span class="mk"><i></i><i></i><i></i></span><b>Stoch</b><span>ops</span>'));
    var nav = el("nav", "nos-sb-nav");
    NAV.forEach(function (grp) {
      var visible = grp.items.filter(function (it) { return canSee(it[1]); });
      if (!visible.length) return;
      if (grp.sec) nav.appendChild(el("div", "nos-sb-sec", esc(grp.sec)));
      visible.forEach(function (it) {
        var a = el("a", "nos-sb-link" + (it[1] === path ? " active" : ""));
        a.href = it[1]; a.textContent = it[0];
        if (it[1] === path) a.setAttribute("aria-current", "page");
        nav.appendChild(a);
      });
    });
    sb.appendChild(nav);
    sb.appendChild(el("div", "nos-sb-foot", "نسخة تجريبية — بيانات مصطنعة"));
    document.body.insertBefore(sb, document.body.firstChild);
    var scrim = el("div", "nos-scrim");
    scrim.addEventListener("click", function () { document.body.classList.remove("nos-sb-open"); });
    document.body.insertBefore(scrim, document.body.firstChild);

    var charityName = (window.NOS_CTX && window.NOS_CTX.charity_name) || "منصة الفاضل";
    var user = (window.NOS_CTX && window.NOS_CTX.user && window.NOS_CTX.user !== "Guest" ? window.NOS_CTX.user : "") || cookie("full_name") || "مستخدم";
    var top = el("header", "nos-top");
    top.innerHTML =
      '<div class="cr"><button class="nos-burger" type="button" aria-label="القائمة">القائمة</button>' +
      '<div><div class="nm">' + esc(charityName) + "</div>" +
      '<div class="bc">منصة الفاضل &rsaquo; ' + esc(label(path)) + "</div></div></div>" +
      '<div class="ac"><span class="u">' + esc(user) + "</span>" +
      '<a href="/nos/settings">الإعدادات</a><a href="#" id="nosLogout">تسجيل الخروج</a></div>';
    var wrap = document.querySelector(".wrap") || document.body;
    wrap.insertBefore(top, wrap.firstChild);

    top.querySelector(".nos-burger").addEventListener("click", function () { document.body.classList.toggle("nos-sb-open"); });
    top.querySelector("#nosLogout").addEventListener("click", function (e) {
      e.preventDefault();
      fetch("/api/method/logout", { headers: { "X-Frappe-CSRF-Token": (window.frappe && frappe.csrf_token) || "" } }).finally(function () { location.href = "/nos"; });
    });
  }

  function boot() {
    fetch("/api/method/stochops_nonprofit.nav.get_my_context", { headers: { "X-Frappe-CSRF-Token": (window.frappe && frappe.csrf_token) || "" } })
      .then(function (r) { return r.json(); })
      .then(function (d) { window.NOS_CTX = (d && d.message) || { roles: null }; })
      .catch(function () { window.NOS_CTX = { roles: null }; })
      .then(build);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
