/* نموذج طلب الاستفادة العام (P2). لا يطلب بيانات مستفيدين، ولا يُنشئ حساباً.
   كابتشا حسابي + حدّ معدل على الخادم. عند النجاح يعرض رقم الطلب ورمز المتابعة. */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "";
  var captchaToken = "";

  var FIELDS = [
    {name: "association_name", label: "الاسم النظامي للجمعية", req: true},
    {name: "license_number", label: "رقم الترخيص/التسجيل", req: true},
    {name: "supervisory_authority", label: "الجهة المشرفة"},
    {name: "region", label: "المنطقة"},
    {name: "city", label: "المدينة"},
    {name: "official_email", label: "البريد الرسمي", req: true},
    {name: "phone", label: "الهاتف"},
    {name: "website", label: "الموقع الإلكتروني"},
    {name: "applicant_name", label: "اسم مقدّم الطلب", req: true},
    {name: "applicant_title", label: "الصفة الوظيفية"},
    {name: "proposed_admin_name", label: "اسم مسؤول المنصّة المقترح"},
    {name: "proposed_admin_email", label: "بريد المسؤول المقترح"},
    {name: "work_size", label: "حجم العمل التقريبي", type: "select", options: ["", "صغير", "متوسط", "كبير"]},
    {name: "current_systems", label: "الأنظمة الحالية", type: "textarea", full: true},
    {name: "challenges", label: "تحديات الجمعية", type: "textarea", full: true},
    {name: "needs", label: "الاحتياج من وحدات الفاضل", type: "textarea", full: true}
  ];

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args, isPost){
    var opt={ headers:{ "X-Frappe-CSRF-Token":CSRF } }, url="/api/method/"+method;
    if(isPost){ opt.method="POST"; opt.headers["Content-Type"]="application/json"; opt.body=JSON.stringify(args||{}); }
    else if(args){ url+="?"+new URLSearchParams(args).toString(); }
    return fetch(url,opt).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }
  function errMsg(res){ try{ var sm=JSON.parse(res.j._server_messages||"[]"); if(sm.length) return (JSON.parse(sm[0]).message||"").replace(/<[^>]+>/g,""); }catch(e){} return "تعذّر الإرسال، حاول مجدداً."; }

  function fieldHtml(f){
    var inp;
    if(f.type==="select"){ inp='<select id="f_'+f.name+'">'+f.options.map(function(o){return '<option value="'+esc(o)+'">'+(o||"—")+'</option>';}).join("")+'</select>'; }
    else if(f.type==="textarea"){ inp='<textarea id="f_'+f.name+'"></textarea>'; }
    else { inp='<input id="f_'+f.name+'" type="text" autocomplete="off">'; }
    return '<div class="fld'+(f.full?' full':'')+'"><label class="fl">'+esc(f.label)+(f.req?' <span class="req">*</span>':'')+'</label>'+inp+'</div>';
  }

  function render(){
    api("stochops_nonprofit.signup.get_captcha").then(function(res){
      captchaToken = (res.ok && res.j.message && res.j.message.token) || "";
      var q = (res.ok && res.j.message && res.j.message.question) || "؟";
      app.innerHTML =
        '<h1>طلب الاستفادة من الفاضل</h1>'+
        '<p class="muted">منصة الفاضل مجانية للجمعيات المختارة. هذا طلب استفادة يخضع للتدقيق والتقييم والاعتماد — وليس فتح حساب فوري.</p>'+
        '<div class="note">لا تُدخِل أي بيانات مستفيدين أو ملفات حساسة في هذه المرحلة.</div>'+
        '<div class="form-grid">'+FIELDS.map(fieldHtml).join("")+
          '<div class="fld"><label class="fl">تحقّق بشري: كم ناتج '+esc(q)+' <span class="req">*</span></label><input id="f_captcha" type="text" inputmode="numeric" autocomplete="off"></div>'+
        '</div>'+
        '<div id="msg" class="msg err"></div>'+
        '<div style="margin-top:16px"><button class="btn" id="submit">إرسال الطلب</button></div>';
      document.getElementById("submit").onclick = submit;
    });
  }

  function val(n){ var e=document.getElementById("f_"+n); return e?(e.value||"").trim():""; }

  function submit(){
    var m=document.getElementById("msg"); m.textContent="";
    var data={};
    for(var i=0;i<FIELDS.length;i++){
      var f=FIELDS[i], v=val(f.name);
      if(f.req && !v){ m.textContent="الحقل «"+f.label+"» مطلوب."; return; }
      if(v) data[f.name]=v;
    }
    var cap=val("captcha");
    if(!cap){ m.textContent="أجب على سؤال التحقّق."; return; }
    var btn=document.getElementById("submit"); btn.disabled=true;
    api("stochops_nonprofit.applications.submit_application",
      {data:JSON.stringify(data), captcha_token:captchaToken, captcha_answer:cap}, true).then(function(res){
      btn.disabled=false;
      if(res.ok && res.j.message){
        var r=res.j.message;
        app.innerHTML='<h1>تم استلام طلبك</h1>'+
          '<div class="ok-box"><p>شكراً لك. تمّ تسجيل طلب الاستفادة وسيُدقَّق ويُقيَّم من فريق STOCHOPS، ثم تُبلَّغ بالقرار.</p>'+
          '<p style="margin-top:10px">رقم الطلب: <span class="code">'+esc(r.application)+'</span></p>'+
          '<p>رمز المتابعة: <span class="code">'+esc(r.access_code)+'</span></p>'+
          '<p class="muted" style="margin-top:10px">احتفظ بالرقم والرمز لمتابعة الطلب عبر صفحة «متابعة طلب» مع البريد الرسمي.</p>'+
          '<p style="margin-top:12px"><a href="/application-status">متابعة الطلب الآن</a></p></div>';
        window.scrollTo(0,0);
      } else {
        m.textContent=errMsg(res);
      }
    });
  }

  render();
})();
