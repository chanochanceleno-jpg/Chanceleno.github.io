(function(){
"use strict";
const LANG=document.documentElement.lang; // fr, en ou pt : chaque page est générée dans sa langue (tools/build.py)
const unmask=window.chMail.unmask; // adresse email masquée dans le code (voir assets/mail.js)
const store={get(k){try{return localStorage.getItem(k)}catch(e){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
const reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
/* ===== CONFIGURATION ===== */
const FORM_ENDPOINT="https://formsubmit.co/ajax/dd4826d916be1ff8585a8daf1f96ea91"; // même service que le site en ligne (FormSubmit)

/* ---------- Menu mobile ---------- */
const nav=document.getElementById("nav"),menuBtn=document.getElementById("menuBtn");
menuBtn.addEventListener("click",()=>{const o=nav.classList.toggle("open");menuBtn.setAttribute("aria-expanded",String(o))});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&nav.classList.contains("open")){nav.classList.remove("open");menuBtn.setAttribute("aria-expanded","false");menuBtn.focus()}});
nav.querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>{nav.classList.remove("open");menuBtn.setAttribute("aria-expanded","false")}));

/* ---------- Langue : le sélecteur FR / EN / PT mémorise le choix (voir assets/redirect.js) ---------- */
document.querySelectorAll(".lang a[data-lang]").forEach(a=>a.addEventListener("click",()=>store.set("ch_lang",a.dataset.lang)));

/* ---------- Préselections passées dans l'adresse (?s=, ?t=, ?a=1, ?e=1) ---------- */
const params=new URLSearchParams(location.search);
const $id=id=>document.getElementById(id);
if($id("r-sec")&&params.has("s"))$id("r-sec").value=params.get("s");
if($id("r-type")&&params.has("t"))$id("r-type").value=params.get("t");
if($id("p-type")){const sel=$id("p-type"),pick=w=>[...sel.options].forEach((o,i)=>{if((o.dataset.fr||o.text).indexOf(w)===0)sel.selectedIndex=i});
  if(params.has("a"))pick("Apporteur");if(params.has("e"))pick("Export")}

/* ---------- Onglets des portails DEMO ---------- */
if(document.getElementById("tab-cli")){
function selectTab(k){
  ["cli","sup"].forEach(x=>{const t=document.getElementById("tab-"+x),p=document.getElementById("pan-"+x);const on=x===k;t.setAttribute("aria-selected",on);t.tabIndex=on?0:-1;p.hidden=!on});
}
document.getElementById("tab-cli").addEventListener("click",()=>selectTab("cli"));
document.getElementById("tab-sup").addEventListener("click",()=>selectTab("sup"));
document.querySelector(".tabs").addEventListener("keydown",e=>{if(e.key==="ArrowRight"||e.key==="ArrowLeft"){const cur=document.getElementById("tab-cli").getAttribute("aria-selected")==="true"?"cli":"sup";const n=cur==="cli"?"sup":"cli";selectTab(n);document.getElementById("tab-"+n).focus()}});
selectTab(params.get("t")==="sup"?"sup":"cli");
}

