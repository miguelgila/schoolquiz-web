window.QUIZ = {
  "id": "fixture",
  "title": "Quiz di prova",
  "subtitle": "Domande facili per provare il motore dei quiz",
  "decks": [
    {
      "id": "prova",
      "label": "Prova",
      "questions": [
        {"id": "p-mc-1", "type": "mc", "q": "Quanti giorni ha una settimana?", "options": ["5", "6", "7", "8"], "answer": 2, "why": "Una settimana ha sette giorni, da lunedì a domenica.", "src": "Calendario"},
        {"id": "p-mc-2", "type": "mc", "q": "Qual è la capitale d'Italia?", "options": ["Milano", "Roma", "Napoli"], "answer": 1, "why": "Roma è la capitale d'Italia dal 1871.", "src": "Costituzione italiana"},
        {"id": "p-mc-3", "type": "mc", "q": "Quanto fa 3 × 4?", "options": ["7", "12", "14", "34"], "answer": 1, "why": "3 × 4 = 12.", "src": "Tabelline"},
        {"id": "p-tf-1", "type": "tf", "q": "Il sole sorge a est.", "answer": true, "why": "Per la rotazione della Terra il sole sorge a est e tramonta a ovest.", "src": "Geografia di base"},
        {"id": "p-tf-2", "type": "tf", "q": "Febbraio ha sempre 31 giorni.", "answer": false, "why": "Febbraio ha 28 giorni, 29 negli anni bisestili.", "src": "Calendario"},
        {"id": "p-tf-3", "type": "tf", "q": "L'acqua bolle a 100 °C al livello del mare.", "answer": true, "why": "Alla pressione del livello del mare l'acqua bolle a 100 °C.", "src": "Scienze di base"},
        {"id": "p-match-1", "type": "match", "q": "Abbina ogni numero al suo nome.", "pairs": [["1", "uno"], ["2", "due"], ["3", "tre"], ["4", "quattro"]], "why": "Sono i primi quattro numeri naturali.", "src": "Aritmetica"},
        {"id": "p-match-2", "type": "match", "q": "Abbina ogni animale al suo verso.", "pairs": [["Cane", "abbaia"], ["Gatto", "miagola"], ["Mucca", "muggisce"]], "why": "Ogni animale ha il suo verso tipico.", "src": "Scienze di base"},
        {"id": "p-order-1", "type": "order", "q": "Metti in ordine i giorni della settimana.", "items": ["Lunedì", "Martedì", "Mercoledì", "Giovedì"], "why": "La settimana inizia il lunedì.", "src": "Calendario"},
        {"id": "p-order-2", "type": "order", "q": "Metti in ordine le stagioni a partire dalla primavera.", "items": ["Primavera", "Estate", "Autunno", "Inverno"], "why": "Le stagioni si susseguono in questo ordine.", "src": "Calendario"}
      ]
    }
  ]
};
