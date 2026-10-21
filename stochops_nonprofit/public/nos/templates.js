/* مكتبة قوالب الامتثال (P4). قوالب هياكل قابلة للتنزيل (DOCX/XLSX) — الجمعية مسؤولة عن
   تعبئتها والتحقّق منها واعتمادها؛ لا تُعدّ معتمدة من STOCHOPS. */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "", USER = window.NOS_USER || "Guest";

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method){
    return fetch("/api/method/"+method, { headers:{ "X-Frappe-CSRF-Token":CSRF } })
      .then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }

  if(!USER || USER==="Guest"){
    app.innerHTML='<div class="ds-state"><h3>مكتبة الامتثال</h3><p>يجب تسجيل الدخول.</p><a class="ds-btn ds-btn--primary" href="/login?redirect-to=/nos/templates">تسجيل الدخول</a></div>';
    return;
  }

  app.innerHTML='<div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>…</p></div>';
  api("stochops_nonprofit.stochops_nonprofit.doctype.compliance_template.compliance_template.list_templates").then(function(res){
    if(!res.ok){ app.innerHTML='<div class="ds-state ds-state--error"><p>تعذّر تحميل المكتبة.</p></div>'; return; }
    var rows=res.j.message||[];
    var groups={}, order=[];
    rows.forEach(function(t){ if(!groups[t.category]){ groups[t.category]=[]; order.push(t.category); } groups[t.category].push(t); });
    var html='<h1>مكتبة قوالب الامتثال</h1>'+
      '<p class="muted">قوالب جاهزة للتنزيل والتعبئة (Word/Excel) تساعد جمعيتك على توثيق التزاماتها.</p>'+
      '<div class="nl-note"><b>مسؤولية الجمعية:</b> هذه القوالب هياكل بتعليمات تعبئة — الجمعية مسؤولة عن إكمالها والتحقّق منها واعتمادها وتنفيذها. '+
      'لا تُعدّ معتمدة من STOCHOPS ولا استشارة قانونية؛ راجِع المصادر النظامية (PDPL/SDAIA) والمختص. القالب غير مكتمل دون تعبئة.</div>';
    if(!rows.length){ html+='<div class="ds-state ds-state--empty"><p>لا قوالب منشورة حالياً.</p></div>'; }
    order.forEach(function(cat){
      html+='<div class="tpl-cat">'+esc(cat)+'</div>';
      groups[cat].forEach(function(t){
        var dl = t.file_path ? '<a class="ds-btn ds-btn--primary ds-btn--sm" href="'+esc(t.file_path)+'" download>تنزيل '+esc(t.file_format)+'</a>'
                             : '<span class="muted">بانتظار رفع القالب المعتمد</span>';
        html+='<div class="tpl"><div>'+
          '<div><b style="color:#fff">'+esc(t.template_name)+'</b><span class="fmt">'+esc(t.file_format)+' · '+esc(t.version||"")+'</span></div>'+
          '<div class="meta">جهة الاعتماد داخل الجمعية: '+esc(t.required_approver||"—")+' · المصدر: '+esc(t.source_ref||"—")+'</div>'+
          (t.fill_instructions?'<div class="instr">'+esc(t.fill_instructions)+'</div>':'')+
          '</div><div>'+dl+'</div></div>';
      });
    });
    app.innerHTML=html;
  });
})();