/* ---------- Globe (rotation complète + points qui descendent sur les villes) ---------- */
(function globe(){
  const svg=document.getElementById("globe"),NS="http://www.w3.org/2000/svg";
  if(!svg)return;
  const cx=260,cy=250,R=200,lat0=10*Math.PI/180;let lon0=0;
  const rad=d=>d*Math.PI/180;
  function proj(lat,lon,h){h=h||0;const f=rad(lat),l=rad(lon);
    const x=Math.cos(f)*Math.sin(l-lon0);
    const y=Math.cos(lat0)*Math.sin(f)-Math.sin(lat0)*Math.cos(f)*Math.cos(l-lon0);
    const z=Math.sin(lat0)*Math.sin(f)+Math.cos(lat0)*Math.cos(f)*Math.cos(l-lon0);
    const k=R*(1+h);return {x:cx+k*x,y:cy-k*y,z,r:k*Math.hypot(x,y)}}
  function el(t,a,parent){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(parent||svg).appendChild(e);return e}
  function line(pts){let d="",pen=false;pts.forEach(p=>{if(p.z>0||p.r>R){d+=(pen?"L":"M")+p.x.toFixed(1)+" "+p.y.toFixed(1);pen=true}else pen=false});return d}
  el("circle",{cx,cy,r:R,class:"limb"});
  const gratEl=el("path",{class:"grat"});const grat=[];
  for(let lo=-180;lo<180;lo+=20){const a=[];for(let la=-90;la<=90;la+=4)a.push([la,lo]);grat.push(a)}
  for(let la=-60;la<=60;la+=20){const a=[];for(let lo=-180;lo<=180;lo+=4)a.push([la,lo]);grat.push(a)}
  // [lat, lon, label, type(0 hub,1 lusophone,2 relais,3 sourcing), dx, dy]
  const C={
    lyon:[45.76,4.84,"Lyon",0,10,-8], lis:[38.72,-9.14,"Lisbonne",1,-62,-6],
    luanda:[-8.84,13.23,"Luanda",1,10,14], pn:[-4.78,11.86,"Pointe-Noire",2,-84,-4], kin:[-4.32,15.31,"Kinshasa",2,10,-5],
    stp:[0.34,6.73,"",1,0,0], maputo:[-25.97,32.57,"Maputo",1,10,4], praia:[14.93,-23.51,"Praia",1,-44,4], bissau:[11.86,-15.6,"",1,0,0],
    sp:[-23.55,-46.63,"São Paulo",1,10,4], dili:[-8.56,125.57,"Dili",1,10,4],
    ham:[53.55,9.99,"",3,0,0], dxb:[25.2,55.27,"Dubaï",3,10,4], sha:[31.23,121.47,"Shanghai",3,10,4], ist:[41.0,28.98,"Istanbul",3,10,-4]};
  function v(p){const f=rad(p[0]),l=rad(p[1]);return [Math.cos(f)*Math.cos(l),Math.cos(f)*Math.sin(l),Math.sin(f)]}
  function arcPts(a,b,alt){const A=v(a),B=v(b);const w=Math.acos(Math.min(1,A[0]*B[0]+A[1]*B[1]+A[2]*B[2]));const out=[];
    for(let i=0;i<=60;i++){const t=i/60;const s1=Math.sin((1-t)*w)/Math.sin(w),s2=Math.sin(t*w)/Math.sin(w);
      const P=[s1*A[0]+s2*B[0],s1*A[1]+s2*B[1],s1*A[2]+s2*B[2]];
      out.push([Math.asin(P[2])*180/Math.PI,Math.atan2(P[1],P[0])*180/Math.PI,alt*Math.sin(Math.PI*t)])}
    return out}
  const defs=[["lyon","luanda",.16,1],["lyon","kin",.12,0],["lyon","pn",.1,0],["lis","luanda",.16,1],["lis","sp",.2,0],["lis","praia",.08,0],["luanda","maputo",.1,0],["sp","luanda",.18,0],["ham","lyon",.04,0],["ist","kin",.13,0],["dxb","maputo",.13,0],["sha","luanda",.3,0],["sha","dili",.1,0],["lyon","bissau",.1,0],["luanda","stp",.05,0]];
  const arcs=defs.map(d=>({pts:arcPts(C[d[0]],C[d[1]],d[2]),base:el("path",{class:"arc"+(d[3]?" main":"")}),glint:el("path",{class:"glint"})}));
  const nodes=Object.keys(C).map(k=>{const c=C[k];const g=el("g",{});const o={c,g,seen:false,drop:-1e9};
    o.trail=el("line",{class:"trail"},g);o.ripple=el("circle",{class:"ripple",r:4},g);
    o.dot=el("circle",{r:c[3]===0?5:(c[3]===3?2.6:3.6),class:"node"+(c[3]<=1&&c[3]!==3?" core":"")},g);
    o.ball=el("circle",{r:3.2,class:"ball"},g);
    if(c[2]){o.t=el("text",{},g);o.t.textContent=c[2]}
    return o});
  const ease=t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
  const bounce=t=>{const n=7.5625,d=2.75;if(t<1/d)return n*t*t;if(t<2/d)return n*(t-=1.5/d)*t+.75;if(t<2.5/d)return n*(t-=2.25/d)*t+.9375;return n*(t-=2.625/d)*t+.984375};
  function render(lonDeg,ms,anim){
    lon0=rad(lonDeg);
    gratEl.setAttribute("d",grat.map(a=>line(a.map(q=>proj(q[0],q[1])))).join(""));
    arcs.forEach((a,i)=>{
      const pr=anim?ease(Math.min(1,Math.max(0,(ms-500-i*140)/1500))):1;
      const n=Math.round(pr*60);
      a.base.setAttribute("d",n>0?line(a.pts.slice(0,n+1).map(q=>proj(q[0],q[1],q[2]))):"");
      if(anim&&pr>=1){const ph=((ms/1000+i*1.37)/6)%1;const fw=Math.round(ph*60);const e=(i%2)?60-fw:fw;const st=(i%2)?e:Math.max(0,e-8),en=(i%2)?Math.min(60,e+8):e;
        a.glint.setAttribute("d",line(a.pts.slice(st,en+1).map(q=>proj(q[0],q[1],q[2]))));a.glint.style.opacity=String(Math.sin(Math.PI*ph))}
      else a.glint.setAttribute("d","")});
    nodes.forEach(o=>{const p=proj(o.c[0],o.c[1]);const vis=p.z>0.12;
      if(!vis){o.g.style.display="none";o.seen=false;return}
      o.g.style.display="";
      if(anim&&!o.seen){o.seen=true;o.drop=ms}
      const dt=anim?(ms-o.drop)/900:2;
      const land=Math.min(1,Math.max(0,dt));const fall=bounce(land);
      const by=p.y-34*(1-fall);
      o.ball.setAttribute("cx",p.x);o.ball.setAttribute("cy",by);o.ball.style.opacity=land<1?String(Math.min(1,land*3)):"0";
      o.trail.setAttribute("x1",p.x);o.trail.setAttribute("x2",p.x);o.trail.setAttribute("y1",by-14);o.trail.setAttribute("y2",by);
      o.trail.style.opacity=land<1?String(.8*(1-land)):"0";
      o.dot.setAttribute("cx",p.x);o.dot.setAttribute("cy",p.y);o.dot.style.opacity=land>=.6?"1":"0";
      const rp=Math.min(1,Math.max(0,(dt-1)/0.9));
      o.ripple.setAttribute("cx",p.x);o.ripple.setAttribute("cy",p.y);o.ripple.setAttribute("r",(4+16*rp).toFixed(1));o.ripple.style.opacity=(rp>0&&rp<1)?String(.8*(1-rp)):"0";
      if(o.t){o.t.setAttribute("x",p.x+o.c[4]);o.t.setAttribute("y",p.y+o.c[5]);
        const edge=Math.min(1,(p.z-0.12)/0.25);o.t.style.opacity=String(Math.max(0,Math.min(1,(dt-.4)*2))*edge)}});
  }
  const btn=document.getElementById("gPause");
  if(reduce){render(15,0,false);if(btn)btn.hidden=true;return}
  let running=true,visible=true,elapsed=0,last=null;
  const START=-25, PERIOD=70000; // un tour complet en 70 s, départ centré Atlantique / Afrique
  function frame(now){
    if(running&&visible&&!document.hidden){if(last!==null)elapsed+=Math.min(64,now-last);last=now;
      render(START+360*elapsed/PERIOD+40,elapsed,true)}else last=null;
    requestAnimationFrame(frame)}
  if("IntersectionObserver" in window){new IntersectionObserver(es=>{visible=es[0].isIntersecting}).observe(svg)}
  if(btn)btn.addEventListener("click",()=>{running=!running;btn.setAttribute("aria-pressed",String(!running));btn.textContent=window.__t(running?"Mettre l'animation en pause":"Relancer l'animation")});
  render(15,0,true);requestAnimationFrame(frame);
})();

