# Application fil rouge : cours de mise en production de projets data science

## Contexte

Ce dépôt est la partie pratique du cours https://ensae-reproductibilite.github.io/website/chapters/application.html. Il illustre l'application progressive des bonnes pratiques de mise en production : chaque application corrige ou enrichit la précédente.

Son rôle est de produire automatiquement un tag Git par application, qui versionne l'état attendu du projet à la fin de cette application. Ne crée, ne déplace et ne supprime aucun tag sans que je le demande.

## Dépôts liés (lecture seule)

- `../website` : les consignes du cours. C'est la référence : en cas de doute sur ce qu'une application doit contenir, relis la consigne correspondante.
- `../application` : le projet de départ, volontairement perfectible. Les exercices consistent justement à l'améliorer.

Demande moi s'il convient de modifier ces deux dépôts.

## Organisation de ce dépôt

- `src/` : code source Python de chaque application.
- `gitops/` : code du dépôt GitOps, utilisé à partir des applications avancées.

## Règle principale : propager les modifications

Les applications forment une chaîne. Toute modification faite dans l'application N doit être reportée dans les applications N+1, N+2… jusqu'à la dernière, sauf si une application ultérieure modifie volontairement ce passage. Dans ce cas, c'est la version de l'application ultérieure qui fait foi.

Cela vaut aussi pour les fichiers :

- un fichier créé dans l'application N doit exister dans les suivantes, sauf si une application ultérieure le supprime ou le remplace ;
- un fichier supprimé ou renommé dans l'application N ne doit plus être référencé dans les suivantes (imports, chemins, Dockerfile, CI, manifests de `gitops/`…).

Avant de conclure, liste toutes les applications touchées par la propagation et vérifie la cohérence de chacune.

## Chaque application est autonome

Chaque application doit fonctionner seule, sans dépendre d'une autre, dès l'application 1. Après toute modification, exécute chaque application affectée pour vérifier que rien n'est cassé.

Si tu ne peux pas exécuter une application (dépendance manquante, accès réseau, identifiants...), dis-le explicitement plutôt que de supposer qu'elle fonctionne.

## Dépendances

Les premières applications ne gèrent pas proprement leurs dépendances. C'est volontaire : n'ajoute pas de `requirements.txt` ou de `pyproject.toml` avant l'application qui l'introduit.

S'il manque un package pour exécuter une application, n'installe rien : signale le nom du package et l'application concernée, je l'installerai.

## Qualité de code

À partir de l'application qui introduit un critère de forme (linter `ruff`, formatage…), ce critère s'applique à cette application et à toutes les suivantes. Après chaque modification, lance-le sur chaque application concernée et corrige les erreurs.

Ne l'applique pas aux applications antérieures : leur code imparfait fait partie de l'exercice.

## Respecter la progression pédagogique

Chaque application doit refléter ce que demande sa consigne, ni plus ni moins. N'introduis pas dans une application une bonne pratique qui n'arrive que plus tard dans le cours (tests, typage, logging, conteneurisation…).

## Compte rendu de fin de tâche

Termine en indiquant :

- les applications modifiées et ce qui a changé dans chacune ;
- les vérifications effectuées (exécution, linter) et leur résultat ;
- les packages manquants éventuels ;
- ce que tu n'as pas pu vérifier.