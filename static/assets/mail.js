/* Adresse email : écrite « contact(at)chanceleno.com » dans le code des pages pour échapper aux robots
   collecteurs de spam, puis reconstituée au chargement (texte normal et lien mailto cliquable). */
(function(){
  var MAIL=["contact","chanceleno.com"].join("@"),TOKEN=/contact\(at\)chanceleno\.com/g;
  function unmask(s){return String(s).replace(TOKEN,MAIL)}
  function reveal(root){
    root.querySelectorAll("a[data-mail]").forEach(function(a){a.href="mailto:"+MAIL});
    var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),n;
    while((n=w.nextNode()))if(n.nodeValue.indexOf("(at)")>-1)n.nodeValue=unmask(n.nodeValue);
  }
  window.chMail={unmask:unmask,reveal:reveal};
  /* Après tous les scripts de la page : site.js doit d'abord lire les textes d'origine pour la traduction. */
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",function(){reveal(document.body)});else reveal(document.body);
})();