/* ---------- Files & extraction demo ---------- */
const files=[];const list=document.getElementById("fileList");
if(list){
function renderFiles(){list.innerHTML=files.map((f,i)=>`<li><span>${f.name.replace(/[<>&]/g,"")} <span class="muted">(${Math.max(1,Math.round(f.size/1024))} Ko)</span></span><button type="button" data-rm="${i}" aria-label="${window.__t("Retirer")} ${f.name.replace(/"/g,"")}">${window.__t("Retirer")}</button></li>`).join("")}
function addFiles(fl){for(const f of fl){if(f.size>10*1024*1024){alert("« "+f.name+" » "+window.__t("dépasse 10 Mo. Compressez-le ou envoyez-le à contact(at)chanceleno.com."));continue}if(files.reduce((n,x)=>n+x.size,0)+f.size>10*1024*1024){alert("« "+f.name+" » "+window.__t("ne peut pas être ajouté : la limite est de 10 Mo au total. Envoyez-le à contact(at)chanceleno.com."));continue}files.push(f)}renderFiles()}
document.getElementById("r-files").addEventListener("change",e=>{addFiles(e.target.files);e.target.value=""});
document.getElementById("r-cam").addEventListener("change",e=>{addFiles(e.target.files);e.target.value=""});
document.getElementById("r-photos").addEventListener("change",e=>{addFiles(e.target.files);e.target.value=""});
list.addEventListener("click",e=>{const b=e.target.closest("[data-rm]");if(b){files.splice(+b.dataset.rm,1);renderFiles()}});
const drop=document.getElementById("drop");
["dragover","dragenter"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.style.borderColor="var(--copper)"}));
["dragleave","drop"].forEach(ev=>drop.addEventListener(ev,e=>{e.preventDefault();drop.style.borderColor=""}));
drop.addEventListener("drop",e=>addFiles(e.dataTransfer.files));
}

