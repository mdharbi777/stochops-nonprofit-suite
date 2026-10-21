/* محرّك التفاصيل الموحّد (P2) — config-driven. يقرأ window.NOS_DETAIL ويبني صفحة تفاصيل سجل:
   مسار تنقّل + عنوان + حالة + حقول (مع كشف/روابط) + إجراءات حالة + علاقات (جداول مرتبطة) + حالات واجهة. */
(function () {
  "use strict";
  var C = window.NOS_DETAIL; if (!C) return;
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "", USER = window.NOS_USER || "Guest";
  var NAME = new URLSearchParams(location.search).get("name") || "";

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args, isPost){
    var opt={ headers:{ "X-Frappe-CSRF-Token":CSRF } }, url="/api/method/"+method;
    if(isPost){ opt.method="POST"; opt.headers["Content-Type"]="application/json"; opt.body=JSON.stringify(args||{}); }
    else if(args){ url+="?"+new URLSearchParams(args).toString(); }
    return fetch(url,opt).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }
  function errMsg(res){ try{ var sm=JSON.parse(res.j._server_messages||"[]"); if(sm.length) return (JSON.parse(sm[0]).message||"").replace(/<[^>]+>/g,""); }catch(e){} return "تعذّر تنفيذ العملية."; }
  var BMAP={ "نشط":"ok","معتمد":"ok","مصروف":"ok","مكتمل":"ok","مرفوض":"danger","متأخر":"danger","قيد المراجعة":"warn","عالية":"warn","مؤرشف":"muted","مقدم":"muted","مقدّم":"muted","ملغى":"muted","مسودة":"muted" };
  function badge(v){ return '<span class="ds-badge ds-badge--'+(BMAP[v]||"muted")+'">'+esc(v||"—")+'</span>'; }
  function money(v){ return v!=null?Number(v).toLocaleString("en"):"—"; }
  function toast(msg,ref,isErr){ var t=document.createElement("div"); t.className="ds-toast "+(isErr?"ds-toast--err":"ds-toast--ok"); t.innerHTML=esc(msg)+(ref?' <span class="ref">('+esc(ref)+')</span>':""); document.body.appendChild(t); setTimeout(function(){t.remove();},3000); }

  if(!USER || USER==="Guest"){ app.innerHTML='<div class="ds-state"><h3>التفاصيل</h3><p>يجب تسجيل الدخول.</p><a class="ds-btn ds-btn--primary" href="/login?redirect-to='+esc(C.loginRedirect||C.listRoute)+'">تسجيل الدخول</a></div>'; return; }
  if(!NAME){ app.innerHTML='<div class="ds-state ds-state--error"><h3>سجل غير محدد</h3><p>لم يُحدَّد السجل.</p><a class="ds-btn ds-btn--secondary" href="'+esc(C.listRoute)+'">عودة للقائمة</a></div>'; return; }

  function load(){
    app.innerHTML='<div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>جارٍ التحميل…</p></div>';
    api("frappe.client.get",{doctype:C.doctype,name:NAME}).then(function(res){
      if(!res.ok){ var m=errMsg(res), np=/permission|صلاحية|not permitted/i.test(m);
        app.innerHTML='<div class="ds-state '+(np?'':'ds-state--error')+'"><h3>'+(np?'لا صلاحية':'تعذّر التحميل')+'</h3><p>'+esc(m)+'</p><a class="ds-btn ds-btn--secondary" href="'+esc(C.listRoute)+'">عودة للقائمة</a></div>'; return; }
      render(res.j.message||{});
    });
  }

  function fieldVal(f,doc){
    var v=doc[f.field];
    if(f.reveal) return '<button class="ds-btn ds-btn--secondary ds-btn--sm" data-reveal="'+esc(f.reveal)+'" data-arg="'+esc(f.revealArg||"name")+'">كشف</button>';
    if(f.badge) return badge(v);
    if(f.money) return '<span class="nd-mono">'+money(v)+'</span>';
    if(f.link && v) return '<a href="'+esc(f.link)+'?name='+encodeURIComponent(v)+'">'+esc(v)+'</a>';
    return esc(v==null||v===""?"—":String(v));
  }

  function render(doc){
    var title=doc[C.titleField]||NAME, st=C.statusField?doc[C.statusField]:null;
    var kv=C.fields.map(function(f){ return '<div><div class="nd-k">'+esc(f.label)+'</div><div class="nd-v" data-fld="'+esc(f.field)+'">'+fieldVal(f,doc)+'</div></div>'; }).join("");
    var actions=(C.statusActions||[]).filter(function(a){return a.when===st;}).map(function(a){
      return '<button class="ds-btn ds-btn--'+(a.variant||"secondary")+'" data-to="'+esc(a.to)+'">'+esc(a.label)+'</button>';
    }).join("");
    app.innerHTML=
      '<div class="nd-crumb"><a href="'+esc(C.listRoute)+'">'+esc(C.crumbLabel)+'</a> &rsaquo; '+esc(title)+'</div>'+
      '<h1>'+esc(title)+'</h1><p class="muted">'+esc(doc.name)+(st?' — '+badge(st):'')+'</p>'+
      '<div class="panel"><h3>'+esc(C.sectionTitle||"البيانات")+'</h3><div class="nd-kv">'+kv+'</div>'+
      '<div class="nd-actions">'+actions+'<a class="ds-btn ds-btn--secondary" href="'+esc(C.listRoute)+'">عودة للقائمة</a></div></div>'+
      (C.relations||[]).map(function(r,i){ return '<div class="panel" id="rel'+i+'"><h3>'+esc(r.title)+'</h3><div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>جارٍ التحميل…</p></div></div>'; }).join("");

    document.querySelectorAll("[data-reveal]").forEach(function(b){ b.onclick=function(){ doReveal(b); }; });
    document.querySelectorAll("[data-to]").forEach(function(b){ b.onclick=function(){ setStatus(b.getAttribute("data-to")); }; });
    (C.relations||[]).forEach(function(r,i){ loadRel(r,i); });
  }

  function doReveal(btn){
    btn.disabled=true; var arg={}; arg[btn.getAttribute("data-arg")]=NAME;
    api(btn.getAttribute("data-reveal"),arg,true).then(function(res){
      var cell=btn.closest(".nd-v");
      if(res.ok && res.j.message){ var k=Object.keys(res.j.message)[0]; cell.innerHTML='<span class="nd-mono">'+esc(res.j.message[k]||"—")+'</span>'; }
      else { cell.innerHTML='<span class="ds-err">'+esc(errMsg(res))+'</span>'; }
    });
  }
  function setStatus(to){
    api("frappe.client.set_value",{doctype:C.doctype,name:NAME,fieldname:C.statusField,value:to},true).then(function(res){
      if(res.ok){ toast("تم التحديث",NAME); load(); } else { toast("تعذّر التحديث: "+errMsg(res),null,true); }
    });
  }
  function loadRel(r,i){
    var p=document.getElementById("rel"+i);
    var flds=["name"].concat(r.columns.map(function(c){return c.field;}).filter(function(f){return f!=="name";}));
    api("frappe.client.get_list",{doctype:r.doctype,fields:JSON.stringify(flds),filters:JSON.stringify([[r.filterField,"=",NAME]]),order_by:"creation desc",limit_page_length:50}).then(function(res){
      if(!res.ok){ p.innerHTML='<h3>'+esc(r.title)+'</h3><div class="ds-state ds-state--error"><p>'+esc(errMsg(res))+'</p></div>'; return; }
      var data=res.j.message||[];
      if(!data.length){ p.innerHTML='<h3>'+esc(r.title)+'</h3><div class="ds-state ds-state--empty"><p>لا توجد سجلات مرتبطة.</p>'+(r.createRoute?'<a class="ds-btn ds-btn--primary" href="'+esc(r.createRoute)+'">'+esc(r.createLabel||"إنشاء")+'</a>':'')+'</div>'; return; }
      var head=r.columns.map(function(c){return '<th>'+esc(c.label)+'</th>';}).join("");
      var rows=data.map(function(row){ return '<tr>'+r.columns.map(function(c){ var v=row[c.field]; var out=c.badge?badge(v):(c.money?'<span class="nd-mono">'+money(v)+'</span>':esc(v==null?"—":String(v))); return '<td>'+out+'</td>'; }).join("")+'</tr>'; }).join("");
      p.innerHTML='<h3>'+esc(r.title)+' ('+data.length+')</h3><div class="ds-table-wrap"><table class="ds-table"><thead><tr>'+head+'</tr></thead><tbody>'+rows+'</tbody></table></div>';
    });
  }

  load();
})();
