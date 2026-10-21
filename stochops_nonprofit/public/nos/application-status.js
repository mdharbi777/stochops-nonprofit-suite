/* متابعة حالة طلب الاستفادة (P2). بالرقم + رمز المتابعة + البريد الرسمي. لا تُعرض درجات داخلية. */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var BADGE = { "Approved": "b-ok", "Rejected": "b-no", "Information Required": "b-warn",
    "Waitlisted": "b-wait", "Submitted": "b-wait", "Under Review": "b-wait" };

  function esc(s){ var d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }
  function api(method, args){
    var url="/api/method/"+method; if(args) url+="?"+new URLSearchParams(args).toString();
    return fetch(url).then(function(r){ return r.json().then(function(j){ return {ok:r.ok,j:j}; }); });
  }
  function errMsg(res){ try{ var sm=JSON.parse(res.j._server_messages||"[]"); if(sm.length) return (JSON.parse(sm[0]).message||"").replace(/<[^>]+>/g,""); }catch(e){} return "تعذّر جلب الحالة."; }

  function render(){
    app.innerHTML =
      '<h1>متابعة طلب الاستفادة</h1>'+
      '<p class="muted">أدخل رقم الطلب ورمز المتابعة والبريد الرسمي للجمعية كما قُدِّم.</p>'+
      '<div class="fld"><label class="fl">رقم الطلب</label><input id="f_app" autocomplete="off" placeholder="APP-2026-00001"></div>'+
      '<div class="fld"><label class="fl">رمز المتابعة</label><input id="f_code" autocomplete="off"></div>'+
      '<div class="fld"><label class="fl">البريد الرسمي</label><input id="f_email" autocomplete="off"></div>'+
      '<div id="msg" class="msg err"></div>'+
      '<button class="btn" id="check">عرض الحالة</button>'+
      '<div id="out"></div>';
    document.getElementById("check").onclick = check;
  }
  function val(n){ var e=document.getElementById("f_"+n); return e?(e.value||"").trim():""; }

  function check(){
    var m=document.getElementById("msg"); m.textContent="";
    var out=document.getElementById("out"); out.innerHTML="";
    var a=val("app"), c=val("code"), e=val("email");
    if(!a||!c||!e){ m.textContent="أدخل الحقول الثلاثة."; return; }
    var btn=document.getElementById("check"); btn.disabled=true;
    api("stochops_nonprofit.applications.get_application_status",{application:a, access_code:c, email:e}).then(function(res){
      btn.disabled=false;
      if(!res.ok || !res.j.message){ m.textContent=errMsg(res); return; }
      var d=res.j.message;
      out.innerHTML='<div class="result">'+
        '<p class="muted">'+esc(d.association_name||"")+' — طلب '+esc(d.application)+'</p>'+
        '<p style="margin:8px 0"><span class="badge '+(BADGE[d.status]||"b-wait")+'">'+esc(d.status_label)+'</span></p>'+
        (d.submitted_on?'<p class="muted">تاريخ التقديم: '+esc(d.submitted_on)+'</p>':'')+
        (d.note?'<p style="margin-top:10px">ملاحظة: '+esc(d.note)+'</p>':'')+
        '</div>';
    });
  }

  render();
})();