/* ---------- Forms ---------- */
const emailOk=v=>/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
/* Devis, fournisseur, partenaire : envoi classique (multipart) vers FormSubmit, seul mode qui transmet les pièces
   jointes et l'accusé de réception (_autoresponse, captcha actif). FormSubmit redirige ensuite vers la page de
   remerciement (_next) avec la référence. Le contact reste en AJAX (voir plus bas). */
const FORM_POST=FORM_ENDPOINT.replace("/ajax/","/");
const THANKS={fr:"https://chanceleno.com/merci/",pt:"https://chanceleno.com/pt/obrigado/",en:"https://chanceleno.com/en/thank-you/"};
const ACK={
  fr:(k,ref)=>"Bonjour,\n\nNous avons bien reçu "+{RFQ:"votre demande de devis",SUP:"votre candidature fournisseur",PAR:"votre demande de collaboration",CT:"votre message"}[k]+". Votre référence : "+ref+".\nConservez cette référence. Nous revenons vers vous par email, en général sous 48 heures ouvrées.\n\nCHANCELENO\ncontact(at)chanceleno.com · https://chanceleno.com",
  pt:(k,ref)=>"Olá,\n\nRecebemos "+{RFQ:"o seu pedido de cotação",SUP:"a sua candidatura de fornecedor",PAR:"o seu pedido de colaboração",CT:"a sua mensagem"}[k]+". A sua referência: "+ref+".\nGuarde esta referência. Responderemos por email, geralmente em 48 horas úteis.\n\nCHANCELENO\ncontact(at)chanceleno.com · https://chanceleno.com/pt/",
  en:(k,ref)=>"Hello,\n\nWe have received "+{RFQ:"your quote request",SUP:"your supplier application",PAR:"your collaboration enquiry",CT:"your message"}[k]+". Your reference: "+ref+".\nKeep this reference. We will get back to you by email, usually within 48 business hours.\n\nCHANCELENO\ncontact(at)chanceleno.com · https://chanceleno.com"};
