# ECC-H — Mesures reproductibles et budgets

Le benchmark compare quatre charges fixes hors réseau. Aucun seuil de temps
n'est imposé à pytest ou à la CI. Les budgets ci-dessous servent à déclencher
une analyse locale après une nouvelle mesure sur une machine comparable.

## Protocole

Exécuter depuis la racine du projet avec l’environnement isolé ECC-D :

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
local/ecc-dev/Scripts/python.exe scripts/benchmark.py --repeat 3 --output local/benchmark-results.json
```

Le script crée un processus neuf pour chaque répétition. Les imports et la
préparation des rapports/inventaires sont exclus du chronomètre. La destination
JSON est contrôlée avant toute mesure : uniquement sous `local/` du projet,
dossier parent existant, sans lien symbolique, jonction ou lien physique
multiple. Aucun remplacement implicite : ajouter `--overwrite` pour remplacer
un JSON existant. La publication finale est atomique; sans cette option, un
fichier créé par un autre processus pendant les mesures est préservé.
La date `measured_on` est l'horodatage UTC réel du lancement, distinct de la
date fixe du scénario astronomique.

Les chargements
des catalogues et des éléments satellitaires sont inclus. Aucun échauffement
applicatif implicite, mais le cache disque du système peut être chaud : ce n'est
pas une mesure de disque froid. Les sockets sont bloquées et les réglages IERS
sont temporaires. Le contexte impose également `iers_degraded_accuracy=warn`,
y compris sous Astropy 6.1, puis restaure les trois réglages après succès ou
erreur. `PYTHONHASHSEED=0` stabilise les ensembles. Les avertissements
de chaque processus sont conservés dans le JSON, sans les masquer.

Trois passages mesurent le temps avec `perf_counter`, sans instrumentation
mémoire. Un quatrième passage mesure séparément le pic d'allocations avec
`tracemalloc`. Son temps, ralenti par l'instrumentation, ne participe pas à la
médiane. Le pic RSS du processus vient de `GetProcessMemoryInfo` sous Windows,
ou `getrusage` sous POSIX : il inclut imports, préparation et allocations natives.
Ce pic n'est pas une mémoire supplémentaire par rapport à un processus vide.
Le pic Python tracé ne couvre pas toutes les allocations natives. Les deux
mesures ont donc des significations différentes.

1. **Catalogues combinés** : Messier, Caldwell, NGC, GCVS, Bayer et Flamsteed,
   toutes magnitudes, dédoublonnage, calcul public de visibilité et enrichissement.
   32 648 objets, 13 instants sur deux heures, seuil d'altitude 85°, 189 retenus.
   Le champ étroit borne le coût de l'enrichissement saisonnier; un champ large
   peut coûter beaucoup plus. Ce scénario ne couvre pas les orbites cométaires
   et astéroïdales.
2. **Satellites** : les 737 éléments embarqués, 41 instants sur 20 min à pas de
   30 s, seuil 0°, 130 retenus. Le contrôle d'âge est volontairement contourné
   pour exercer le moteur numérique sur tout le catalogue. Ce résultat ne
   constitue pas une recommandation d'observation à partir de TLE périmés.
3. **Rapports volumineux** : 1 000 fiches du catalogue combiné, Alt/Az, météo et
   Lune explicitement synthétiques. Rendu TXT et export PDF atomique réels,
   polices comprises : 486 859 octets TXT et 437 123 octets PDF dans cette mesure.
   Aucun nombre de ce scénario n'est une référence astronomique.
4. **Seestar synthétique** : création préalable de 1 000 dossiers et 10 000 faux
   fichiers nommés comme des empilements. Mesure du scanner et de 1 000 recherches
   de statuts; 1 000 noms reconnus. Aucun FITS réel, aucune archive utilisateur,
   aucun chemin source fourni par argument. Tous les fichiers sont créés sous
   `local/benchmark`, puis supprimés par le contexte temporaire. Les tests Seestar
   existants vérifient séparément l'absence d'écriture pendant le scan.

Tous les scénarios emploient Greenwich, le 17 novembre 2026 à 22 h UTC. Les
catalogues sont ceux de la base de planification `a814a49`; le code de production
n'est pas changé par ECC-H. L'empreinte du script et les versions sont dans
[la preuve JSON intégrale](PERFORMANCES_REFERENCE.json).

## Mesures du 17 novembre 2026

Windows 11 (10.0.22631), Intel64 Family 6 Model 183 Stepping 1, Python 3.13.6,
Astropy 7.2.0, NumPy 2.4.0, SGP4 2.25, ReportLab 4.4.7. Mesures séquentielles,
sans les deux suites de compatibilité exécutées ultérieurement. La charge des
autres applications n'est pas contrôlée. MiB signifie 1 048 576 octets.

| Charge | Temps min–max, s | Médiane, s | Pic RSS sans traçage, MiB | Pic Python tracé, MiB |
| --- | ---: | ---: | ---: | ---: |
| Catalogues combinés | 0,673–0,701 | 0,680 | 176,4 | 97,3 |
| Satellites | 1,871–1,902 | 1,875 | 157,0 | 81,5 |
| TXT + PDF, 1 000 fiches | 2,361–2,486 | 2,447 | 124,4 | 29,2 |
| Inventaire, 10 000 fichiers | 0,205–0,229 | 0,208 | 65,6 | 3,6 |

Le pic RSS du passage instrumenté est respectivement 305,9 / 249,1 / 163,6 /
68,3 MiB. Ne pas comparer ces valeurs aux budgets RSS sans traçage ci-dessous.
Un avertissement IERS de mouvement polaire hors couverture apparaît pour les
catalogues et est conservé dans la preuve. Le benchmark n'est pas une validation
astrométrique de ces dates. Voir les [références indépendantes](SCIENCE_SATELLITE_REFERENCES.md).

## Budgets après mesure

| Charge identique | Budget de médiane, s | Budget RSS sans traçage, MiB | Budget Python tracé, MiB |
| --- | ---: | ---: | ---: |
| Catalogues combinés | 3 | 256 | 128 |
| Satellites | 6 | 256 | 128 |
| Rapports 1 000 fiches | 8 | 192 | 64 |
| Seestar 10 000 fichiers | 1 | 128 | 16 |

Temps : marge supérieure à trois fois les maxima mesurés, arrondie pour absorber
activité du poste et disque. Mémoire : paliers lisibles supérieurs aux pics, au
moins environ 30 % de marge RSS et Python, davantage pour les petites charges.
Ces budgets sont des objectifs de non-régression pour cette taille et ce poste,
pas des plafonds contractuels ni des assertions de CI. Les maxima CLI autorisés
ne sont pas tous mesurés ici et la croissance n'est pas extrapolée linéairement.

Pour investiguer un dépassement : répéter trois fois au calme, vérifier les
effectifs, comparer les versions et les avertissements, puis profiler la charge
concernée. Ne pas augmenter automatiquement un budget pour faire passer un
résultat. Le JSON ne contient ni chemin personnel, ni nom de machine, ni archive
Seestar réelle. Les mesures Linux et d'un autre matériel restent à effectuer.

## Vérifications ECC locales

Méthodes ECC appliquées : `python-testing` (cas paramétrés indépendants, horizon,
sortie publique et contexte IERS restauré) et `verification-loop` (Ruff, tests,
sources, revue des différences et du périmètre). Le plan préexiste dans
`a814a49`. Skyfield est installé seulement dans `local/reference-venv` du
worktree, aucune dépendance applicative n'a été ajoutée.

Première suite avec le Python parent : **604 réussis, 3 ignorés, 27 avertissements**
(ERFA/IERS déjà présents). Le test indépendant seul : **40 réussis**, avec une
alerte visible de table de secondes intercalaires périmée. Les vérifications
avec les environnements fournis par le pilote ont également réussi :

| Environnement | Suite complète | Avertissements visibles |
| --- | --- | --- |
| Python 3.13.6 / Astropy 8.0.2 / NumPy 2.5.5 / SGP4 2.27 | 604 réussis, 3 ignorés | 12 ERFA |
| Python 3.10.16 / Astropy 6.1.7 / NumPy 2.2.6 / SGP4 2.27 | 604 réussis, 3 ignorés | 87 IERS/ERFA |

Les trois cas ignorés concernent deux créations de liens symboliques Windows
et une FIFO POSIX. Aucun nouveau masquage d'avertissement. Ruff, XML du SVG,
différences sans erreurs d'espacement et deux reconstructions identiques de la
fixture réussissent. Les tests ordinaires n'ont pas besoin de Skyfield dans
ces environnements. Les environnements du pilote sont restés inchangés.
Ni compilation de distribution ni nouveau contrôle de typage applicatif n'est
nécessaire à ces fichiers de test et de mesure; aucune validation distante ou
observationnelle n'est revendiquée. Les fichiers communs d'avancement restent
sous la responsabilité du pilote.

### Correctifs ciblés après revue

Les preuves JSON et mesures ci-dessus restent celles du script initial
(`script_sha256` conservé), avant les protections de sorties. Les mesures n'ont
pas été réétiquetées comme une nouvelle campagne. Le correctif ajoute la
politique IERS explicite pour Python 3.10, les validations préalables, le
remplacement volontaire et la publication atomique partagés par les deux
scripts au moyen d'un auxiliaire standard indépendant de GNU Astrolist/Astropy.
La fixture scientifique a été recalculée avec le venv Skyfield local; seules
les empreintes des scripts changent, les 38 positions restent identiques.
Le contrôle ciblé porte sur les références et les sorties, avec dépendance
Skyfield simulée pour les seuls tests de commandes. Aucun calcul Skyfield
n'est simulé dans la fixture gelée. Un passage réel du worker catalogues sous
Python 3.10 termine avec 32 648 entrées, 13 instants et 189 sélections; les
avertissements de précision sont visibles.

Après correctif, les seuls tests ciblés `tests/test_scientific_references.py`
réussissent dans les deux environnements fournis par le pilote : **56 réussis,
3 ignorés, 1 avertissement ERFA** chacun. Les trois cas ignorés nécessitent la
création de liens symboliques Windows; les liens physiques sont réellement
testés et les jonctions sont également couvertes par métadonnées simulées.
Les tests vérifient les refus avant calcul, les alias de source, la publication
atomique interrompue, une création concurrente de destination, le remplacement
explicite et l'horodatage dynamique. Le contexte IERS est vérifié après succès
et erreur. Les suites complètes ne sont pas réexécutées pour ce correctif ciblé.
