# Rapports TXT et PDF : protéger les fichiers — ECC-A

Le programme affiche le rapport dans le terminal. `--output-txt` en enregistre
une copie UTF-8; `--output-pdf` crée la version mise en page. Le dossier de
destination doit déjà exister et les deux fichiers doivent être distincts.

## Créer un nouveau rapport

Depuis le dossier du projet sur l'ordinateur, créer `local` si nécessaire :

```powershell
New-Item -ItemType Directory -Force local
gnu-astrolist --date 2026-08-15 --time-range 21:00-22:00 --lat 45 --lon 0 --az-min 0 --az-max 360 --min-altitude 20 --objects messier --max-magnitude -20 --offline --output-txt local/soiree.txt --output-pdf local/soiree.pdf
```

Cet exemple produit volontairement une liste vide avec `--max-magnitude -20`.
Enlever ce filtre ou le modifier pour préparer une liste d'observation réelle.
La date est un exemple à remplacer. Les rapports contiennent les résumés même
lorsque la liste est vide.

## Remplacer volontairement un ancien rapport

Par défaut, un fichier existant est refusé avant les mises à jour, la météo et
les calculs. Choisir un nom différent pour garder l'ancien, ou ajouter
`--overwrite` à la commande pour autoriser son remplacement. Cette option
s'applique aux deux sorties demandées; vérifier leurs noms avant de l'utiliser.
Elle n'autorise jamais les collisions et destinations protégées ci-dessous.

Le programme ne reconnaît pas le contenu d'un fichier comme « ancien rapport » :
avec `--overwrite`, tout fichier ordinaire choisi comme sortie et autorisé par
ces contrôles peut être remplacé. Ne pas choisir un autre document personnel.

## Destinations toujours refusées

- Le même fichier pour TXT et PDF, même sous deux chemins différents.
- Une sortie correspondant à une entrée déclarée : `--catalog-config`,
  `--asteroids-file`, `--comets-file`, `--cbat-file`, `--satellite-elements-file`,
  `--satcat-file` ou `--unoosa-file`.
- Les fichiers du paquet du logiciel et le dossier de cache de la commande.
- Les liens symboliques, jonctions ou autres points de réanalyse dans un chemin
  de sortie; les fichiers ayant plusieurs liens physiques; les fichiers spéciaux.
- Les archives Seestar protégées quand `--seestar-path` est fourni : racine
  source et, pour un volume Windows distinct du logiciel, volume entier.

Les collisions tiennent compte des chemins résolus et de l'identité des fichiers.
Les refus sont signalés comme des erreurs de commande; aucun rapport n'est écrit
pour une collision décelée avant traitement. Les ressources et caches actifs
restent des entrées, pas des destinations d'export.

## Écriture atomique de chaque rapport

Le TXT et le PDF sont chacun préparés dans un fichier temporaire voisin de la
destination, puis publiés une fois leur écriture terminée et la destination
revérifiée. Si l'écriture ou la publication échoue, l'ancien fichier concerné
reste intact et le temporaire est nettoyé lorsque le système le permet.

Sans `--overwrite`, la publication refuse également un fichier apparu entre
le contrôle et la publication. Windows utilise un renommage sans remplacement;
POSIX utilise un lien physique suivi du retrait du nom temporaire. Si le système
de fichiers ne permet pas cette opération, l'export échoue sans basculer vers
une écriture destructive.

**Les deux exports ne forment pas une transaction commune.** Le TXT peut réussir
puis le PDF échouer; le TXT terminé reste alors disponible. L'atomicité ne promet
pas non plus une sauvegarde face à une panne matérielle ou à l'arrêt brutal du
processus. Un temporaire peut subsister après un tel arrêt.

Ces contrôles ne remplacent pas une protection matérielle contre un changement
malveillant de chemin pendant les opérations. Le disque Seestar réel n'est
jamais utilisé pour les tests et doit rester en lecture seule.

## API Python

`report_files.validate_report_paths()` vérifie sans écrire les entrées, sorties,
racine Seestar, cache et ressources. `report_files.staged_report()` fournit le
temporaire et publie le rapport selon la même politique. L'API PDF accepte
`overwrite=False`, `input_paths=()` et `protected_roots=()`; les appelants directs
doivent fournir leurs propres entrées et racine Seestar via l'inventaire.
La CLI fournit automatiquement son contexte complet.