/* Référence CH-XXX-AAAAMMJJ-HHMM, à l'heure de Paris (heure de réception), quel que soit le pays du visiteur. */
function makeRef(code){let p={};try{new Intl.DateTimeFormat("fr-FR",{timeZone:"Europe/Paris",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(new Date()).forEach(x=>{p[x.type]=x.value})}catch(e){const d=new Date(),pad=x=>String(x).padStart(2,"0");p={year:d.getFullYear(),month:pad(d.getMonth()+1),day:pad(d.getDate()),hour:pad(d.getHours()),minute:pad(d.getMinutes())}}return "CH-"+code+"-"+p.year+p.month+p.day+"-"+p.hour+p.minute}
function sendClassic(fd,toSend,ref,kind){
  const l=["pt","en"].includes(document.documentElement.lang)?document.documentElement.lang:"fr";
  const nf=document.createElement("form");nf.method="POST";nf.action=FORM_POST;nf.enctype="multipart/form-data";nf.acceptCharset="UTF-8";nf.hidden=true;
  const add=(k,v)=>{const i=document.createElement("input");i.type="hidden";i.name=k;i.value=v;nf.appendChild(i)};
  for(const [k,v] of fd.entries())if(k!=="_captcha")add(k,v);
  add("_next",THANKS[l]+"?ref="+encodeURIComponent(ref));add("_autoresponse",unmask(ACK[l](kind,ref)));
  if(toSend.length){const fi=document.createElement("input");fi.type="file";fi.name="upload";fi.multiple=true;const dt=new DataTransfer();toSend.forEach(f=>dt.items.add(f));fi.files=dt.files;nf.appendChild(fi)}
  document.body.appendChild(nf);nf.submit()}
/* Retour arrière depuis FormSubmit : réactiver les boutons restés sur « Envoi en cours… ». */
window.addEventListener("pageshow",e=>{if(e.persisted)document.querySelectorAll("form[data-kind] button[type=submit]").forEach(b=>{if(b.dataset.label){b.disabled=false;b.textContent=b.dataset.label}})});
document.querySelectorAll("form[data-kind]").forEach(form=>{
  form.addEventListener("submit",e=>{
    e.preventDefault();
    const st=form.querySelector(".status");st.className="status";
    const hp=form.querySelector(".hp");if(hp&&hp.value)return;
    let first=null;
    form.querySelectorAll("[required]").forEach(inp=>{
      const bad=!inp.value.trim()||(inp.type==="email"&&!emailOk(inp.value.trim()));
      const er=document.getElementById("e-"+inp.id);
      inp.setAttribute("aria-invalid",bad);if(er){er.classList.toggle("show",bad);if(bad)inp.setAttribute("aria-describedby",er.id)}
      if(bad&&!first)first=inp});
    if(first){st.className="status bad show";st.textContent=window.__t("Certains champs sont à compléter. Vos informations saisies sont conservées.");first.focus();return}
    /* statistiques : formulaire valide qui part (voir assets/stats.js) */
    if(window.chStat)window.chStat({RFQ:"envoi-devis",SUP:"envoi-fournisseur",PAR:"envoi-partenaire",CT:"envoi-contact"}[form.dataset.kind]);
    const btn=form.querySelector("button[type=submit]");const label=btn.textContent;btn.dataset.label=label;btn.disabled=true;btn.textContent=window.__t("Envoi en cours…");
    const ref=makeRef(form.dataset.kind==="CT"?"MSG":form.dataset.kind);
    const fd=new FormData();
    const subj={RFQ:"Demande de devis",SUP:"Candidature fournisseur",PAR:"Demande de collaboration",CT:"Message de contact"}[form.dataset.kind];
    fd.append("_captcha","false");fd.append("_honey",hp?hp.value:"");fd.append("_template","table");fd.append("Référence",ref);fd.append("_subject",subj+" "+ref);fd.append("Langue",document.documentElement.lang);
    form.querySelectorAll("input,select,textarea").forEach(el=>{
      if(el.classList.contains("hp")||el.type==="file"||!el.id)return;
      const lab=form.querySelector('label[for="'+el.id+'"]');const key=(el.dataset.key||(lab&&lab.dataset.fr)||(lab?lab.childNodes[0].textContent:el.id)).trim();
      const val=el.type==="checkbox"?(el.checked?"oui":"non"):(el.tagName==="SELECT"?(el.options[el.selectedIndex].dataset.fr||el.options[el.selectedIndex].text):el.value);
      if(el.type==="email")fd.append("email",val);
      fd.append(key,val)});
    const toSend=form.id==="rfqForm"?files:Array.from((form.querySelector("input[type=file]")||{}).files||[]);
    if(toSend.reduce((n,f)=>n+f.size,0)>10*1024*1024){st.className="status bad show";st.textContent=window.__t("Vos fichiers dépassent 10 Mo au total. Retirez-en, ou envoyez-les par email à contact(at)chanceleno.com.");btn.disabled=false;btn.textContent=label;st.setAttribute("tabindex","-1");st.focus();return}
    if(form.dataset.kind!=="CT"){sendClassic(fd,toSend,ref,form.dataset.kind);return}
    toSend.forEach(f=>fd.append("upload",f,f.name));
    const lg=["pt","en"].includes(document.documentElement.lang)?document.documentElement.lang:"fr";fd.append("_autoresponse",unmask(ACK[lg]("CT",ref)));
    /* Contact : FormSubmit (point d'accès AJAX) répond en JSON : seul success:"true" vaut confirmation. */
    const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),30000);
    fetch(FORM_ENDPOINT,{method:"POST",body:fd,headers:{Accept:"application/json"},signal:ctl.signal})
    .then(r=>r.json().catch(()=>({})).then(j=>{if(!r.ok||String(j.success)!=="true")throw new Error(j.message||"HTTP "+r.status)}))
    .then(()=>{
      const what={RFQ:"Votre demande de devis est bien envoyée",SUP:"Votre candidature est bien envoyée. Son statut est « Candidat » jusqu'à l'évaluation",PAR:"Votre demande de collaboration est bien envoyée",CT:"Votre message est bien envoyé"}[form.dataset.kind];
      st.className="status ok show";st.innerHTML=window.__t(what)+". "+window.__t("Référence")+" : <code>"+ref+"</code><br><span class=\"muted\" style=\"font-size:14px\">"+window.__t("Conservez cette référence. Nous revenons vers vous par email, en général sous 48 heures ouvrées.")+"</span>";
      form.querySelectorAll("input:not([type=checkbox]),textarea").forEach(i=>{if(i.type!=="file")i.value=""});
      if(form.id==="rfqForm"){files.length=0;renderFiles()}
    })
    .catch(err=>{
      console.warn("Envoi du formulaire non confirmé :",err);
      st.className="status bad show";st.innerHTML=window.__t("L'envoi n'a pas abouti. Vos informations sont conservées : réessayez, ou écrivez-nous directement à")+" <a data-mail href=\"/#/contact\">contact(at)chanceleno.com</a> "+window.__t("ou sur")+" <a href=\"https://wa.me/33641808499\" target=\"_blank\" rel=\"noopener\">WhatsApp</a>.";window.chMail.reveal(st);
    })
    .finally(()=>{clearTimeout(timer);btn.disabled=false;btn.textContent=label;st.setAttribute("tabindex","-1");st.focus()});
  });
  form.addEventListener("input",e=>{const t=e.target;if(t.getAttribute("aria-invalid")==="true"&&t.value.trim()){t.setAttribute("aria-invalid","false");const er=document.getElementById("e-"+t.id);if(er)er.classList.remove("show")}});
});

