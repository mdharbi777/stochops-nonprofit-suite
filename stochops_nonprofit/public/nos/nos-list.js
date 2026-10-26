/* محرّك القوائم الموحّد (P2) — config-driven. يقرأ window.NOS_LIST ويبني صفحة قائمة كاملة:
   بحث + تصفية + ترقيم على الخادم + فرز أعمدة + Design System + حالات (تحميل/فراغ/خطأ/لا صلاحية) + نموذج إضافة.
   يعتمد window.NOS_CSRF و window.NOS_USER المحقونين من الصفحة. */
(function () {
  "use strict";
  var C = window.NOS_LIST; if (!C) return;
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "", USER = window.NOS_USER || "Guest";

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args, isPost){
    var opt={ headers:{ "X-Frappe-CSRF-Token":CSRF } }, url="/api/method/"+method;
    if(isPost){ opt.method="POST"; opt.headers["Content-Type"]="application/json"; opt.body=JSON.stringify(args||{}); }
    else if(args){ url+="?"+new URLSearchParams(args).toString(); }
    return fetch(url,opt).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }
  function errMsg(res){ try{ var sm=JSON.parse(res.j._server_messages||"[]"); if(sm.length) return (JSON.parse(sm[0]).message||"").replace(/<[^>]+>/g,""); }catch(e){} return "تعذّر تنفيذ العملية."; }
  function showAlert(box,msg,isErr){ if(!box) return; box.innerHTML='<div class="ds-alert ds-alert--'+(isErr?"err":"ok")+'"><span class="ico">'+(isErr?"⚠":"✓")+'</span>'+
    '<div class="bd"><b>'+(isErr?"تعذّر الحفظ":"تم")+'</b>'+esc(msg)+'</div><button type="button" class="x" aria-label="إغلاق">✕</button></div>';
    var x=box.querySelector(".x"); if(x) x.onclick=function(){ box.innerHTML=""; }; }
  var BMAP={ "نشط":"ok","نشطة":"ok","معتمد":"ok","معتمدة":"ok","مصروف":"ok","مُنفّذ":"ok","مكتمل":"ok","ساري":"ok","مرفوض":"danger","مرفوضة":"danger","متأخر":"danger","قيد المراجعة":"warn","قيد الإعداد":"warn","قيد التنفيذ":"warn","عالية":"warn","موقوف":"warn","High":"warn","In Progress":"warn","مؤرشف":"muted","مؤرشفة":"muted","مقدم":"muted","مقدّم":"muted","مقترحة":"muted","مقدَّمة":"muted","مغلقة":"muted","منتهٍ":"muted","قادم":"muted","ملغى":"muted","مسودة":"muted","Open":"muted","Completed":"ok","Cancelled":"muted","Normal":"muted","Draft":"muted","Approved":"ok" };
  function badge(v){ return '<span class="ds-badge ds-badge--'+(BMAP[v]||"muted")+'">'+esc(v||"—")+'</span>'; }
  function money(v){ return v!=null ? Number(v).toLocaleString("en") : "—"; }

  if(!USER || USER==="Guest"){
    app.innerHTML='<div class="ds-state"><h3>'+esc(C.title)+'</h3><p>يجب تسجيل الدخول للوصول إلى هذه الصفحة.</p><a class="ds-btn ds-btn--primary" href="/login?redirect-to='+esc(C.loginRedirect||"/nos/console")+'">تسجيل الدخول</a></div>';
    return;
  }

  var state={ page:1, size:10, search:"", filters:{}, sort:(C.defaultSort||"creation"), dir:"desc", total:0 }, tmr;
  function buildFilters(){
    var f=[];
    (C.filters||[]).forEach(function(flt){ if(state.filters[flt.field]) f.push([flt.field,"=",state.filters[flt.field]]); });
    if(C.search && state.search) f.push([C.search.field,"like","%"+state.search+"%"]);
    return f;
  }

  function render(){
    var filtersHtml=(C.filters||[]).map(function(flt){
      return '<select data-flt="'+flt.field+'"><option value="">'+esc(flt.label)+'</option>'+flt.options.map(function(o){return '<option>'+esc(o)+'</option>';}).join("")+'</select>';
    }).join("");
    app.innerHTML=
      '<div class="pagehdr"><div><h1>'+esc(C.title)+'</h1>'+(C.desc?'<p class="muted">'+esc(C.desc)+'</p>':'')+'</div>'+
      (C.addFields?'<button class="ds-btn ds-btn--primary" id="addToggle" type="button">'+esc(C.addLabel||"إضافة")+'</button>':'')+'</div>'+
      (C.note?'<div class="nl-note">'+esc(C.note)+'</div>':'')+
      '<div class="nl-toolbar">'+
        (C.search?'<input class="nl-search" id="q" placeholder="'+esc(C.search.placeholder||"بحث...")+'" autocomplete="off">':'')+
        filtersHtml+
        '<select id="fsize"><option value="10">10 لكل صفحة</option><option value="25">25</option><option value="50">50</option></select>'+
      '</div><div id="addpanel"></div><div class="panel" id="listpanel"></div>';
    var at=document.getElementById("addToggle"); if(at) at.onclick=toggleAdd;
    var q=document.getElementById("q"); if(q) q.oninput=function(e){ clearTimeout(tmr); tmr=setTimeout(function(){ state.search=e.target.value.trim(); state.page=1; load(); },350); };
    document.querySelectorAll("[data-flt]").forEach(function(s){ s.onchange=function(){ state.filters[s.getAttribute("data-flt")]=s.value; state.page=1; load(); }; });
    document.getElementById("fsize").onchange=function(e){ state.size=parseInt(e.target.value,10); state.page=1; load(); };
    load();
  }

  function sortTh(col){
    if(!col.sortable) return '<th>'+esc(col.label)+'</th>';
    var active=state.sort===col.field, dir=active?(state.dir==="asc"?" ↑":" ↓"):"";
    return '<th class="nl-sort" data-f="'+col.field+'">'+esc(col.label)+'<span style="color:var(--nl-cyan)">'+dir+'</span></th>';
  }
  function cell(col,row){
    var v=row[col.field];
    if(col.badge) return badge(v);
    if(col.money) return '<span class="nl-mono">'+money(v)+'</span>';
    return esc(v==null||v===""?"—":String(v));
  }

  function load(){
    var lp=document.getElementById("listpanel");
    lp.innerHTML='<div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>جارٍ التحميل…</p></div>';
    var fl=JSON.stringify(buildFilters());
    var flds=["name"].concat(C.columns.map(function(c){return c.field;}).filter(function(f){return f!=="name";}));
    api("frappe.client.get_count",{doctype:C.doctype,filters:fl}).then(function(cr){
      state.total=(cr.ok&&typeof cr.j.message==="number")?cr.j.message:0;
      api("frappe.client.get_list",{ doctype:C.doctype, fields:JSON.stringify(flds), filters:fl,
        order_by:state.sort+" "+state.dir, limit_start:(state.page-1)*state.size, limit_page_length:state.size }).then(function(res){
        if(!res.ok){ lp.innerHTML='<div class="ds-state ds-state--error"><h3>تعذّر تحميل القائمة</h3><p>'+esc(errMsg(res))+'</p><button class="ds-btn ds-btn--secondary" id="retry">إعادة المحاولة</button></div>'; var rb=document.getElementById("retry"); if(rb)rb.onclick=load; return; }
        var data=res.j.message||[];
        if(!data.length && state.total===0){
          lp.innerHTML='<div class="ds-state ds-state--empty"><h3>لا توجد سجلات</h3><p>ابدأ بإضافة أول سجل.</p>'+(C.addFields?'<button class="ds-btn ds-btn--primary" id="emptyadd">'+esc(C.addLabel||"إضافة")+'</button>':'')+'</div>';
          var ea=document.getElementById("emptyadd"); if(ea) ea.onclick=toggleAdd; return;
        }
        var rows=data.map(function(row){
          var tds=C.columns.map(function(c){ var hs=c.hideSmall?' class="nl-hs"':''; return '<td'+hs+'>'+cell(c,row)+'</td>'; }).join("");
          var open=C.detailRoute?'<td><span class="ds-btn ds-btn--secondary ds-btn--sm">فتح</span></td>':'';
          return '<tr'+(C.detailRoute?' class="nl-row" data-n="'+esc(row.name)+'"':'')+'>'+tds+open+'</tr>';
        }).join("");
        var from=(state.page-1)*state.size+1, to=Math.min(state.page*state.size,state.total), pages=Math.max(1,Math.ceil(state.total/state.size));
        lp.innerHTML='<div class="ds-table-wrap"><table class="ds-table"><thead><tr>'+C.columns.map(sortTh).join("")+(C.detailRoute?'<th></th>':'')+'</tr></thead><tbody>'+rows+'</tbody></table></div>'+
          '<div class="nl-pager"><div>عرض '+from+'–'+to+' من '+state.total+'</div><div class="nav">'+
          '<button class="ds-btn ds-btn--secondary ds-btn--sm" id="prev" '+(state.page<=1?'disabled':'')+'>السابق</button>'+
          '<span>صفحة '+state.page+' من '+pages+'</span>'+
          '<button class="ds-btn ds-btn--secondary ds-btn--sm" id="next" '+(state.page>=pages?'disabled':'')+'>التالي</button></div></div>';
        document.querySelectorAll(".nl-sort").forEach(function(th){ th.onclick=function(){ var f=th.getAttribute("data-f"); if(state.sort===f){state.dir=state.dir==="asc"?"desc":"asc";}else{state.sort=f;state.dir="asc";} load(); }; });
        if(C.detailRoute) document.querySelectorAll(".nl-row").forEach(function(tr){ tr.style.cursor="pointer"; tr.onclick=function(){ location.href=C.detailRoute+"?name="+encodeURIComponent(tr.getAttribute("data-n")); }; });
        var pv=document.getElementById("prev"), nx=document.getElementById("next");
        if(pv) pv.onclick=function(){ if(state.page>1){state.page--; load();} };
        if(nx) nx.onclick=function(){ if(state.page<pages){state.page++; load();} };
      });
    });
  }

  function toggleAdd(){
    var p=document.getElementById("addpanel"); if(p.innerHTML){ p.innerHTML=""; return; }
    var fh=C.addFields.map(function(f){
      var inp;
      if(f.type==="select"){ inp='<select class="ds-select" id="f_'+f.field+'"><option value="">—</option>'+f.options.map(function(o){return '<option>'+esc(o)+'</option>';}).join("")+'</select>'; }
      else if(f.type==="number"){ inp='<input class="ds-input" id="f_'+f.field+'" type="number" min="0" value="'+esc(f.default||"0")+'">'; }
      else if(f.type==="date"){ inp='<input class="ds-input" id="f_'+f.field+'" type="date">'; }
      else { inp='<input class="ds-input" id="f_'+f.field+'">'; }
      return '<div class="ds-field"><label>'+esc(f.label)+(f.required?' <span class="req">*</span>':'')+'</label>'+inp+'</div>';
    }).join("");
    p.innerHTML='<div class="panel"><h3 style="color:#fff;margin-bottom:10px">'+esc(C.addLabel||"إضافة")+'</h3>'+fh+
      '<div id="addmsg" class="ds-err"></div><div style="margin-top:8px;display:flex;gap:10px">'+
      '<button class="ds-btn ds-btn--primary" id="addbtn">حفظ</button><button class="ds-btn ds-btn--secondary" id="addcancel">إلغاء</button></div></div>';
    document.getElementById("addbtn").onclick=addRec;
    document.getElementById("addcancel").onclick=toggleAdd;
  }
  window.__nosToggleAdd=toggleAdd;

  function addRec(){
    var em=document.getElementById("addmsg"), doc={doctype:C.doctype};
    for(var i=0;i<C.addFields.length;i++){
      var f=C.addFields[i], el=document.getElementById("f_"+f.field), v=(el.value||"").trim();
      if(f.required && !v){ showAlert(em,esc(f.label)+" مطلوب.",true); return; }
      if(v && f.pattern && !f.pattern.test(v)){ showAlert(em,f.patternMsg||"قيمة غير صحيحة.",true); return; }
      if(v!==""){
        if(f.type==="number"){ var n=parseInt(v,10); if(isNaN(n)) n=0; if(n<0){ n=0; el.value="0"; } // لا قيم سالبة (مبالغ/أعداد)
          doc[f.field]=n; } else { doc[f.field]=v; }
      }
    }
    var btn=document.getElementById("addbtn"); btn.disabled=true; em.innerHTML="";
    api("frappe.client.insert",{doc:doc},true).then(function(res){
      btn.disabled=false;
      if(res.ok && res.j.message){ toggleAdd(); state.page=1; state.search=""; var q=document.getElementById("q"); if(q)q.value=""; load(); }
      else { showAlert(em,errMsg(res),true); }
    });
  }

  render();
})();
