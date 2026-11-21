# application-deployment

Dépôt GitOps de l'API de prix au m² des logements (données DVF).

- `deployment/` contient les manifestes Kubernetes de l'API ;
- `application.yaml` est l'application ArgoCD qui surveille le dossier `deployment/` sur la branche `main`.

Pour déployer une nouvelle version, changer le tag de l'image dans `deployment/deployment.yaml`
(par exemple `<DOCKERHUB_USERNAME>/application:v0.0.3`), puis pousser le changement sur `main` :
ArgoCD applique alors les manifestes.

L'API lit son jeton dans le secret `api-jeton`, qui doit exister dans le namespace avant le déploiement :

```bash
kubectl create secret generic api-jeton --from-literal=JETON_API='mon_jeton'
```

L'API charge le modèle de production depuis MLflow (modèle `dvf`, alias `production`)
au lieu de lire un fichier `model.skops`. Dans `deployment/deployment.yaml`, la variable
`MLFLOW_TRACKING_URI` doit être remplacée par l'URL de votre propre serveur MLflow. Les
identifiants de ce serveur sont lus dans le secret `mlflow-secrets`, qui doit exister
dans le namespace avant le déploiement :

```bash
kubectl create secret generic mlflow-secrets \
  --from-literal=MLFLOW_TRACKING_USERNAME="$MLFLOW_TRACKING_USERNAME" \
  --from-literal=MLFLOW_TRACKING_PASSWORD="$MLFLOW_TRACKING_PASSWORD"
```

## Entraînements avec Argo Workflows

`argo-workflow/manifest.yaml` décrit un _workflow_ `Argo Workflows` qui entraîne le modèle DVF avec quatre combinaisons de `n_trees` et de `learning_rate`, en parallèle. Chaque entraînement est enregistré dans l'expérimentation `dvf` de MLflow.

Le _workflow_ utilise l'image `<DOCKERHUB_USERNAME>/application:v0.0.4` et lit ses identifiants dans les secrets `mlflow-secrets` et `api-jeton`, qui doivent exister dans le namespace.

`ArgoCD` ne surveille que le dossier `deployment/` : ce manifeste n'est donc pas déployé automatiquement. Le _workflow_ se soumet à la demande, depuis le dépôt cloné :

```bash
kubectl create -f argo-workflow/manifest.yaml
```

Utiliser `create` et non `apply` : grâce à `generateName`, chaque soumission reçoit un nouveau nom. Le service `Argo Workflows` doit être lancé dans le namespace.
