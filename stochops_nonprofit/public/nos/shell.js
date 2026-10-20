/* هيكل منصة الفاضل الموحّد: قائمة جانبية ثابتة + شريط علوي + تنقّل.
   يُضمَّن في صفحات الوحدات داخل /nos ويبني الهيكل وقت التشغيل دون تعديل محتوى الصفحة. */
(function () {
  "use strict";
  var NAV = [
    { items: [["لوحة التشغيل", "/nos/console", "📊"]] },
    { sec: "المستفيدون", items: [["المستفيدون", "/nos/beneficiaries", "👤"], ["طلبات المساعدة", "/nos/assistance", "🤝"]] },
    { sec: "الموارد والمالية", items: [["المتبرعون", "/nos/donors", "💛"], ["المنح", "/nos/grants", "🎁"], ["المصروفات", "/nos/expenses", "💳"], ["المشتريات", "/nos/procurement", "🛒"]] },
    { sec: "الحوكمة", items: [["اللجان", "/nos/committees", "🏛️"], ["الاجتماعات", "/nos/meetings", "📅"], ["القرارات", "/nos/decisions", "✅"], ["المبادرات", "/nos/initiatives", "🚀"], ["المهام", "/nos/tasks", "📌"], ["الالتزامات الحكومية", "/nos/compliance", "📋"]] },
    { sec: "الموارد البشرية", items: [["الموظفون والعقود", "/nos/personnel", "🧑‍💼"]] },
    { sec: "التقارير والذكاء", items: [["التقارير", "/nos/reports", "📈"], ["المساعد الذكي", "/nos/ai", "🤖"]] },
    { sec: "الخصوصية (PDPL)", items: [["الخصوصية وحماية البيانات", "/nos/privacy", "🔒"], ["حقوق الأفراد", "/nos/rights", "🛡️"], ["الإفصاح والمشاركة", "/nos/disclosures", "📤"], ["الحوادث والاحتفاظ", "/nos/incidents", "⚠️"]] },
    { sec: "الإدارة", items: [["إدارة الحسابات", "/nos/accounts", "👥"], ["إعدادات الجمعية", "/nos/settings", "⚙️"], ["الدليل", "/nos/guide", "📖"]] }
  ];

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function cookie(k) { var m = document.cookie.match("(^|;)\\s*" + k + "\\s*=\\s*([^;]+)"); return m ? decodeURIComponent(m.pop()) : ""; }

  function currentPath() {
    var p = location.pathname.replace(/\/+$/, "");
    if (p === "/nos" || p === "") p = "/nos/console";
    return p;
  }

  function label(path) {
    for (var g = 0; g < NAV.length; g++) for (var i = 0; i < NAV[g].items.length; i++) if (NAV[g].items[i][1] === path) return NAV[g].items[i][0];
    return "منصة الفاضل";
  }

  function build() {
    if (document.querySelector(".nos-sidebar")) return;
    var path = currentPath();
    document.body.classList.add("nos-app");
    // إخفاء أي شريط علوي قديم داخل الصفحة لتفادي التكرار
    document.querySelectorAll(".topbar").forEach(function (t) { t.style.display = "none"; });

    // القائمة الجانبية
    var sb = el("aside", "nos-sidebar");
    var brand = el("div", "nos-sb-brand", '<span class="mk"><i></i><i></i><i></i></span><b>Stoch</b><span>ops</span>');
    sb.appendChild(brand);
    var nav = el("nav", "nos-sb-nav");
    NAV.forEach(function (grp) {
      if (grp.sec) nav.appendChild(el("div", "nos-sb-sec", grp.sec));
      grp.items.forEach(function (it) {
        var a = el("a", "nos-sb-link" + (it[1] === path ? " active" : ""));
        a.href = it[1];
        a.innerHTML = '<span class="ic">' + it[2] + "</span><span>" + it[0] + "</span>";
        nav.appendChild(a);
      });
    });
    sb.appendChild(nav);
    sb.appendChild(el("div", "nos-sb-foot", 'نسخة تجريبية · <span class="pill">بيانات مصطنعة</span>'));
    document.body.insertBefore(sb, document.body.firstChild);
    var scrim = el("div", "nos-scrim");
    scrim.addEventListener("click", function () { document.body.classList.remove("nos-sb-open"); });
    document.body.insertBefore(scrim, document.body.firstChild);

    // الشريط العلوي الموحّد
    var user = cookie("full_name") || cookie("user_id") || "";
    var top = el("header", "nos-top");
    top.innerHTML =
      '<div class="cr">' +
      '<button class="nos-burger" aria-label="القائمة">☰</button>' +
      '<div><div class="nm" id="nosCharity">منصة الفاضل</div>' +
      '<div class="bc">منصة الفاضل <b>›</b> ' + label(path) + "</div></div></div>" +
      '<div class="ac"><span class="u">' + (user || "مستخدم") + "</span>" +
      '<a href="/nos/settings">الإعدادات</a>' +
      '<a href="#" id="nosLogout">خروج</a></div>';
    var wrap = document.querySelector(".wrap") || document.body;
    wrap.insertBefore(top, wrap.firstChild);

    top.querySelector(".nos-burger").addEventListener("click", function () { document.body.classList.toggle("nos-sb-open"); });
    top.querySelector("#nosLogout").addEventListener("click", function (e) {
      e.preventDefault();
      fetch("/api/method/logout", { headers: { "X-Frappe-CSRF-Token": (window.frappe && frappe.csrf_token) || "" } })
        .finally(function () { location.href = "/nos"; });
    });

    // اسم الجمعية (اختياري — لا يُعطّل الشريط إن فشل)
    try {
      fetch("/api/method/frappe.client.get_value?doctype=User&filters=" + encodeURIComponent(JSON.stringify({ name: cookie("user_id") })) + "&fieldname=charity")
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var ch = d && d.message && d.message.charity;
          if (!ch) return;
          return fetch("/api/method/frappe.client.get_value?doctype=Charity&filters=" + encodeURIComponent(JSON.stringify({ name: ch })) + "&fieldname=charity_name")
            .then(function (r) { return r.json(); })
            .then(function (d2) { if (d2 && d2.message && d2.message.charity_name) document.getElementById("nosCharity").textContent = d2.message.charity_name; });
        }).catch(function () {});
    } catch (e) {}
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
