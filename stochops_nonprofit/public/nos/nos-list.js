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
      '<div class="nl-hdr-actions">'+
        (C.importable?'<button class="ds-btn ds-btn--secondary" id="importToggle" type="button">استيراد ملف</button>':'')+
        (C.addFields?'<button class="ds-btn ds-btn--primary" id="addToggle" type="button">'+esc(C.addLabel||"إضافة")+'</button>':'')+
      '</div></div>'+
      (C.note?'<div class="nl-note">'+esc(C.note)+'</div>':'')+
      '<div class="nl-toolbar">'+
        (C.search?'<input class="nl-search" id="q" placeholder="'+esc(C.search.placeholder||"بحث...")+'" autocomplete="off">':'')+
        filtersHtml+
        '<select id="fsize"><option value="10">10 لكل صفحة</option><option value="25">25</option><option value="50">50</option></select>'+
      '</div><div id="addpanel"></div><div id="importpanel"></div><div class="panel" id="listpanel"></div>';
    var at=document.getElementById("addToggle"); if(at) at.onclick=toggleAdd;
    var it=document.getElementById("importToggle"); if(it) it.onclick=toggleImport;
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
      else if(f.type==="search"){ inp='<div class="nl-srch"><input class="ds-input" id="f_'+f.field+'" autocomplete="off" placeholder="'+esc(f.placeholder||"ابحث بالاسم...")+'"><input type="hidden" id="h_'+f.field+'"><div class="nl-srch-menu" id="m_'+f.field+'" hidden></div></div>'; }
      else { inp='<input class="ds-input" id="f_'+f.field+'">'; }
      return '<div class="ds-field"><label>'+esc(f.label)+(f.required?' <span class="req">*</span>':'')+'</label>'+inp+'</div>';
    }).join("");
    p.innerHTML='<div class="panel"><h3 style="color:#fff;margin-bottom:10px">'+esc(C.addLabel||"إضافة")+'</h3>'+fh+
      '<div id="addmsg" class="ds-err"></div><div style="margin-top:8px;display:flex;gap:10px">'+
      '<button class="ds-btn ds-btn--primary" id="addbtn">حفظ</button><button class="ds-btn ds-btn--secondary" id="addcancel">إلغاء</button></div></div>';
    document.getElementById("addbtn").onclick=addRec;
    document.getElementById("addcancel").onclick=toggleAdd;
    C.addFields.forEach(function(f){ if(f.type==="search") bindSearch(f); });
  }
  window.__nosToggleAdd=toggleAdd;

  function bindSearch(f){
    var inp=document.getElementById("f_"+f.field), hid=document.getElementById("h_"+f.field), menu=document.getElementById("m_"+f.field), t;
    function close(){ menu.hidden=true; menu.innerHTML=""; }
    function pick(it){ hid.value=it.value; inp.value=it.label+" ("+it.value+")"; close(); }
    inp.oninput=function(){
      hid.value=""; var q=inp.value.trim(); clearTimeout(t);
      t=setTimeout(function(){
        api(f.searchMethod,{q:q}).then(function(res){
          var list=(res.ok && res.j.message)||[];
          if(!list.length){ menu.innerHTML='<div class="nl-srch-empty">لا نتائج مطابقة</div>'; menu.hidden=false; return; }
          menu.innerHTML=list.map(function(it,i){ return '<div class="nl-srch-item" data-i="'+i+'">'+esc(it.label)+' <span class="muted">('+esc(it.value)+(it.hint?" · "+esc(it.hint):"")+')</span></div>'; }).join("");
          menu.hidden=false;
          menu.querySelectorAll(".nl-srch-item").forEach(function(el){ el.onclick=function(){ pick(list[parseInt(el.getAttribute("data-i"),10)]); }; });
        });
      },300);
    };
    inp.onblur=function(){ setTimeout(close,180); }; // تأخير يسمح بنقرة العنصر قبل الإغلاق
  }

  function addRec(){
    var em=document.getElementById("addmsg"), doc={doctype:C.doctype};
    for(var i=0;i<C.addFields.length;i++){
      var f=C.addFields[i], el=document.getElementById((f.type==="search"?"h_":"f_")+f.field), v=(el.value||"").trim();
      if(f.required && !v){ showAlert(em,esc(f.label)+(f.type==="search"?" مطلوب — اختر من نتائج البحث.":" مطلوب."),true); return; }
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

  /* ========== الاستيراد الجماعي (CSV/Excel) ========== */
  var IMP=null; // مخطّط الاستيراد المحمّل من الخادم {doctype,label,max_rows,fields}
  function csvCell(v){ v=String(v==null?"":v); return /[",\r\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v; }
  function norm(s){ return String(s==null?"":s).replace(/^﻿/,"").replace(/\s+/g," ").trim().toLowerCase(); }
  function parseCSV(text){
    text=String(text||"").replace(/^﻿/,"");
    var rows=[],row=[],cur="",q=false,i=0,n=text.length;
    while(i<n){ var c=text[i];
      if(q){ if(c==='"'){ if(text[i+1]==='"'){cur+='"';i+=2;continue;} q=false;i++;continue; } cur+=c;i++;continue; }
      if(c==='"'){ q=true;i++;continue; }
      if(c===','){ row.push(cur);cur="";i++;continue; }
      if(c==='\r'){ i++;continue; }
      if(c==='\n'){ row.push(cur);rows.push(row);row=[];cur="";i++;continue; }
      cur+=c;i++;
    }
    if(cur!==""||row.length){ row.push(cur); rows.push(row); }
    // تجاهل الصفوف الفارغة تماماً
    return rows.filter(function(r){ return r.some(function(x){ return (x||"").trim()!==""; }); });
  }
  function download(name,text){
    var blob=new Blob([text],{type:"text/csv;charset=utf-8"});
    var a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=name;
    document.body.appendChild(a); a.click();
    setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); },0);
  }
  function fieldHint(f){
    if(f.options) return esc(f.options.join(" / "));
    if(f.pattern) return "نمط: "+esc(f.pattern);
    if(f.type==="int") return "رقم ≥ 0";
    return "نص";
  }
  function toggleImport(){
    var p=document.getElementById("importpanel"); if(p.innerHTML){ p.innerHTML=""; return; }
    var ap=document.getElementById("addpanel"); if(ap) ap.innerHTML="";
    p.innerHTML='<div class="panel"><div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>جارٍ التحضير…</p></div></div>';
    api("stochops_nonprofit.imports.get_import_schema",{doctype:C.doctype}).then(function(res){
      if(!res.ok || !res.j.message){ p.innerHTML='<div class="panel"><div class="ds-alert ds-alert--err"><span class="ico">⚠</span><div class="bd"><b>تعذّر</b>'+esc(errMsg(res))+'</div></div></div>'; return; }
      IMP=res.j.message; renderImport(p);
    });
  }
  function renderImport(p){
    var cols=IMP.fields.map(function(f){
      return '<tr><td>'+esc(f.label)+(f.required?' <span class="req">*</span>':'')+'</td><td class="muted">'+fieldHint(f)+'</td></tr>';
    }).join("");
    p.innerHTML='<div class="panel">'+
      '<h3 style="color:#fff;margin-bottom:6px">استيراد '+esc(IMP.label)+' من ملف</h3>'+
      '<p class="muted" style="margin-bottom:10px">نزّل القالب، املأه في Excel، ثم ارفعه أو الصق محتواه. العناوين تطابق أسماء الأعمدة أدناه. الحدّ الأقصى '+esc(String(IMP.max_rows))+' صفّاً للدفعة. كل سجلّ يُربط بجمعيتك تلقائياً.</p>'+
      '<div class="nl-imp-cols"><table class="ds-table"><thead><tr><th>العمود</th><th>المسموح</th></tr></thead><tbody>'+cols+'</tbody></table></div>'+
      '<div style="display:flex;gap:10px;flex-wrap:wrap;margin:12px 0">'+
        '<button class="ds-btn ds-btn--secondary" id="impTpl" type="button">تنزيل قالب CSV</button>'+
        '<label class="ds-btn ds-btn--secondary" style="cursor:pointer">رفع ملف CSV<input type="file" id="impFile" accept=".csv,text/csv" style="display:none"></label>'+
      '</div>'+
      '<label style="display:block;font-size:13px;color:var(--nl-text,#e2e8f0);margin:4px 0 6px">أو الصق محتوى CSV هنا:</label>'+
      '<textarea class="ds-input" id="impText" rows="5" style="width:100%;font-family:monospace;direction:ltr" placeholder="name,phone,..."></textarea>'+
      '<div id="impmsg"></div>'+
      '<div style="margin-top:10px;display:flex;gap:10px"><button class="ds-btn ds-btn--primary" id="impParse" type="button">تحليل ومعاينة</button>'+
      '<button class="ds-btn ds-btn--secondary" id="impCancel" type="button">إغلاق</button></div>'+
      '<div id="imppreview"></div></div>';
    document.getElementById("impTpl").onclick=function(){
      var header=IMP.fields.map(function(f){ return csvCell(f.field); }).join(",");
      download(C.doctype.toLowerCase()+"_template.csv","﻿"+header+"\r\n");
    };
    document.getElementById("impFile").onchange=function(e){
      var f=e.target.files&&e.target.files[0]; if(!f) return;
      var rd=new FileReader(); rd.onload=function(){ document.getElementById("impText").value=rd.result; parseImport(); }; rd.readAsText(f,"utf-8");
    };
    document.getElementById("impParse").onclick=parseImport;
    document.getElementById("impCancel").onclick=toggleImport;
  }
  function parseImport(){
    var msg=document.getElementById("impmsg"), prev=document.getElementById("imppreview");
    prev.innerHTML=""; msg.innerHTML="";
    var raw=document.getElementById("impText").value||"";
    var grid=parseCSV(raw);
    if(grid.length<2){ showAlert(msg,"الملف يحتاج صفّ عناوين وصفّ بيانات واحداً على الأقل.",true); return; }
    var headers=grid[0].map(norm);
    // طابق كل عمود بحقلٍ (بالاسم البرمجي أو التسمية العربية)
    var colField=headers.map(function(h){
      for(var i=0;i<IMP.fields.length;i++){ var f=IMP.fields[i];
        if(h===norm(f.field)||h===norm(f.label)) return f.field;
      } return null;
    });
    var matched=colField.filter(Boolean);
    var missingReq=IMP.fields.filter(function(f){ return f.required && matched.indexOf(f.field)<0; });
    if(!matched.length){ showAlert(msg,"لم يُطابَق أي عمود. استخدم القالب (عناوين الأعمدة بالأسماء البرمجية).",true); return; }
    if(missingReq.length){ showAlert(msg,"عمود مطلوب مفقود: "+missingReq.map(function(f){return f.label;}).join("، "),true); return; }
    var rows=[];
    for(var r=1;r<grid.length;r++){ var obj={}, line=grid[r];
      for(var c=0;c<colField.length;c++){ if(colField[c]) obj[colField[c]]=(line[c]==null?"":line[c]).trim(); }
      rows.push(obj);
    }
    if(rows.length>IMP.max_rows){ showAlert(msg,"عدد الصفوف ("+rows.length+") يتجاوز الحدّ ("+IMP.max_rows+"). قسّم الملف.",true); return; }
    IMP._rows=rows;
    // معاينة أول 5 صفوف
    var show=rows.slice(0,5);
    var th=IMP.fields.filter(function(f){ return matched.indexOf(f.field)>=0; });
    var head=th.map(function(f){ return '<th>'+esc(f.label)+'</th>'; }).join("");
    var body=show.map(function(o){ return '<tr>'+th.map(function(f){ return '<td>'+esc(o[f.field]||"—")+'</td>'; }).join("")+'</tr>'; }).join("");
    prev.innerHTML='<div class="nl-note" style="margin-top:12px">جاهز للاستيراد: <b>'+rows.length+'</b> صفّاً. معاينة أول '+show.length+':</div>'+
      '<div class="ds-table-wrap"><table class="ds-table"><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></div>'+
      '<button class="ds-btn ds-btn--primary" id="impRun" type="button" style="margin-top:10px">استيراد '+rows.length+' سجلّاً</button>';
    document.getElementById("impRun").onclick=runImport;
  }
  function runImport(){
    var msg=document.getElementById("impmsg"), btn=document.getElementById("impRun");
    if(!IMP||!IMP._rows||!IMP._rows.length){ showAlert(msg,"لا توجد بيانات.",true); return; }
    btn.disabled=true; btn.textContent="جارٍ الاستيراد…"; msg.innerHTML="";
    api("stochops_nonprofit.imports.bulk_import",{doctype:C.doctype,rows:JSON.stringify(IMP._rows)},true).then(function(res){
      btn.disabled=false; btn.textContent="استيراد";
      if(!res.ok || !res.j.message){ showAlert(msg,errMsg(res),true); return; }
      var m=res.j.message, prev=document.getElementById("imppreview");
      var failHtml="";
      if(m.failed && m.failed.length){
        failHtml='<div class="nl-note" style="margin-top:10px;border-color:var(--nl-red,#f87171)">تعذّر استيراد '+m.failed.length+' صفّاً:</div>'+
          '<div class="ds-table-wrap"><table class="ds-table"><thead><tr><th>الصفّ</th><th>السبب</th></tr></thead><tbody>'+
          m.failed.map(function(f){ return '<tr><td>'+esc(String(f.row))+'</td><td>'+esc(f.error)+'</td></tr>'; }).join("")+'</tbody></table></div>';
      }
      prev.innerHTML='<div class="ds-alert ds-alert--ok"><span class="ico">✓</span><div class="bd"><b>اكتمل</b>استُورد '+m.inserted+' من '+m.total+' صفّاً.</div></div>'+failHtml;
      state.page=1; load();
    });
  }
  window.__nosToggleImport=toggleImport;

  render();
})();
