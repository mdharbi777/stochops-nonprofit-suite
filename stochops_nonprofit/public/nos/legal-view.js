/* عارض المركز القانوني (P1). يقرأ window.LEGAL_SLUG:
   - فارغ  => قائمة الوثائق المنشورة (مركز قانوني).
   - معرّف => عرض الوثيقة المنشورة لذلك المسار.
   المحتوى من نقطة guest للقراءة فقط (الخادم مصدر الحقيقة؛ تُعرض النسخة المنشورة فقط). */
(function () {
  "use strict";
  var app = document.getElementById("legal");
  if (!app) return;
  var slug = window.LEGAL_SLUG || "";
  var LANG = "ar";

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args){
    var u = "/api/method/" + method;
    if (args) u += "?" + new URLSearchParams(args).toString();
    return fetch(u).then(function(r){ return r.json(); }).then(function(j){ return (j && j.message) || null; });
  }

  if (!slug) {
    app.innerHTML = '<p class="muted">…جارِ التحميل</p>';
    api("stochops_nonprofit.legal_document.list_published", { language: LANG }).then(function(docs){
      docs = docs || [];
      app.innerHTML =
        '<h1>المركز القانوني</h1>' +
        '<p class="muted">الوثائق القانونية المنشورة للمشغّل. كل نسخة منشورة ثابتة بإصدار وتاريخ نفاذ وبصمة محتوى.</p>' +
        (docs.length
          ? '<ul class="legal-list">' + docs.map(function(d){
              return '<li><a href="/legal/' + esc(d.slug) + '">' + esc(d.title) + '</a> ' +
                     '<span class="muted">— إصدار ' + esc(d.version) + (d.effective_date ? ' · نفاذ ' + esc(d.effective_date) : '') + '</span></li>';
            }).join("") + '</ul>'
          : '<p class="muted">لا توجد وثائق منشورة بعد.</p>');
    });
    return;
  }

  app.innerHTML = '<p class="muted">…جارِ التحميل</p>';
  api("stochops_nonprofit.legal_document.get_published", { slug: slug, language: LANG }).then(function(d){
    if (!d) {
      app.innerHTML = '<h1>وثيقة غير منشورة</h1>' +
        '<p class="muted">لم تُنشر هذه الوثيقة بعد. تُعرض بمجرد اعتمادها ونشرها من مشغّل المنصّة.</p>' +
        '<p class="crumb"><a href="/legal">العودة إلى المركز القانوني</a></p>';
      return;
    }
    app.innerHTML =
      '<div class="crumb"><a href="/legal">المركز القانوني</a> &rsaquo; ' + esc(d.title) + '</div>' +
      '<h1>' + esc(d.title) + '</h1>' +
      '<p class="muted">المُصدر: ' + esc(d.operator) + ' · إصدار ' + esc(d.version) +
        (d.effective_date ? ' · تاريخ النفاذ ' + esc(d.effective_date) : '') + '</p>' +
      '<div class="legal-content">' + (d.content || "") + '</div>' +
      '<p class="hash">بصمة المحتوى (SHA-256): <code>' + esc(d.content_hash || "") + '</code></p>';
  });
})();
