# Règles de travail de GNU Astrolist

- Lire README.md, CONTRIBUTING.md et les documents du domaine modifié.
- Détailler les nouveaux lots dans ROADMAP.md avant leur implémentation. Pour
  les prochains lots, enregistrer le plan dans un commit local avant de coder.
- Les améliorations approuvées après l'audit ECC portent les identifiants
  ECC-A à ECC-I; leurs sous-étapes conservent ce préfixe (exemple : ECC-A.1).
  Quand l'utilisateur demande la prochaine étape, lire leur état dans ROADMAP.md,
  donner le premier lot incomplet dans l'ordre ECC-A à ECC-I et dire explicitement
  « Utiliser ECC pour réaliser ECC-X », avec son objectif. Ne pas recommander
  une étape déjà terminée ni commencer son implémentation sur une simple demande
  d'information. Pour réaliser ces lots, utiliser les méthodes ECC pertinentes
  selon docs/DEVELOPPEMENT_ECC.md. Si ECC n'est pas accessible, le signaler sans
  prétendre l'avoir utilisé. Son usage n'autorise aucune installation ni
  activation de service externe sans instruction correspondante.
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
  Le parcours débutant doit être compréhensible à 10 ans : phrases courtes,
  mots expliqués, étapes numérotées et exemples faciles à copier. Séparer le
  journal technique du guide de démarrage.
  Identifier schémas et exemples synthétiques; ne jamais fabriquer de captures.
- Travailler uniquement dans les copies locales selon la consigne actuelle :
  aucun push, PR distante, fusion distante ou réglage GitHub. Utiliser les
  données locales et les outils déjà installés pour les contrôles.
- Ajouter aux nouveaux fichiers Python les avis SPDX GPL-3.0-or-later et le
  titulaire réel. Ne jamais fabriquer une signature DCO ou cryptographique.
- Respecter PRIVACY.md : exemples publics, aucune donnée privée ni secret.
- Le disque et les archives Seestar sont strictement sources en lecture seule :
  aucune écriture, modification d'attributs, création de cache ou sortie sur ces
  supports. Les rapports et fichiers temporaires restent dans le projet local.
  Les tests et illustrations utilisent uniquement des archives synthétiques.
- Les branches, commits et tests locaux ne prouvent ni publication distante,
  ni protection effective de main, ni validation scientifique externe.
