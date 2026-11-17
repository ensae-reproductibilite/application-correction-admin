# application-deployment

Dépôt GitOps de l'API de prix au m² des logements (données DVF).

- `deployment/` contient les manifestes Kubernetes de l'API ;
- `application.yaml` est l'application ArgoCD qui surveille le dossier `deployment/` sur la branche `main`.

L'API lit son jeton dans le secret `api-jeton`, qui doit exister dans le namespace avant le déploiement :

```bash
kubectl create secret generic api-jeton --from-literal=JETON_API='mon_jeton'
```
