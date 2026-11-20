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
