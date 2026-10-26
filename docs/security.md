# Sécurité — évolution comptes et chambres (TP)

## Compromis volontaire

La version précédente utilisait une phrase non transmise au serveur. **Cette version utilise le code de chambre comme entrée PBKDF2 et transmet ce code au serveur pour le routage. Le serveur peut donc dériver la clé. Ne pas présenter ce TP comme du chiffrement de bout en bout contre le serveur.** Tous les membres d'une chambre peuvent fabriquer des messages authentifiés ; un compte n'est pas une preuve d'identité réelle. Un code court permet la recherche hors ligne et peut être deviné par un autre compte.

Le serveur relaie le chiffré sans en déchiffrer le contenu dans le chemin normal, mais peut techniquement le faire. Le sel public stable CHAT_KDF_SALT est exposé via /api/config. AES-256-GCM, IV aléatoire 12 octets, tag 16 octets ; PBKDF2-HMAC-SHA256 600000 itérations. Les collisions d'IV restent théoriquement possibles, pas d'unicité mathématique garantie. État anti-répétition temporaire et borné ; pas d'ordre global garanti contre un serveur malveillant.

## Comptes

Identifiants ASCII uniques insensibles à la casse. Mots de passe 5–128 caractères, lettre et chiffre requis ; minimum faible accepté pour le TP. PBKDF2-SHA256 serveur, 600000 itérations, sel aléatoire 16 octets par compte, comparaison constante du haché. Calcul hors de la boucle asyncio. Stockage SQLite : identifiant, nom affiché, sel et haché uniquement. Requêtes paramétrées. Aucune table de messages.

Cookie de session aléatoire 256 bits, HttpOnly, SameSite=Strict, Secure pour les requêtes provenant de l'origine HTTPS autorisée, durée maximale 8 heures. Sessions serveur seulement en mémoire ; redémarrage = reconnexion nécessaire. Déconnexion invalide le jeton ; une connexion existante est nettoyée à sa prochaine activité/heartbeat ou au timeout. Une seule présence de chat par compte. Les autres onglets d'un même profil partagent le cookie.

Création/login/logout : vérification exacte d'Origin, limite 20 requêtes/minute/adresse sur ces routes, corps <=1024 octets et validation stricte. Limiteur en mémoire borné ; ce n'est pas une défense complète contre une attaque distribuée et des utilisateurs partageant une IP peuvent atteindre le même plafond. Pas de récupération de compte, d'e-mail de vérification, d'admin ou de modération.

## WebSocket et interface

Origin exact et session valide avant acceptation ; maximum 50 sockets incluant l'attente initiale ; join sous 10 secondes ; code et pseudo liés au compte et à la connexion. Diffusion de messages ET présence filtrée par chambre. 8 KiB par paquet ; 5 messages/s/client, contrôle limité séparément ; file d'envoi bornée ; heartbeat 27 secondes. Aucun historique.

CSP sans inline/eval, scripts locaux, rendu textContent, en-têtes nosniff, referrer, permissions. Clé non exportable en mémoire, aucun stockage de code/messages dans localStorage ; pas de garantie d'effacement physique de mémoire ni de contrôle des copies faites par les participants. Quitter efface la conversation locale, pas celle des autres. Le serveur fournit le JavaScript et peut le modifier.

## Compatibilité et limites des tests

AbortSignal.timeout, Object.hasOwn et crypto.randomUUID ne sont plus requis. Repli pour dialog.showModal absent. JavaScript, cookies de première partie, HTTPS et Web Crypto restent indispensables. APIs récentes absentes simulées dans Chromium, mais aucun iPhone 7 réel testé ; pas de certification Safari/iOS. Pas de charge prolongée, test DDoS, expiration heartbeat par attente complète ou audit indépendant. Dépendances directes fixées, transitives non verrouillées intégralement. Le stockage gratuit Render n'est pas durable ; SQLite et les comptes peuvent être perdus.
