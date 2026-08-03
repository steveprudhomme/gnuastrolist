# Provenance du cache SIMBAD

- Service : SIMBAD Astronomical Database, CDS, Strasbourg
- Accès : service TAP synchrone
- URL : <https://simbad.cds.unistra.fr/simbad/sim-tap>
- Tables interrogées : `ident`, `basic` et `flux`
- Mode d'interrogation : une requête ADQL pour les identifiants M1 à M110
- Date de récupération : 2026-08-03 UTC
- Nombre d'objets : 110
- Dimensions disponibles : 104
- Magnitudes apparentes V disponibles : 62
- Empreinte SHA-256 du cache distribué :
  `e1f602e8dac70d754c04ce45cdac45d9f128e252ff6d39d5d392b18106a91754`
- Référence générale : Wenger et al., 2000, *A&AS*, 143, 9,
  bibcode `2000A&AS..143....9W`

## Cache et reproductibilité

Le fichier `simbad_messier_cache.csv.gz` est un instantané local de la réponse
TAP. Le script `scripts/update_simbad_cache.py` reproduit l'interrogation en une
seule requête et peut aussi reconstruire le cache depuis une réponse CSV déjà
téléchargée. Le paquet n'interroge jamais SIMBAD pendant une observation : le
cache permet de limiter les requêtes, de respecter le service et de fonctionner
hors ligne.

Pour actualiser volontairement le cache :

```bash
python scripts/update_simbad_cache.py \
  --output src/gnu_astrolist/data/simbad_messier_cache.csv.gz
```

Il faut ensuite reconstruire `messier.csv.gz` avec
`scripts/build_messier_catalog.py`.

## Règles de sélection

Pour chaque objet, le générateur applique séparément les règles suivantes :

1. les axes majeur et mineur de SIMBAD sont choisis lorsqu'ils sont tous deux
   numériques, strictement positifs et ordonnés `majeur ≥ mineur`;
2. sinon, les dimensions OpenNGC sont conservées lorsqu'elles existent;
3. une magnitude V numérique de SIMBAD est choisie lorsqu'elle existe;
4. sinon, la magnitude V OpenNGC est conservée.

Chaque valeur distribuée conserve son catalogue source, son bibcode ou sa
référence et sa date de récupération. Pour OpenNGC, la référence enregistrée
est le DOI `10.21938/y.1ejWUD_MQ6b_eDFoVbbw`.

## Attribution et conditions

Les données SIMBAD restent attribuées au Centre de données astronomiques de
Strasbourg et ne sont pas relicenciées sous la GPL du logiciel. Les publications
ou services dérivés doivent citer SIMBAD conformément aux recommandations du
CDS : <https://simbad.cds.unistra.fr/simbad/>.
