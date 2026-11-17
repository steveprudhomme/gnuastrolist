# Catalogue NGC embarqué

Le fichier `ngc.csv.gz` est dérivé du fichier `database_files/NGC.csv` du projet
[OpenNGC](https://github.com/mattiaverga/OpenNGC), révision
`be3cd6c5498806a2fbb2f7e0452ef802dbb02be0`, déjà récupéré le 16 novembre 2026
pour Caldwell. L'intégration NGC utilise cette copie locale, sans téléchargement.

Attribution : Mattia Verga et contributeurs OpenNGC. Données dérivées sous
**CC BY-SA 4.0**, référence `doi:10.21938/y.1ejWUD_MQ6b_eDFoVbbw`.
Les transformations sont la sélection des entrées NGC, la conversion des
coordonnées J2000 en degrés, la normalisation des noms et la compression CSV.
Ces données ne sont pas relicenciées sous GPL.

## Périmètre et dénombrement

La source contient 8 373 lignes dont l'identifiant commence par NGC.
Le catalogue distribué conserve **8 098 entrées exploitables** après exclusion
de 274 lignes `Dup` et d'une ligne `NonEx`. Aucune autre ligne NGC de cette
révision n'a de coordonnées absentes. Le générateur exclut explicitement les
lignes sans coordonnées et comptabilise cette exclusion.

Ce nombre comprend les composants portant un suffixe, notamment NGC61A et
NGC61B, ainsi que les groupes nommés dans OpenNGC. Il ne désigne donc pas le
nombre historique de numéros NGC ni un inventaire dédoublonné d'objets physiques.
Un groupe et ses composants peuvent apparaître simultanément. Les étoiles,
doubles et entrées `Other` sont conservées avec le type attribué par la source.
Les entrées IC sont exclues; le catalogue IC reste une évolution distincte.

Les identifiants d'affichage retirent seulement les zéros initiaux :
`NGC0224` devient `NGC224`. Le champ `catalog_designation` conserve la forme
OpenNGC originale, et les suffixes restent distincts. Les coordonnées et les
dimensions de chaque ligne représentent cette entrée, sans fusion de composants.

## Photométrie et provenance

La magnitude est exclusivement `V-Mag` d'OpenNGC; les bandes B/J/H/K et la
magnitude de l'étoile centrale d'une nébuleuse planétaire ne la remplacent pas.
Il y a **3 506 valeurs V disponibles** et **4 592 valeurs absentes**.
Les valeurs absentes deviennent `None`, s'affichent « non disponible » et
passent après les valeurs connues au tri. Sans filtre, les entrées restent
sélectionnables; avec `--max-magnitude`, elles sont exclues.

Les tailles et magnitudes disponibles conservent leur source, la référence
OpenNGC et la date de récupération. Aucun complément SIMBAD propre au NGC
n'est interrogé dans ce lot. Le type de NGC1976 est `Cl+N` dans cette révision.

## Reconstruction hors réseau

```text
python scripts/build_ngc_catalog.py --source NGC.csv --retrieved-on 2026-11-16 --output src/gnu_astrolist/data/ngc.csv.gz
```

Le fichier local doit avoir l'empreinte SHA-256 suivante, vérifiée par défaut :
`54abea0b57b0a103831bfc7a8e3a99a23acfbf4bb581fcf3d8af539cbb826c84`.
Le gzip est déterministe avec horodatage nul. Pour une nouvelle révision,
examiner les différences et mettre à jour la notice et les tests avant de
fournir sa nouvelle empreinte via `--expected-sha256`.
