# Protocole comptes/chambres

## HTTP

POST /api/register et /api/login : JSON strict {"nick":"Alice","password":"abcd1"}, Origin autorisée obligatoire. Renvoie {"nick":"Alice"} et cookie cipher_session HttpOnly/SameSite=Strict, Secure sur HTTPS. GET /api/me renvoie le compte ou 401 authRequired. POST /api/logout reçoit {} et invalide la session. Codes d'erreur JSON `detail` : nickname, passInvalid, accountExists, credentials, authRequired, origin, rate, storage, invalid.

GET /api/config : {"v":1,"mode":"rooms","salt":"32 caractères hexadécimaux","iterations":600000}. Aucun code de chambre n'est renvoyé par cet endpoint. GET /health : {"status":"ok"}.

## WebSocket

Cookie valide + Origin exacte avant acceptation. Première trame sous 10 secondes : {"type":"join","nick":"Alice","room":"1111A"}. Pseudo = nom du compte. Code canonique : 5–24 caractères A–Z/0–9, au moins une lettre et un chiffre ; le client convertit en majuscules avant transmission. Le serveur rejette la forme non canonique.

Welcome : {"type":"welcome","session":"UUID v4","room":"1111A","members":["Alice"]}. Présence : {"type":"presence","event":"join ou leave","nick":"Alice","room":"1111A","members":[...]}. Liste et événements limités à la chambre. Ils ne sont pas authentifiés par la clé AES et ne prouvent pas une identité réelle.

Ping applicatif toutes les 27 secondes : {"type":"ping"} → {"type":"pong"}. Départ : {"type":"quit"}, émis par le bouton ou /quit sans transmettre ce texte comme message. Contrôles <=10/s, timeout serveur de réception 65 secondes. Reconnexion exponentielle 1–30 secondes + jitter, nouvelle session ; aucune récupération de message.

Message : {"type":"message","v":1,"room":"1111A","nick":"Alice","id":"UUID v4","session":"UUID v4 serveur","seq":1,"ts":"2026-10-26T12:00:00.000Z","iv":"base64","ciphertext":"base64"}.

Champs supplémentaires interdits, entiers stricts 1..9007199254740991 pour seq, UUID v4 minuscules, date ISO UTC valide avec 3 millisecondes. Base64 canonique standard avec padding. IV 12 octets ; ciphertext (tag GCM inclus) 17..6016 octets. Le serveur lie room, nick et session à la connexion et impose une séquence croissante.

AAD = UTF-8 du JSON sans espaces [v,room,nick,ts,session,seq,id], ordre fixe. Clé = PBKDF2-SHA256 du CODE DE CHAMBRE avec sel public stable, 600000 itérations. AES-256-GCM, tag 128 bits. Le serveur connaît les deux entrées et pourrait dériver cette clé : chiffrement pédagogique, pas confidentialité contre le serveur.

8 KiB maximum par paquet, 5 messages/s/client. Client : 2000 points de code maximum et taille finale contrôlée ; les caractères multioctets peuvent atteindre la borne avant 2000 caractères. Serveur incapable de compter les caractères en clair sans déchiffrer. Récepteur : vérification tag, texte non vide et longueur, 4096 ids et 512 sessions en mémoire ; rejette répétitions/séquences obsolètes, signale les sauts. État mis à jour après authentification seulement. Éviction et rechargement limitent la protection.

Sortie : messages effacés seulement sur la page qui quitte ; aucun effacement imposé aux autres. SQLite contient les comptes seulement. Fin de session invalide les prochains échanges ; heartbeat/nettoyage peut prendre jusqu'au délai de détection. Plafond avant handshake produit une fermeture générique ; navigateur ne peut pas toujours distinguer origine refusée, cookie manquant et indisponibilité réseau.