/* ---------- Images : logo animé et photo de repli (remplacent les anciens onload/onerror en ligne, interdits par la CSP) ---------- */
document.querySelectorAll(".brand img").forEach(img=>{const ok=()=>img.parentNode.classList.add("has-logo"),ko=()=>img.remove();if(img.complete)(img.naturalWidth?ok:ko)();else{img.addEventListener("load",ok);img.addEventListener("error",ko)}});
document.querySelectorAll("img[data-fallback]").forEach(img=>{const ko=()=>img.parentNode.classList.add("noimg");if(img.complete&&!img.naturalWidth)ko();else img.addEventListener("error",ko)});


/* ---------- Logo : rejouer l'animation au survol ---------- */
const brand=document.querySelector(".brand");let rpl=0;
function replayLogo(){if(reduce||Date.now()-rpl<2500)return;rpl=Date.now();brand.classList.add("replay");void brand.offsetWidth;brand.classList.remove("replay")}
brand.addEventListener("mouseenter",replayLogo);brand.addEventListener("focus",replayLogo);

/* ---------- Assistant guidé (sans service externe) ---------- */
const cbBtn=document.getElementById("cbBtn"),cbPanel=document.getElementById("cbPanel");
const cbClose=()=>{cbPanel.hidden=true;cbBtn.setAttribute("aria-expanded","false")};
cbBtn.addEventListener("click",()=>{const o=cbPanel.hidden;cbPanel.hidden=!o;cbBtn.setAttribute("aria-expanded",String(o))});
cbPanel.querySelectorAll("a").forEach(a=>a.addEventListener("click",cbClose));
document.getElementById("cbWa").addEventListener("click",function(){const pt=LANG==="pt";const msg={fr:"Bonjour CHANCELENO, j’ai une demande :",en:"Hello CHANCELENO, I have a request:",pt:"Olá CHANCELENO, tenho um pedido:"}[LANG]||"";this.href="https://wa.me/"+(pt?"244928424849":"33641808499")+"?text="+encodeURIComponent(msg)});
document.addEventListener("keydown",e=>{if(e.key==="Escape")cbClose()});

