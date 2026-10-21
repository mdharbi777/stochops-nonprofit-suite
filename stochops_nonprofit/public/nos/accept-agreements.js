/* صفحة قبول الاتفاقيات (P3) للممثّل المخوّل. وثيقتان منفصلتان بمربّعي موافقة مستقلّين غير مؤشّرين
   مسبقاً + إقرار تمثيل. القبول يُنشئ سجلّي قبول إلكتروني (دليل) خادميّاً. */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var CSRF = window.NOS_CSRF || "";
  var token = new URLSearchParams(location.search).get("token") || "";

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args, isPost){
    var opt={ headers:{ "X-Frappe-CSRF-Token":CSRF } }, url="/api/method/"+method;
    if(isPost){ opt.method="POST"; opt.headers["Content-Type"]="application/json"; opt.body=JSON.stringify(args||{}); }
    else if(args){ url+="?"+new URLSearchParams(args).toString(); }
    return fetch(url,opt).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }
  function errMsg(res){ try{ var sm=JSON.parse(res.j._server_messages||"[]"); if(sm.length) return (JSON.parse(sm[0]).message||"").replace(/<[^>]+>/g,""); }catch(e){} return "تعذّر إتمام القبول."; }
  function agr(d){ return '<div class="agr"><h2>'+esc(d.title)+'</h2><div class="v">إصدار '+esc(d.version)+(d.effective_date?' · نفاذ '+esc(d.effective_date):'')+'</div><div class="body">'+(d.content||"")+'</div></div>'; }

  if(!token){ app.innerHTML='<h1>رابط غير صالح</h1><p class="muted">رابط القبول مفقود.</p>'; return; }

  function load(){
    app.innerHTML='<p class="muted">…جارِ التحميل</p>';
    api("stochops_nonprofit.activation.get_acceptance_context",{token:token}).then(function(res){
      if(!res.ok){ app.innerHTML='<h1>تعذّر فتح الرابط</h1><p class="muted">'+esc(errMsg(res))+'</p>'; return; }
      var c=res.j.message;
      app.innerHTML=
        '<h1>قبول الاتفاقيات وتفعيل الجمعية</h1>'+
        '<p class="muted">'+esc(c.association_name||"")+' — يرجى قراءة الاتفاقيتين والموافقة عليهما لإتمام التفعيل.</p>'+
        agr(c.terms)+
        '<label class="chk"><input type="checkbox" id="ck_terms"> أقرّ بأنني اطّلعت على «'+esc(c.terms.title)+'» وأوافق عليها نيابةً عن الجمعية.</label>'+
        agr(c.dpa)+
        '<label class="chk"><input type="checkbox" id="ck_dpa"> أقرّ بأنني اطّلعت على «'+esc(c.dpa.title)+'» وأوافق عليها نيابةً عن الجمعية.</label>'+
        '<div class="fld"><label>اسم الممثّل المخوّل</label><input type="text" id="rep_name" value="'+esc(c.representative_name||"")+'"></div>'+
        '<div class="fld"><label>الصفة الوظيفية</label><input type="text" id="rep_title"></div>'+
        '<label class="chk"><input type="checkbox" id="ck_decl"> أقرّ بأنني مخوّل بتمثيل الجمعية والموافقة على هذه الاتفاقيات.</label>'+
        '<div id="msg" class="msg err"></div>'+
        '<button class="btn" id="accept">تأكيد القبول وإتمام التفعيل</button>';
      document.getElementById("accept").onclick=accept;
    });
  }

  function accept(){
    var m=document.getElementById("msg"); m.textContent="";
    var t=document.getElementById("ck_terms").checked, p=document.getElementById("ck_dpa").checked, decl=document.getElementById("ck_decl").checked;
    var name=(document.getElementById("rep_name").value||"").trim(), title=(document.getElementById("rep_title").value||"").trim();
    if(!t || !p){ m.textContent="يجب الموافقة على الاتفاقيتين كلتيهما."; return; }
    if(!decl){ m.textContent="يجب إقرار تمثيلك للجمعية وتفويضك."; return; }
    if(!name){ m.textContent="اسم الممثّل مطلوب."; return; }
    var btn=document.getElementById("accept"); btn.disabled=true;
    api("stochops_nonprofit.activation.accept_agreements",
      {token:token, accept_terms:1, accept_dpa:1, declaration:1, representative_name:name, representative_title:title}, true).then(function(res){
      btn.disabled=false;
      if(res.ok && res.j.message){
        app.innerHTML='<h1>تم قبول الاتفاقيات</h1>'+
          '<div class="agr"><p>شكراً لك. سُجّل قبولك للاتفاقيتين (بإصدارهما وبصمتهما) كدليل.</p>'+
          '<p style="margin-top:10px">سيُفعّل مشغّل المنصّة حساب جمعيتك، وتصل مديرها دعوة لضبط كلمة المرور — دون إرسال كلمة مرور في البريد.</p></div>';
        window.scrollTo(0,0);
      } else { m.textContent=errMsg(res); }
    });
  }

  load();
})();
