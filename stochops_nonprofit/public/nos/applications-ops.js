/* لوحة المشغّل لطلبات الاستفادة (P2) — لمشغّل المنصّة فقط (System Manager / Stochops Admin).
   قائمة حسب المرحلة + تحقّق + تقييم استرشادي + قرار موثّق. الخادم يفرض الحالات والشروط. */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "", USER = window.NOS_USER || "Guest";
  var OPER_ROLES = ["System Manager", "Stochops Admin"];
  var FLOW = {
    "Submitted": ["Under Review", "Information Required", "Rejected"],
    "Under Review": ["Information Required", "Waitlisted", "Approved", "Rejected"],
    "Information Required": ["Under Review", "Waitlisted", "Rejected"],
    "Waitlisted": ["Under Review", "Approved", "Rejected"],
    "Approved": [], "Rejected": []
  };
  var AR = { "Submitted": "مُقدَّم", "Under Review": "قيد المراجعة", "Information Required": "يحتاج استكمالاً",
    "Waitlisted": "قائمة انتظار", "Approved": "مقبول", "Rejected": "مرفوض" };
  var BADGE = { "Approved": "ok", "Rejected": "danger", "Information Required": "warn", "Waitlisted": "muted", "Submitted": "muted", "Under Review": "warn" };
  var SCORES = [
    ["score_need", "الاحتياج (0-25)", 25], ["score_readiness", "الجاهزية (0-20)", 20], ["score_scale", "الحجم (0-15)", 15],
    ["score_governance", "الحوكمة (0-20)", 20], ["score_manager", "مسؤول المنصّة (0-10)", 10], ["score_fit", "التوافق (0-10)", 10]
  ];
  var DECISION = { "Approved": "اعتماد", "Rejected": "رفض" };
  var state = { filter: "", name: null };

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args, isPost){
    var opt={ headers:{ "X-Frappe-CSRF-Token":CSRF } }, url="/api/method/"+method;
    if(isPost){ opt.method="POST"; opt.headers["Content-Type"]="application/json"; opt.body=JSON.stringify(args||{}); }
    else if(args){ url+="?"+new URLSearchParams(args).toString(); }
    return fetch(url,opt).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }
  function errMsg(res){ try{ var sm=JSON.parse(res.j._server_messages||"[]"); if(sm.length) return (JSON.parse(sm[0]).message||"").replace(/<[^>]+>/g,""); }catch(e){} return "تعذّر تنفيذ العملية."; }
  function badge(s){ return '<span class="ds-badge ds-badge--'+(BADGE[s]||"muted")+'">'+esc(AR[s]||s)+'</span>'; }
  function toast(msg,isErr){ var t=document.createElement("div"); t.className="ds-toast "+(isErr?"ds-toast--err":"ds-toast--ok"); t.textContent=msg; if(isErr){ var x=document.createElement("span"); x.className="x"; x.textContent="✕"; t.appendChild(x); } document.body.appendChild(t);
    if(isErr){ t.onclick=function(){ t.remove(); }; } else { setTimeout(function(){t.remove();},3000); } }
  function showAlert(box,msg,isErr){ if(!box) return; box.innerHTML='<div class="ds-alert ds-alert--'+(isErr?"err":"ok")+'"><span class="ico">'+(isErr?"⚠":"✓")+'</span>'+
    '<div class="bd"><b>'+(isErr?"تعذّر تنفيذ العملية":"تم")+'</b>'+esc(msg)+'</div><button type="button" class="x" aria-label="إغلاق">✕</button></div>';
    var x=box.querySelector(".x"); if(x) x.onclick=function(){ box.innerHTML=""; }; }

  if(!USER || USER==="Guest"){
    app.innerHTML='<div class="ds-state"><h3>لوحة المشغّل</h3><p>يجب تسجيل الدخول بحساب مشغّل المنصّة.</p><a class="ds-btn ds-btn--primary" href="/login?redirect-to=/nos/applications">تسجيل الدخول</a></div>';
    return;
  }

  function start(){
    api("stochops_nonprofit.nav.get_my_context").then(function(res){
      var roles=(res.ok && res.j.message && res.j.message.roles) || [];
      if(!OPER_ROLES.some(function(r){ return roles.indexOf(r)>=0; })){
        app.innerHTML='<div class="ds-state"><h3>للمشغّل فقط</h3><p>هذه اللوحة مخصّصة لمشغّل المنصّة (STOCHOPS).</p><a class="ds-btn ds-btn--secondary" href="/nos/console">لوحة الجمعية</a></div>';
        return;
      }
      list();
    });
  }

  function list(){
    var tabs=[["","الكل"],["Submitted",""],["Under Review",""],["Information Required",""],["Waitlisted",""],["Approved",""],["Rejected",""]]
      .map(function(t){ var k=t[0], lbl=t[1]||AR[k]; return '<button class="optab'+(state.filter===k?" active":"")+'" data-f="'+esc(k)+'">'+esc(lbl)+'</button>'; }).join("");
    app.innerHTML='<h1>طلبات الاستفادة</h1><p class="muted">القبول انتقائي — التقديم لا يُنشئ حساباً. الترخيص شرط إلزامي مستقل لا تعوّضه الدرجات.</p>'+
      '<div class="optabs">'+tabs+'</div><div class="panel" id="listpanel"><div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>…</p></div></div>';
    document.querySelectorAll("[data-f]").forEach(function(b){ b.onclick=function(){ state.filter=b.getAttribute("data-f"); list(); }; });
    var filters = state.filter ? JSON.stringify([["status","=",state.filter]]) : "[]";
    api("frappe.client.get_list",{doctype:"Association Application", filters:filters,
      fields:JSON.stringify(["name","association_name","license_number","status","score_total","submitted_on"]),
      order_by:"submitted_on desc", limit_page_length:100}).then(function(res){
      var lp=document.getElementById("listpanel");
      if(!res.ok){ lp.innerHTML='<div class="ds-state ds-state--error"><p>'+esc(errMsg(res))+'</p></div>'; return; }
      var rows=res.j.message||[];
      if(!rows.length){ lp.innerHTML='<div class="ds-state ds-state--empty"><p>لا طلبات في هذه المرحلة.</p></div>'; return; }
      lp.innerHTML='<div class="ds-table-wrap"><table class="ds-table"><thead><tr><th>الطلب</th><th>الجمعية</th><th>الترخيص</th><th>الدرجة</th><th>الحالة</th><th></th></tr></thead><tbody>'+
        rows.map(function(r){ return '<tr class="nl-row" data-n="'+esc(r.name)+'"><td class="nl-mono">'+esc(r.name)+'</td><td>'+esc(r.association_name)+'</td><td>'+esc(r.license_number||"—")+'</td><td class="nl-mono">'+(r.score_total||0)+'</td><td>'+badge(r.status)+'</td><td><span class="ds-btn ds-btn--secondary ds-btn--sm">فتح</span></td></tr>'; }).join("")+
        '</tbody></table></div>';
      document.querySelectorAll(".nl-row").forEach(function(tr){ tr.style.cursor="pointer"; tr.onclick=function(){ state.name=tr.getAttribute("data-n"); detail(); }; });
    });
  }

  function row(label,val){ return '<div><div class="nd-k">'+esc(label)+'</div><div class="nd-v">'+esc(val==null||val===""?"—":String(val))+'</div></div>'; }

  function detail(){
    app.innerHTML='<div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>…</p></div>';
    api("frappe.client.get",{doctype:"Association Application", name:state.name}).then(function(res){
      if(!res.ok){ app.innerHTML='<div class="ds-state ds-state--error"><p>'+esc(errMsg(res))+'</p></div>'; return; }
      var d=res.j.message||{};
      var info='<div class="nd-kv">'+
        row("الجمعية",d.association_name)+row("الترخيص",d.license_number)+row("الجهة المشرفة",d.supervisory_authority)+
        row("المنطقة/المدينة",(d.region||"")+" "+(d.city||""))+row("البريد الرسمي",d.official_email)+row("الهاتف",d.phone)+
        row("مقدّم الطلب",(d.applicant_name||"")+" — "+(d.applicant_title||""))+row("المسؤول المقترح",(d.proposed_admin_name||"")+" — "+(d.proposed_admin_email||""))+
        row("حجم العمل",d.work_size)+row("الأنظمة الحالية",d.current_systems)+row("التحديات",d.challenges)+row("الاحتياج",d.needs)+
      '</div>';
      var verify='<div class="chkrow">'+
        chk("email_verified","تحقّق البريد",d.email_verified)+chk("license_verified","تحقّق الترخيص",d.license_verified)+chk("representative_authorized","تحقّق التفويض",d.representative_authorized)+
        '</div><button class="ds-btn ds-btn--secondary ds-btn--sm" id="savev">حفظ التحقّق</button>';
      var scores='<div class="scoregrid">'+SCORES.map(function(s){ return '<div class="fld"><label>'+esc(s[1])+'</label><input id="s_'+s[0]+'" type="number" min="0" max="'+s[2]+'" value="'+(d[s[0]]||0)+'"></div>'; }).join("")+
        '<div class="fld" style="grid-column:1 / -1"><label>توصية المُقيّم</label><input id="s_recommendation" value="'+esc(d.recommendation||"")+'"></div></div>'+
        '<p class="muted" style="margin:8px 0">الإجمالي الحالي: <b>'+(d.score_total||0)+'</b> / 100 (استرشادي).</p>'+
        '<button class="ds-btn ds-btn--secondary ds-btn--sm" id="saves">حفظ التقييم</button>';
      var acts=(FLOW[d.status]||[]).map(function(to){
        var v=(to==="Approved")?"primary":(to==="Rejected"?"warning":"secondary");
        return '<button class="ds-btn ds-btn--'+v+'" data-to="'+esc(to)+'">'+(DECISION[to]||("تحويل إلى "+(AR[to]||to)))+'</button>';
      }).join("");
      app.innerHTML='<div class="nd-crumb"><a href="#" id="back">طلبات الاستفادة</a> &rsaquo; '+esc(d.name)+'</div>'+
        '<h1>'+esc(d.association_name||d.name)+'</h1><p class="muted">'+esc(d.name)+' — '+badge(d.status)+(d.submitted_on?' · '+esc(d.submitted_on):'')+'</p>'+
        '<div class="panel"><h3>بيانات الطلب</h3>'+info+'</div>'+
        '<div class="panel"><h3>التحقّق (شرط إلزامي مستقل للقبول)</h3>'+verify+'</div>'+
        '<div class="panel"><h3>التقييم الداخلي (استرشادي)</h3>'+scores+'</div>'+
        '<div class="panel"><h3>القرار</h3>'+
          (d.decision_reason?'<p class="muted">آخر مبرّر: '+esc(d.decision_reason)+(d.decided_by?' — '+esc(d.decided_by):'')+(d.decided_on?' · '+esc(d.decided_on):'')+'</p>':'')+
          '<div id="decmsg" class="ds-err"></div>'+
          '<div class="nd-actions">'+(acts||'<span class="muted">حالة نهائية — لا انتقالات.</span>')+'<a class="ds-btn ds-btn--secondary" href="#" id="back2">عودة للقائمة</a></div>'+
          '<div id="decform"></div></div>'+
        '<div class="panel" id="actv"><h3>القبول والتفعيل</h3><div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>…</p></div></div>';
      document.getElementById("back").onclick=function(e){ e.preventDefault(); list(); };
      document.getElementById("back2").onclick=function(e){ e.preventDefault(); list(); };
      document.getElementById("savev").onclick=saveVerify;
      document.getElementById("saves").onclick=saveScores;
      document.querySelectorAll("[data-to]").forEach(function(b){ b.onclick=function(){ decide(b.getAttribute("data-to")); }; });
      loadActivation(d);
    });
  }

  function loadActivation(d){
    var p=document.getElementById("actv"); if(!p) return;
    if(d.status!=="Approved" && d.status!=="Rejected" && d.status!=="Waitlisted"){
      // قبل الاعتماد: لا تفعيل
    }
    api("frappe.client.get_list",{doctype:"Association Approval", filters:JSON.stringify([["application","=",d.name]]),
      fields:JSON.stringify(["name","status","charity","admin_user","acceptance_token"]), order_by:"creation desc", limit_page_length:1}).then(function(res){
      var appr=(res.ok && res.j.message && res.j.message[0]) || null;
      var html='<h3>القبول والتفعيل</h3>';
      if(!appr){
        if(d.status!=="Approved"){ html+='<p class="muted">يُتاح إصدار رابط القبول والتفعيل بعد اعتماد الطلب.</p>'; }
        else { html+='<p class="muted">الطلب معتمَد. يتطلّب الإصدار نشر «شروط الاستخدام» و«DPA» في المركز القانوني.</p>'+
          '<div id="am" class="ds-err"></div><button class="ds-btn ds-btn--primary" id="issue">إصدار رابط القبول والتفعيل</button>'; }
      } else {
        var stmap={ "Awaiting Acceptance":"بانتظار قبول الممثّل", "Accepted":"قُبِلت الاتفاقيات", "Activated":"مُفعّلة", "Revoked":"ملغاة" };
        html+='<div class="nd-kv"><div><div class="nd-k">قرار الاعتماد</div><div class="nd-v">'+esc(appr.name)+'</div></div>'+
          '<div><div class="nd-k">الحالة</div><div class="nd-v">'+esc(stmap[appr.status]||appr.status)+'</div></div>'+
          '<div><div class="nd-k">الجمعية (مساحة)</div><div class="nd-v">'+esc(appr.charity||"—")+'</div></div>'+
          (appr.admin_user?'<div><div class="nd-k">حساب المدير</div><div class="nd-v">'+esc(appr.admin_user)+'</div></div>':'')+'</div>'+
          '<div id="am" class="ds-err"></div><div class="nd-actions">';
        if(appr.status==="Accepted"){ html+='<button class="ds-btn ds-btn--primary" id="activate">تفعيل الحساب وإنشاء المدير</button>'; }
        else if(appr.status==="Awaiting Acceptance"){ html+='<span class="muted">بانتظار قبول الممثّل للاتفاقيات عبر الرابط المرسَل.</span>'; }
        else if(appr.status==="Activated"){ html+='<span class="ds-badge ds-badge--ok">مُفعّلة</span>'; }
        html+='</div>';
      }
      p.innerHTML=html;
      var ib=document.getElementById("issue"); if(ib) ib.onclick=function(){ ib.disabled=true; issueActivation(d.name); };
      var ab=document.getElementById("activate"); if(ab) ab.onclick=function(){ ab.disabled=true; activateAccount(appr.name); };
    });
  }
  function issueActivation(appName){
    api("stochops_nonprofit.activation.issue_activation",{application:appName},true).then(function(res){
      if(res.ok){ toast("صدر رابط القبول وأُرسل للممثّل"); detail(); }
      else { var m=document.getElementById("am"); if(m) m.textContent=errMsg(res); var b=document.getElementById("issue"); if(b) b.disabled=false; }
    });
  }
  function activateAccount(apprName){
    api("stochops_nonprofit.activation.activate",{approval:apprName},true).then(function(res){
      if(res.ok){ toast("تم تفعيل الجمعية وإرسال دعوة المدير"); detail(); }
      else { var m=document.getElementById("am"); if(m) m.textContent=errMsg(res); var b=document.getElementById("activate"); if(b) b.disabled=false; }
    });
  }
  function chk(id,label,v){ return '<label><input type="checkbox" id="c_'+id+'"'+(v?" checked":"")+'> '+esc(label)+'</label>'; }

  function saveVerify(){
    var payload={ email_verified:document.getElementById("c_email_verified").checked?1:0,
      license_verified:document.getElementById("c_license_verified").checked?1:0,
      representative_authorized:document.getElementById("c_representative_authorized").checked?1:0 };
    api("frappe.client.set_value",{doctype:"Association Application",name:state.name,fieldname:JSON.stringify(payload)},true).then(function(res){
      if(res.ok){ toast("حُفظ التحقّق"); } else { toast(errMsg(res),true); }
    });
  }
  function saveScores(){
    // تقييد كل درجة ضمن [0, الحدّ الأقصى للمعيار] مع تصحيح الإدخال في الواجهة (ملاحظة #4)
    var payload={}, clamped=false;
    SCORES.forEach(function(s){ var el=document.getElementById("s_"+s[0]); var raw=parseInt(el.value||"0",10); if(isNaN(raw)) raw=0;
      var v=Math.max(0,Math.min(s[2],raw)); if(v!==raw){ clamped=true; el.value=v; } payload[s[0]]=v; });
    payload.recommendation=document.getElementById("s_recommendation").value||"";
    api("frappe.client.set_value",{doctype:"Association Application",name:state.name,fieldname:JSON.stringify(payload)},true).then(function(res){
      if(res.ok){ toast(clamped?"حُفظ التقييم (صُحِّحت درجات تجاوزت الحدّ الأقصى)":"حُفظ التقييم"); detail(); } else { toast(errMsg(res),true); }
    });
  }
  function decide(to){
    var needReason=(to==="Approved"||to==="Rejected");
    var box=document.getElementById("decform");
    if(needReason){
      box.innerHTML='<div class="ds-field" style="margin-top:12px"><label>مبرّر القرار <span class="req">*</span></label><textarea class="ds-input" id="dreason" rows="2"></textarea></div>'+
        '<div id="dm" class="ds-err"></div><div class="nd-actions"><button class="ds-btn ds-btn--primary" id="dok">تأكيد '+esc(DECISION[to])+'</button><button class="ds-btn ds-btn--secondary" id="dcancel">إلغاء</button></div>';
      document.getElementById("dcancel").onclick=function(){ box.innerHTML=""; };
      document.getElementById("dok").onclick=function(){
        var reason=(document.getElementById("dreason").value||"").trim();
        if(!reason){ showAlert(document.getElementById("dm"),"مبرّر القرار مطلوب قبل البتّ.",true); return; }
        this.disabled=true; applyTransition(to, reason, this);
      };
    } else {
      var box2=document.getElementById("decform"); box2.innerHTML='<div id="dm" class="ds-err"></div>';
      applyTransition(to, null, null);
    }
  }
  function applyTransition(to, reason, btn){
    var payload={status:to}; if(reason!=null) payload.decision_reason=reason;
    api("frappe.client.set_value",{doctype:"Association Application",name:state.name,fieldname:JSON.stringify(payload)},true).then(function(res){
      if(res.ok){ toast("تم تحديث الحالة إلى "+(AR[to]||to)); detail(); }
      else { var m=errMsg(res); showAlert(document.getElementById("dm"),m,true); toast(m,true); if(btn) btn.disabled=false; }
    });
  }

  start();
})();
