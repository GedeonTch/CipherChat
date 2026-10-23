# Déploiement manuel : GitHub, Render, surveillance

Aucune de ces actions externes n'a été effectuée. Les commandes Git ci-dessous sont des instructions à exécuter après autorisation, pas un compte rendu d'actions réalisées.

## GitHub

1. Exécuter les tests, vérifier `.gitignore`, ne pas ajouter `.env`.
2. Créer un dépôt vide et copier son URL réelle.
3. Depuis CipherChat :

```bash
git init -b main
git add .
git status
# Examiner les fichiers, puis :
git commit -m "Initial CipherChat Web implementation"
# Remplacer URL_DU_DEPOT_REEL par l'adresse réellement créée :
git remote add origin URL_DU_DEPOT_REEL
git push -u origin main
```

## Render

1. Créer un Web Service Python depuis le dépôt autorisé, ou utiliser le Blueprint `render.yaml`.
2. Build : `pip install -r requirements.txt` ; démarrage : `python server.py`.
3. Configurer `CHAT_KDF_SALT` avec la valeur initiale de 32 caractères hexadécimaux. La réutiliser, ne pas en générer à chaque déploiement. La conserver dans le tableau de bord et dans une copie de configuration administrateur ; si le service est recréé, la ressaisir à l'identique.
4. Configurer `ALLOWED_ORIGINS` avec l'origine HTTPS exacte attribuée au service, sans chemin ni slash final. Si le nom n'est connu qu'après création, compléter la variable puis redéployer ; aucun wildcard temporaire.
5. Render fournit `PORT` ; ne pas imposer un port fixe dans la configuration production.
6. Garder un seul worker et une seule instance. L'état des membres ne serait pas partagé entre processus/instances.
7. Vérifier GET `/health` = HTTP 200 et `{"status":"ok"}`, chargement du frontend, HTTPS/WSS, deux navigateurs avec la même phrase, phrase incorrecte, départ et reconnexion après redémarrage.
8. Enregistrer l'URL réelle dans le README seulement après vérification.

Le sel est public. La phrase secrète et la clé AES ne doivent jamais être des variables serveur. Le sel ne tourne pas automatiquement ; un changement volontaire nécessite une reconnexion coordonnée de tous les clients.

## Surveillance HTTP externe

Choisir un moniteur HTTP dont l'offre autorise une fréquence de cinq minutes (vérifier les conditions actuelles dans son tableau de bord). Saisir l'URL HTTPS réelle suivie de `/health`, attendre HTTP 200, choisir 5 minutes si disponible et configurer les alertes voulues. Enregistrer un résultat de contrôle réel avant de déclarer le moniteur actif.

Pas d'intégration payante ni de compte externe créé automatiquement. La surveillance n'est pas une garantie de maintien éveillé ni de disponibilité. Les connexions et données en mémoire disparaissent après redémarrage ; les clients se reconnectent sans historique. L'interface signale les démarrages lents et les interruptions.
