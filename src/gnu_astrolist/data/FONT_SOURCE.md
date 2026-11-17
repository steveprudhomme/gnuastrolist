# Polices PDF

Les fichiers `fonts/DejaVuSans.ttf` et `fonts/DejaVuSans-Bold.ttf` sont copiés
sans modification depuis `matplotlib/mpl-data/fonts/ttf/` de l'installation
locale Matplotlib 3.10.8. Matplotlib n'est pas une dépendance d'exécution ajoutée.

Ces polices couvrent les lettres grecques et indices utilisés par les noms Bayer.
La génération des PDF les incorpore et les lit comme ressources binaires du paquet,
sans créer de fichier temporaire de police sur le disque Seestar.

Les droits Bitstream, les modifications DejaVu et les glyphes Arev sont conservés
dans la notice intégrale [LICENSE_DEJAVU.txt](fonts/LICENSE_DEJAVU.txt), redistribuée
avec les deux polices. Ces fichiers ne sont pas relicenciés sous GPL.

| Fichier | Empreinte SHA-256 |
| --- | --- |
| DejaVuSans.ttf | `3fdf69cabf06049ea70a00b5919340e2ce1e6d02b0cc3c4b44fb6801bd1e0d22` |
| DejaVuSans-Bold.ttf | `b184b89e3c1075f22f6b71575b6fc20d4972b3cfd3b23322ca6fd596dcaef167` |

La police précédente Vera ne couvrait pas correctement les noms grecs dans
les PDF de test. Les tests exigent désormais leur conservation à l'extraction.
