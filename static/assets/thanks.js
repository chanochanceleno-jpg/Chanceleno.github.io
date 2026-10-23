/* Pages de remerciement : affiche la référence de la demande transmise par FormSubmit (?ref=...). */
(function(){
  var ALL={"fr": {"RFQ": "Votre demande de devis est bien envoyée.", "SUP": "Votre candidature est bien envoyée. Son statut est « Candidat » jusqu'à l'évaluation.", "PAR": "Votre demande de collaboration est bien envoyée."}, "en": {"RFQ": "Your quote request has been sent.", "SUP": "Your application has been sent. Its status is “Applicant” until assessment.", "PAR": "Your collaboration enquiry has been sent."}, "pt": {"RFQ": "O seu pedido de cotação foi enviado.", "SUP": "A sua candidatura foi enviada. O seu estado é «Candidato» até à avaliação.", "PAR": "O seu pedido de colaboração foi enviado."}};
  var KINDS=ALL[document.documentElement.lang]||ALL.fr;
  var ref=new URLSearchParams(location.search).get("ref")||"";
  var m=/^CH-(RFQ|SUP|PAR)-\d{8}-\d{4}$/.exec(ref);
  if(m){
    document.getElementById("what").textContent=KINDS[m[1]];
    document.getElementById("ref").textContent=ref;
    document.getElementById("refline").hidden=false;
    document.getElementById("keep").hidden=false;
  }
  document.querySelectorAll(".lang a").forEach(function(a){a.search=location.search});
})();
