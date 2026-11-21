/* Statistiques de visite GoatCounter (sans cookie) : événements comptés en plus des pages vues.
   Sans code GoatCounter configuré (config/site.yml), count.js n'est pas chargé et rien n'est envoyé. */
(function(){
  function stat(name){
    try{var g=window.goatcounter;if(g&&g.count)g.count({path:name,title:name+" ("+document.documentElement.lang+")",event:true})}catch(e){}
  }
  window.chStat=stat; // utilisé par site.js à l'envoi des formulaires
  /* Clics WhatsApp, sur toutes les pages. Écoute en phase de remontée : le lien de l'assistant fixe son numéro
     (selon la langue) dans son propre gestionnaire, juste avant. */
  document.addEventListener("click",function(e){
    var a=e.target.closest&&e.target.closest('a[href*="wa.me/"]');if(!a||a.id==="cbBtn")return; // la bulle d'aide ouvre un menu (lien WhatsApp seulement sans JavaScript)
    stat(a.href.indexOf("wa.me/{{wa_afrique_num}}")>-1?"whatsapp-afrique":"whatsapp-europe");
  });
  /* Clics « Demander un devis » : tout lien vers la page Devis, quelle que soit la langue (adresses de content/site.json) */
  var DEVIS="{{chemins_devis}}".split(",");
  document.addEventListener("click",function(e){
    var a=e.target.closest&&e.target.closest("a[href]");if(!a)return;
    var u;try{u=new URL(a.href,location.href)}catch(x){return}
    if(u.origin===location.origin&&DEVIS.indexOf(u.pathname)>-1)stat("clic-devis");
  });
})();
