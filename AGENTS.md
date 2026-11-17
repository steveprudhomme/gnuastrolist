# Règles de travail de GNU Astrolist

- Lire README.md, CONTRIBUTING.md et les documents du domaine modifié.
- Détailler les nouveaux lots dans ROADMAP.md avant leur implémentation. Pour
  les prochains lots, enregistrer le plan dans un commit local avant de coder.
- Documentation en français, interfaces et identifiants Python en anglais.
- Garder les responsabilités distinctes : interface, temps civil, catalogues,
  calcul astronomique, météo et rendu. Préserver les commandes existantes.
- Toute donnée astronomique ajoutée exige une source, une date de récupération,
  une licence et une méthode de reconstruction documentées. Ne pas inventer
  une magnitude, une mesure ni un résultat pour remplir une cellule vide.
- Une magnitude absente vaut None; une autre bande ne devient jamais une valeur V.
- Les tests ordinaires restent déterministes et hors réseau. Tester les cas
  limites et les sorties publiques affectées; exécuter pytest et Ruff.
- Mettre à jour README, CHANGELOG, ROADMAP et docs concernés avec le code.
- Documenter chaque lot dans docs/TUTORIEL.md avec des images versionnées.
  Identifier schémas et exemples synthétiques; ne jamais fabriquer de captures.
- Travailler uniquement dans les copies locales selon la consigne actuelle :
  aucun push, PR distante, fusion distante ou réglage GitHub. Utiliser les
  données locales et les outils déjà installés pour les contrôles.
- Ajouter aux nouveaux fichiers Python les avis SPDX GPL-3.0-or-later et le
  titulaire réel. Ne jamais fabriquer une signature DCO ou cryptographique.
- Respecter PRIVACY.md : exemples publics, aucune donnée privée ni secret.
- Les branches, commits et tests locaux ne prouvent ni publication distante,
  ni protection effective de main, ni validation scientifique externe.
