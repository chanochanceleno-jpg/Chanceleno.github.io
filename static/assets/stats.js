/* Statistiques de visite GoatCounter (sans cookie) : événements comptés en plus des pages vues.
   Sans code GoatCounter configuré (content/site.json), count.js n'est pas chargé et rien n'est envoyé. */
(function(){
  function stat(name){
    try{var g=window.goatcounter;if(g&&g.count)g.count({path:name,title:name+" ("+document.documentElement.lang+")",event:true})}catch(e){}
  }
  window.chStat=stat; // utilisé par site.js à l'envoi des formulaires
  /* Clics WhatsApp, sur toutes les pages. Écoute en phase de remontée : le lien de l'assistant fixe son numéro
     (selon la langue) dans son propre gestionnaire, juste avant. */
  document.addEventListener("click",function(e){
    var a=e.target.closest&&e.target.closest('a[href*="wa.me/"]');if(!a)return;
    stat(a.href.indexOf("wa.me/244")>-1?"whatsapp-afrique":"whatsapp-europe");
  });
})();
