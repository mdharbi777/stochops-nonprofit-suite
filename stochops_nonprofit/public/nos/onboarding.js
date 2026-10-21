/* رحلة تهيئة الجمعية (P5) — خطوات مرشدة: الهوية، حدّ الاعتماد المالي، دعوة الفريق.
   تعتمد نقاط خادمية معزولة (مدير الجمعية فقط): accounts.onboarding_status / update_charity_settings
   / invite_account / list_accounts. الخادم مصدر الحقيقة؛ هذه الصفحة واجهة فقط. */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "", USER = window.NOS_USER || "Guest";
  var ROLE_LABELS = {
    "Nonprofit Admin": "مدير الجمعية", "Program Coordinator": "منسّق برامج",
    "Committee Coordinator": "منسّق لجان", "Executive Viewer": "مطّلع تنفيذي"
  };

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args, isPost){
    var opt={ headers:{ "X-Frappe-CSRF-Token":CSRF } }, url="/api/method/"+method;
    if(isPost){ opt.method="POST"; opt.headers["Content-Type"]="application/json"; opt.body=JSON.stringify(args||{}); }
    else if(args){ url+="?"+new URLSearchParams(args).toString(); }
    return fetch(url,opt).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }
  function errMsg(res){ try{ var sm=JSON.parse(res.j._server_messages||"[]"); if(sm.length) return (JSON.parse(sm[0]).message||"").replace(/<[^>]+>/g,""); }catch(e){} return "تعذّر تنفيذ العملية."; }
  function toast(msg,isErr){ var t=document.createElement("div"); t.className="ds-toast "+(isErr?"ds-toast--err":"ds-toast--ok"); t.textContent=msg; document.body.appendChild(t); setTimeout(function(){t.remove();},3000); }

  if(!USER || USER==="Guest"){
    app.innerHTML='<div class="ds-state"><h3>تهيئة الجمعية</h3><p>يجب تسجيل الدخول.</p><a class="ds-btn ds-btn--primary" href="/login?redirect-to=/nos/onboarding">تسجيل الدخول</a></div>';
    return;
  }

  var S = {};

  function load(){
    app.innerHTML='<div class="ds-state ds-state--loading"><div class="ds-spinner"></div><p>جارٍ التحميل…</p></div>';
    api("stochops_nonprofit.accounts.onboarding_status").then(function(res){
      if(!res.ok){
        var m=errMsg(res), np=/صلاحية|permitted|permission/i.test(m);
        app.innerHTML='<div class="ds-state '+(np?'':'ds-state--error')+'"><h3>'+(np?'لمدير الجمعية فقط':'تعذّر التحميل')+'</h3><p>'+esc(m)+'</p><a class="ds-btn ds-btn--secondary" href="/nos/console">لوحة التشغيل</a></div>';
        return;
      }
      S=res.j.message||{};
      render();
    });
  }

  function stepHeader(n, title, done){
    return '<div class="ob-hd"><div class="ob-step"><span class="n'+(done?' done':'')+'">'+n+'</span>'+
      '<h3 style="margin:0">'+esc(title)+'</h3></div>'+
      '<span class="ds-badge ds-badge--'+(done?'ok':'muted')+'">'+(done?'مكتملة':'غير مكتملة')+'</span></div>';
  }

  function render(){
    var pct=Math.round((S.steps_done||0)/(S.steps_total||3)*100);
    var head=
      '<h1>تهيئة الجمعية</h1>'+
      '<p class="muted">'+esc(S.charity_name||S.charity||"")+' — رحلة إعداد أوّلي لمرة واحدة. يمكنك العودة لاحقاً من الإعدادات.</p>'+
      (S.complete
        ? '<div class="ds-state" style="border-color:#22c55e"><h3>اكتملت التهيئة الأساسية</h3><p>ضبطت هوية الجمعية وحدّ الاعتماد المالي. يمكنك دعوة بقية الفريق في أي وقت.</p><a class="ds-btn ds-btn--primary" href="/nos/console">الذهاب إلى لوحة التشغيل</a></div>'
        : '<div class="ob-prog"><i style="width:'+pct+'%"></i></div><p class="muted">أنجزت '+(S.steps_done||0)+' من '+(S.steps_total||3)+' خطوات.</p>');

    var step1=
      '<div class="panel">'+stepHeader(1,"هوية الجمعية", S.identity_done)+
      '<p class="muted" style="margin:6px 0 12px">رقم التسجيل وبريد التواصل الرسمي — تظهر في التقارير الرسمية.</p>'+
      '<div class="ob-grid">'+
        field("reg","رقم التسجيل","text",S.registration_number)+
        field("cemail","بريد التواصل","text",S.contact_email)+
        field("cmobile","جوال التواصل (اختياري)","text",S.contact_mobile)+
      '</div><div id="m1" class="ds-err"></div>'+
      '<div class="ds-field" style="margin-top:10px"><button class="ds-btn ds-btn--primary" id="save1">حفظ الهوية</button></div></div>';

    var step2=
      '<div class="panel">'+stepHeader(2,"حدّ الاعتماد المالي", S.limit_done)+
      '<p class="muted" style="margin:6px 0 12px">أعلى مبلغ يعتمده مدير الجمعية للصرف/الشراء؛ ما يتجاوزه يتطلّب تصعيداً لمشغّل المنصّة (رقابة مالية).</p>'+
      '<div class="ob-grid">'+
        field("limit","حدّ الاعتماد (ريال)","number",S.expense_approval_limit)+
      '</div><div id="m2" class="ds-err"></div>'+
      '<div class="ds-field" style="margin-top:10px"><button class="ds-btn ds-btn--primary" id="save2">حفظ الحدّ</button></div></div>';

    var step3=
      '<div class="panel">'+stepHeader(3,"دعوة الفريق", S.team_done)+
      '<p class="muted" style="margin:6px 0 12px">تُرسل دعوة برابط أحادي ليضبط العضو كلمة مروره بنفسه (حتى '+(S.max_accounts||5)+' حسابات). المستخدم الآن: '+(S.accounts_used||1)+'.</p>'+
      '<div class="ob-grid">'+
        field("iname","اسم العضو","text","")+
        field("iemail","بريد العضو","text","")+
        selectField("irole","الدور",["Program Coordinator","Committee Coordinator","Executive Viewer","Nonprofit Admin"])+
      '</div><div id="m3" class="ds-err"></div>'+
      '<div class="ds-field" style="margin-top:10px"><button class="ds-btn ds-btn--primary" id="save3">إرسال الدعوة</button> '+
      '<a class="ds-btn ds-btn--secondary" href="/nos/accounts">إدارة الحسابات</a></div>'+
      '<div id="acclist" style="margin-top:12px"></div></div>';

    var finish = S.complete ? "" :
      '<div class="panel"><div class="ob-hd"><h3 style="margin:0">إنهاء التهيئة</h3></div>'+
      '<p class="muted" style="margin:6px 0 12px">'+
        (S.can_finish ? 'راجعت الهوية وحدّ الاعتماد؛ يمكنك إنهاء الرحلة الآن (تبقى كل الصفحات متاحة للتعديل لاحقاً).'
                      : 'أكمل هوية الجمعية (الخطوة ١) أولاً لتتمكّن من الإنهاء.')+'</p>'+
      '<div id="mf" class="ds-err"></div>'+
      '<button class="ds-btn ds-btn--primary" id="finish"'+(S.can_finish?'':' disabled')+'>إنهاء التهيئة</button></div>';

    app.innerHTML=head+step1+step2+step3+finish;

    document.getElementById("save1").onclick=saveIdentity;
    document.getElementById("save2").onclick=saveLimit;
    document.getElementById("save3").onclick=invite;
    var fb=document.getElementById("finish"); if(fb) fb.onclick=finishOnboarding;
    loadAccounts();
  }

  function finishOnboarding(){
    var m=document.getElementById("mf"); if(m) m.textContent="";
    var btn=document.getElementById("finish"); btn.disabled=true;
    api("stochops_nonprofit.accounts.complete_onboarding",{},true).then(function(res){
      if(res.ok){ toast("اكتملت التهيئة"); load(); }
      else { btn.disabled=false; if(m) m.textContent=errMsg(res); }
    });
  }

  function field(id,label,type,val){
    return '<div class="ds-field"><label>'+esc(label)+'</label>'+
      '<input class="ds-input" id="f_'+id+'" type="'+(type==="number"?"number":"text")+'"'+(type==="number"?' min="0"':'')+' value="'+esc(val==null?"":val)+'"></div>';
  }
  function selectField(id,label,opts){
    return '<div class="ds-field"><label>'+esc(label)+'</label><select class="ds-select" id="f_'+id+'">'+
      opts.map(function(o){return '<option value="'+esc(o)+'">'+esc(ROLE_LABELS[o]||o)+'</option>';}).join("")+'</select></div>';
  }
  function val(id){ var e=document.getElementById("f_"+id); return e?(e.value||"").trim():""; }

  function saveIdentity(){
    var m=document.getElementById("m1"); m.textContent="";
    var reg=val("reg"), em=val("cemail");
    if(!reg || !em){ m.textContent="رقم التسجيل وبريد التواصل مطلوبان لإكمال هذه الخطوة."; return; }
    var btn=document.getElementById("save1"); btn.disabled=true;
    api("stochops_nonprofit.accounts.update_charity_settings",
      {registration_number:reg, contact_email:em, contact_mobile:val("cmobile")}, true).then(function(res){
      btn.disabled=false;
      if(res.ok){ toast("حُفظت هوية الجمعية"); load(); } else { m.textContent=errMsg(res); }
    });
  }
  function saveLimit(){
    var m=document.getElementById("m2"); m.textContent="";
    var lim=val("limit");
    if(!lim || Number(lim)<=0){ m.textContent="أدخل حدّ اعتماد أكبر من صفر."; return; }
    var btn=document.getElementById("save2"); btn.disabled=true;
    api("stochops_nonprofit.accounts.update_charity_settings",{expense_approval_limit:lim}, true).then(function(res){
      btn.disabled=false;
      if(res.ok){ toast("حُفظ حدّ الاعتماد"); load(); } else { m.textContent=errMsg(res); }
    });
  }
  function invite(){
    var m=document.getElementById("m3"); m.textContent="";
    var name=val("iname"), em=val("iemail"), role=val("irole");
    if(!name || !em){ m.textContent="اسم العضو وبريده مطلوبان."; return; }
    var btn=document.getElementById("save3"); btn.disabled=true;
    api("stochops_nonprofit.accounts.invite_account",{full_name:name, email:em, role:role}, true).then(function(res){
      btn.disabled=false;
      if(res.ok){ toast("أُرسلت الدعوة إلى "+em); load(); } else { m.textContent=errMsg(res); }
    });
  }
  function loadAccounts(){
    api("stochops_nonprofit.accounts.list_accounts").then(function(res){
      var el=document.getElementById("acclist"); if(!el) return;
      if(!res.ok){ el.innerHTML=""; return; }
      var d=res.j.message||{}, accs=d.accounts||[];
      el.innerHTML='<div class="muted" style="margin-bottom:6px">الحسابات الحالية ('+(d.used||accs.length)+'/'+(d.max_accounts||5)+'):</div>'+
        accs.map(function(a){
          return '<div class="ob-acc"><span>'+esc(a.full_name||a.name)+' <span class="muted">— '+esc((a.roles||[]).map(function(r){return ROLE_LABELS[r]||r;}).join("، "))+'</span></span>'+
            '<span class="ds-badge ds-badge--'+(a.enabled?'ok':'muted')+'">'+(a.enabled?'مفعّل':'بانتظار القبول')+'</span></div>';
        }).join("");
    });
  }

  load();
})();
