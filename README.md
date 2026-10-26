# CipherChat Web

**Comptes simples · Chambres isolées · Messages éphémères · FR / EN**

[Application en ligne](https://cipherchat-0fhm.onrender.com) · [Code Web](https://github.com/GedeonTch/CipherChat) · [Version CLI](https://github.com/GedeonTch/CipherChat-CLI)

TP de messagerie Web : créez un compte, connectez-vous puis saisissez un code de chambre. Les personnes utilisant **le même code** se voient et échangent ; les autres chambres sont isolées. L'interface ne montre qu'une chambre à la fois, sans annuaire public.

> Cette évolution comptes/chambres a été testée localement. Sa présence sur le site public dépend de son déploiement. Le service Render gratuit peut démarrer lentement et perdre ses fichiers locaux lors d'un remplacement d'instance.

![Identité visuelle CipherChat — capture de la version précédente, conservée](docs/home-dark.png)

## Fonctionnement

1. **Créer un compte** ou **se connecter** avec son identifiant et son mot de passe.
2. Saisir un **code de chambre**, par exemple `1111A` (5 à 24 lettres/chiffres, au moins un de chaque ; les lettres sont converties en majuscules).
3. Seuls les comptes présents dans cette chambre sont listés et reçoivent ses messages.
4. **Quitter** ou `/quit` efface les messages de sa propre page et revient au choix de chambre. Les autres conservent leur affichage. Aucun historique n'est envoyé à la prochaine entrée.
5. **Déconnexion du compte** invalide sa session. Le compte est conservé tant que le fichier SQLite existe.

Les identifiants contiennent 1 à 24 lettres ASCII, chiffres, `_` ou `-`, et sont uniques sans distinction de casse. Mot de passe : **5 à 128 caractères, dont une lettre ASCII et un chiffre**. Ce minimum est faible : privilégier un mot de passe long. Une seule connexion de chat par compte à la fois.

Les conversations restent seulement dans les pages des participants (500 éléments affichés maximum) et dans les files temporaires de diffusion, **jamais dans SQLite**. Quitter n'efface pas les messages des autres et ne peut pas empêcher une capture d'écran. Les messages manqués pendant une interruption ne sont pas récupérés.

## Chiffrement : simplification pédagogique importante

Le **code de chambre sert aussi de phrase partagée de chiffrement**, sans champ supplémentaire. AES-256-GCM, IV aléatoire de 96 bits, PBKDF2-HMAC-SHA256 à **600000 itérations** ; métadonnées authentifiées par AAD.

**Le serveur connaît le code de chambre et le sel public : il peut donc dériver la clé. Cette version ne protège pas les messages contre le serveur.** Les codes courts sont faciles à chercher hors ligne. Ce compromis est volontaire pour ce TP : ne pas utiliser pour des données sensibles. Les comptes ne vérifient pas une identité réelle.

Le mot de passe du compte est distinct : il est envoyé uniquement via HTTPS en production puis haché côté serveur avec PBKDF2-SHA256 (600000 itérations et sel aléatoire propre au compte). Jamais enregistré en clair. Les sessions utilisent un cookie HttpOnly, SameSite=Strict, Secure sur l'origine HTTPS, valable au maximum 8 heures et conservé côté serveur en mémoire. Un redémarrage impose une reconnexion, pas une recréation de compte si SQLite a été conservé.

## Interface et compatibilité

Français par défaut, anglais, clair/sombre, mobile, messages d'erreur rouges et accessibles, animations respectant `prefers-reduced-motion`. Seuls thème et langue sont enregistrés dans localStorage ; aucun mot de passe, cookie de session, code ou message n'y est placé par l'application.

Les API problématiques sur iOS 15 ont été remplacées : timeout via AbortController, UUID via crypto.getRandomValues, pas de Object.hasOwn. Repli pour les navigateurs sans dialogue natif. Cible : navigateurs récents et iOS 15 avec Web Crypto, JavaScript et cookies de première partie autorisés. HTTPS obligatoire hors localhost.

Les erreurs distinguent identifiants incorrects, compte existant, champs invalides, session expirée/cookies bloqués, délai, réseau/requête bloquée, stockage ou serveur indisponible. On ne peut pas identifier avec certitude toutes les raisons d'un blocage réseau, ni contourner les restrictions du navigateur.

## Installation

Python 3.12+ et pip ; Node.js 20+ pour les tests cryptographiques.

```bash
git clone https://github.com/GedeonTch/CipherChat.git
cd CipherChat
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(16))"
```

Reporter le sel généré UNE SEULE FOIS dans `.env`, puis le conserver :

```dotenv
CHAT_KDF_SALT=REMPLACER_PAR_32_CARACTERES_HEXADECIMAUX
ALLOWED_ORIGINS=http://localhost:8000
PORT=8000
CHAT_DB_PATH=accounts.sqlite3
```

```bash
python server.py
```

Ouvrir **http://localhost:8000**. Pour un essai à plusieurs comptes, utiliser des profils ou fenêtres privées distincts : la session du compte est partagée entre les onglets d'un même profil.

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `CHAT_KDF_SALT` | Sel public de 16 octets, exactement 32 caractères hexadécimaux, stable. Absence/format invalide = refus de démarrage. Ce n'est pas un secret ni une clé. |
| `ALLOWED_ORIGINS` | Origines exactes sans slash final. Production : `https://cipherchat-0fhm.onrender.com`. Local : `http://localhost:8000`. Liste séparée par virgules ; aucun joker. |
| `PORT` | Port local 8000 ; automatiquement fourni par Render. |
| `CHAT_DB_PATH` | Fichier SQLite des comptes, par défaut `accounts.sqlite3` à la racine. Son dossier doit exister et être accessible en écriture. Jamais commiter ce fichier. |
| `PYTHON_VERSION` | Version de Python sélectionnée par Render ; configuration proposée 3.12.10. |

`.env` local n'est pas transféré à Render. Aucun mot de passe de compte ni code de chambre ne doit être une variable serveur.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
npm test
# Navigateur, serveur local lancé à part :
python -m playwright install chromium
# Linux si nécessaire : python -m playwright install-deps chromium
python tests/browser_check.py
```

Résultats de cette évolution : **32 tests backend, 6 tests cryptographiques et parcours Chromium réussis**. Création/reconnexion, mauvais mot de passe, sessions, validation, isolation de chambres, présence, limites, effacement local, absence d'historique, rendu sûr, erreurs réseau/503/cookies et absence simulée d'API récentes testés. Mesure PBKDF2 Node observée lors de la régression : environ 120 ms, pas une mesure mobile.

**Pas de test sur iPhone 7 physique ni de promesse de compatibilité universelle.** Les restrictions de cookies ou JavaScript doivent être levées par l'utilisateur. Un avertissement non bloquant Starlette/AnyIO subsiste. Pas de test de charge prolongé ni d'audit indépendant des dépendances.

## Structure

`app/auth.py` : comptes, hachage, sessions et limite des tentatives. `app/main.py` : routes, présence et diffusion isolée. `app/protocol.py` : schémas. `app/settings.py` : environnement. `static/` : interface et modules crypto/protocole/connexion/réseau/traductions. `tests/` : tests réels. `docs/` : protocole, sécurité, déploiement et bilan.

## Render et surveillance

Un seul Web Service Python, un seul worker et une seule instance. Build : `pip install -r requirements.txt` ; démarrage : `python server.py`. `/health` doit répondre HTTP 200. Vérifier l'origine HTTPS exacte dans Environment, conserver le sel et laisser Render fournir PORT.

**SQLite sur le disque gratuit éphémère peut disparaître après redéploiement ou remplacement d'instance** : les comptes devront alors être recréés. C'est accepté pour ce TP, pas un stockage durable garanti. Un disque persistant ou une base externe serait nécessaire pour conserver durablement les comptes.

[Procédure Render/GitHub et surveillance](docs/deployment.md) · [Protocole](docs/protocol.md) · [Sécurité](docs/security.md) · [Bilan](docs/BILAN.md)

Un contrôle HTTP externe de `/health` toutes les cinq minutes peut être configuré manuellement si l'offre choisie le permet. Aucun moniteur n'est créé par le code, et cela ne garantit pas une disponibilité continue.

## Créateur

**Créé par GEDEON CIBANVUNYA**  
[tchibanvunyagedeon@gmail.com](mailto:tchibanvunyagedeon@gmail.com) · © 2026
