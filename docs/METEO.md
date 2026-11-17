# Météo fiable et données partielles — ECC-B

GNU Astrolist complète la liste astronomique avec deux sources : Open-Meteo
pour les conditions civiles et 7Timer! ASTRO pour les indices astronomiques.
Ces prévisions restent informatives : elles ne filtrent pas les objets.

## Données complètes, partielles ou indisponibles

Une réponse valide est conservée variable par variable. Une température peut
donc être affichée même si les nuages sont inconnus; la transparence peut rester
disponible sans seeing. Une valeur manquante n'est jamais remplacée par zéro.
Un véritable zéro reste une mesure valide.

Les valeurs nulles, de mauvais type, non finies ou hors du domaine accepté
sont omises avec un avertissement **données partielles**. Une série de longueur
différente de la liste des heures est écartée entièrement : le logiciel ne
devine pas à quelle heure rattacher ses valeurs. Une chronologie invalide,
dupliquée ou non croissante rend la série du fournisseur inutilisable.

Les avertissements portent sur la réponse reçue, pas seulement sur la plage
où une valeur s'affiche. Une absence dans une période n'efface pas les mesures
valides de l'autre. Si les deux sources sont indisponibles, les résumés météo
le disent et la liste astronomique reste produite pour les erreurs attendues
de transport ou de données. Une erreur de programmation inattendue n'est pas
silencieusement transformée en panne météo.

Ces états et avertissements sont identiques dans le terminal et les rapports
TXT/PDF. Les cellules inconnues utilisent un tiret. `--offline` conserve sa
priorité : aucune requête météo n'est effectuée.

## Rosée : comparer les mêmes instants

Le calcul retient seulement les instants où **température, point de rosée et
humidité sont tous trois valides**. Le point de rosée est la température à
laquelle la vapeur d'eau peut commencer à se condenser.

Exemple inventé :

| Heure | Température | Point de rosée | Humidité | Utilisation pour la rosée |
| --- | --- | --- | --- | --- |
| 21 h | 5 °C | Manquant | 70 % | Trio incomplet : écarté |
| 22 h | 20 °C | 10 °C | 70 % | Trio complet : conservé |

L'écart exploitable vaut 20 − 10 = 10 °C. On ne compare jamais les 5 °C de
21 h aux 10 °C de 22 h. Dans cet exemple, le niveau est « faible » **pour la
seule mesure complète**, avec un avertissement sur les données manquantes.
Ce n'est pas une garantie pour les heures non mesurées.

Les seuils existants sont conservés : très élevé si l'écart minimal est au plus
1 °C ou l'humidité maximale au moins 95 %, élevé à 2 °C ou 90 %, modéré à 4 °C
ou 80 %, faible sinon. Ces extrêmes sont pris parmi les trios complets de la
période. Sans trio complet, le risque reste inconnu, jamais « faible » par défaut.

## Heures et périodes de repli

Les horodatages munis d'un décalage UTC ou de `Z` sont convertis dans le fuseau
du site. Le décalage n'est pas simplement remplacé. Une heure civile sans
décalage doit exister et désigner un instant unique; les heures ambiguës ou
inexistantes d'un changement d'heure sont refusées. Le logiciel n'invente pas
le choix d'heure d'été/hiver. Deux occurrences d'une heure avec des décalages
explicites différents peuvent désigner deux instants distincts valides.

Avec les horaires solaires valides, la soirée couvre les trois heures suivant
le coucher du Soleil; la période avant l'aube, les trois heures précédant son
lever le lendemain. Si ces horaires manquent, les plages conventionnelles
**20–23 h** et **3–6 h locales** sont utilisées et annoncées par un avertissement.
Elles ne prouvent pas l'existence d'une nuit ou d'une aube, notamment aux pôles.
Des horaires solaires valides peuvent encore servir aux indices 7Timer même si
les mesures horaires Open-Meteo sont inutilisables.

La moyenne civile utilise les valeurs valides de chaque variable dans la période,
bords inclus, sans interpolation. Les précipitations utilisent le maximum prévu.
Les indices de qualité 7Timer restent les conversions déjà documentées dans le
[README](../README.md); ce ne sont pas des probabilités ni des mesures sur place.

## Contrôles techniques de lecture

La réponse est limitée à **2 Mio**, avec un délai de socket de 10 secondes par
requête. Les séries utilisées sont limitées à **1 000 échantillons**. Le client
demande une réponse sans compression et refuse les encodages HTTP inattendus;
il ne décompresse pas une réponse non sollicitée. Un JSON invalide, une clé
dupliquée ou une constante JSON non standard NaN/Infinity est rejeté.

Les domaines ci-dessous sont des garde-fous d'acceptation de l'application,
pas une validation scientifique exhaustive de la prévision :

| Champ consommé | Domaine accepté | Unité attendue si fournie |
| --- | --- | --- |
| Température et point de rosée | −150 à 100 | °C |
| Nuages, humidité, probabilité de précipitations | 0 à 100 | % |
| Vent | 0 à 1 000 | km/h |
| Seeing et transparence | Catégories entières 1 à 8 | Catégories ASTRO |
| Indice de soulèvement | −10, −6, −4, −1, 2, 6, 10, 15 | Catégories ASTRO |
| Échéance ASTRO | 0 à 72 heures depuis l'initialisation | Heures |

Les booléens et chaînes numériques ne sont pas traités comme des mesures.
Si `hourly_units` est fourni, une unité absente ou incompatible écarte la variable
concernée; aucune conversion arbitraire n'est effectuée. Sans ce dictionnaire,
les unités explicitement demandées au fournisseur sont utilisées.

Les tests emploient exclusivement des réponses synthétiques et ne prouvent pas
la disponibilité actuelle des services. Ce lot n'ajoute ni archive météo, ni
fournisseur, ni cache. Les protections d'export ECC-A et la lecture seule des
archives Seestar restent applicables.