/* ---------- WhatsApp ---------- */
const waBtn=document.getElementById("waBtn"),waMenu=document.getElementById("waMenu");
waBtn.addEventListener("click",()=>{const o=waMenu.classList.toggle("open");waBtn.setAttribute("aria-expanded",String(o))});
document.addEventListener("click",e=>{if(!e.target.closest(".wa")){waMenu.classList.remove("open");waBtn.setAttribute("aria-expanded","false")}});

/* ---------- Textes affichés par le script : traductions générées dans assets/strings.js ---------- */
const STR=window.CH_STRINGS||{};
const norm=t=>t.trim().replace(/\s+/g," ");
window.__t=fr=>{if(LANG==="fr")return unmask(fr);const e=STR[norm(fr)];return unmask(e&&e[LANG]?e[LANG]:fr)};

/* ---------- Statistiques (après window.__t, utilisé à l'affichage) : « Ne pas compter mes visites » (page Cookies) ---------- */
/* GoatCounter n'envoie rien quand localStorage « skipgc » vaut « t » (mécanisme prévu par count.js). */
const gcBtn=document.getElementById("gcOptout"),gcState=document.getElementById("gcState");
if(gcBtn&&document.querySelector("script[data-goatcounter]")){
  gcBtn.hidden=false;gcState.hidden=false;
  const skip=()=>store.get("skipgc")==="t";
  const show=()=>{gcBtn.textContent=window.__t(skip()?"Compter à nouveau mes visites":"Ne pas compter mes visites");
    gcState.textContent=window.__t(skip()?"Vos visites ne sont pas comptées sur cet appareil.":"Vos visites sont comptées de façon anonyme.")};
  gcBtn.addEventListener("click",()=>{if(skip()){try{localStorage.removeItem("skipgc")}catch(e){}}else store.set("skipgc","t");show()});
  show();
}
})();
