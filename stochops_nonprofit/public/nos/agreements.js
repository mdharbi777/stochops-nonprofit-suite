/* شاشة الاتفاقيات والإقرارات (P5): تعرض ما قَبِلته الجمعية من اتفاقيات (شروط/DPA) بإصدارها
   وممثّلها ووقتها وبصمتها — معزولة بالجمعية (الخادم مصدر الحقيقة). */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "", USER = window.NOS_USER || "Guest";

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args){
    var url="/api/method/"+method; if(args) url+="?"+new URLSearchParams(args).toString();
    return fetch(url, { headers:{ "X-Frappe-CSRF-Token":CSRF } }).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }

  if(!USER || USER==="Guest"){
    app.innerHTML='<div class="ds-state"><h3>الاتفاقيات والإقرارات</h3><p>يجب تسجيل الدخول.</p><a class="ds-btn ds-btn--primary" href="/login?redirect-to=/nos/agreements">تسجيل الدخول</a></div>';
    return;
  }

  app.innerHTML='<div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>…</p></div>';
  api("frappe.client.get_list",{doctype:"Legal Acceptance",
    fields:JSON.stringify(["name","document_title","document_version","representative_name","representative_title","accepted_on","document_hash"]),
    order_by:"accepted_on desc", limit_page_length:0}).then(function(res){
    if(!res.ok){ app.innerHTML='<div class="ds-state ds-state--error"><h3>لا صلاحية</h3><p>هذه الشاشة لمدير الجمعية.</p></div>'; return; }
    var rows=res.j.message||[];
    var html='<h1>الاتفاقيات والإقرارات</h1>'+
      '<p class="muted">سجلّ ما قَبِلته جمعيتك من اتفاقيات المشغّل — بإصدارها ووقتها وبصمتها (دليل إثبات غير قابل للتعديل).</p>';
    if(!rows.length){
      html+='<div class="ds-state ds-state--empty"><h3>لا اتفاقيات مقبولة بعد</h3><p>تظهر هنا بعد قبول الاتفاقيات عند تفعيل الجمعية.</p></div>';
    } else {
      html+='<div class="panel"><div class="ds-table-wrap"><table class="ds-table"><thead><tr><th>الاتفاقية</th><th>الإصدار</th><th>الممثّل</th><th>وقت القبول</th><th>البصمة</th></tr></thead><tbody>'+
        rows.map(function(r){ return '<tr><td>'+esc(r.document_title||r.name)+'</td><td class="nl-mono">'+esc(r.document_version||"—")+'</td>'+
          '<td>'+esc(r.representative_name||"—")+(r.representative_title?' — '+esc(r.representative_title):'')+'</td>'+
          '<td class="nl-mono">'+esc(r.accepted_on||"—")+'</td>'+
          '<td class="nl-mono" style="font-size:11px;max-width:160px;overflow:hidden;text-overflow:ellipsis">'+esc((r.document_hash||"").slice(0,16))+(r.document_hash?'…':'')+'</td></tr>'; }).join("")+
        '</tbody></table></div></div>';
    }
    app.innerHTML=html;
  });
})();
