# Modèle de sécurité

La phrase secrète (minimum 5 caractères, dont au moins une lettre ASCII et un chiffre dans le client officiel) n'est jamais transmise. PBKDF2-HMAC-SHA256, 600000 itérations, AES-256-GCM et IV aléatoire 96 bits via le générateur cryptographique natif. Les IV ne sont pas déterministes : leur unicité repose sur l'aléa, avec risque résiduel de collision ; aucun test fini ne prouve une unicité absolue. Clé non exportable, en mémoire ; aucun effacement garanti de la mémoire JS. La phrase saisie est retirée du champ après dérivation. Aucun stockage de clé ou de phrase dans localStorage ou URL.

CHAT_KDF_SALT : 16 octets aléatoires, 32 caractères hexadécimaux exactement, sans espace ou préfixe. Majuscules acceptées, forme publique normalisée en minuscules. Absence ou format invalide = refus de démarrage. Validation de format, pas preuve d'entropie. Le sel public n'est pas un secret. Généré UNE FOIS, conservé en configuration ; aucun sel automatique au démarrage. Changer le sel change la clé : coordonner le changement et recharger tous les clients.

## Limites essentielles

- Salon accessible sans preuve de connaissance de la phrase. Présence et événements de présence ne sont pas authentifiés avec la clé du salon.
- Pseudos uniques simultanément seulement, sans réservation ni identité réelle.
- Un client peut observer les métadonnées et soumettre un chiffré invalide structurellement correct ; serveur incapable de détecter le mauvais tag.
- Le client rejette le contenu non authentifié ; avis d'échec regroupés (au plus un avis de déchiffrement par 5 secondes).
- Tous les détenteurs de la clé peuvent fabriquer un message valide. Les AAD ne prouvent pas une identité individuelle.
- Le serveur voit métadonnées, tailles, heures et connexions ; pas le texte clair dans le protocole normal.
- Phrase faible : recherche hors ligne possible. Aucune forward secrecy et aucune rotation automatique des clés.
- Serveur compromis : JavaScript modifiable, secrets récupérables. Extensions malveillantes ou terminal compromis hors protection.
- Origin réduit les connexions de pages non autorisées, pas celles de clients natifs capables de choisir leur en-tête.
- Les limites par connexion ne suffisent pas contre un déni de service distribué. Pas de modération ni d'authentification ajoutée.

## Mesures

Origin exact avant acceptation ; 50 connexions incluant l'attente de join, timeout initial 10s. Validation stricte, limite 8 KiB, 5 messages/s ; files de diffusion limitées à 64 événements ; client lent déconnecté. CSP locale sans unsafe-inline/eval, textContent pour le contenu utilisateur, en-têtes nosniff/referrer/permissions et HSTS sur requêtes HTTPS reconnues. HTTPS/WSS en production. Un seul worker ; mémoire volatile, aucun historique serveur. Les journaux Uvicorn peuvent inclure IP et chemins HTTP, pas le contenu des messages.

## Validation restante

Tests automatisés Chromium uniquement, pas Safari/Firefox ou appareils physiques. Charge longue durée, expiration heartbeat par attente complète, saturation des files avec réseau réellement lent et déni de service distribué non validés. Audit indépendant et test d'intrusion non réalisés. Ce projet n'est pas une messagerie certifiée.
