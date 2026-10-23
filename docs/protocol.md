# Protocole v1

Transport JSON UTF-8, un seul salon `#general`. Paquet maximum 8192 octets UTF-8. Aucun message d'historique.

## Contrôles

Client → serveur : `{"type":"join","nick":"Alice"}` dans les 10 secondes suivant l'acceptation. Pseudo ASCII `[A-Za-z0-9_-]{1,24}`, unique avec comparaison insensible à la casse. Le serveur attribue la session (UUID v4).

Serveur → client : `{"type":"welcome","session":"UUID v4","members":["Alice"]}`.

Présence : `{"type":"presence","event":"join","nick":"Alice","members":["Alice"]}` ; `event` vaut `join` ou `leave`. Informations serveur NON authentifiées par la clé du salon. Membres = connexions, pas identités vérifiées.

Heartbeat : `{"type":"ping"}` → `{"type":"pong"}` toutes les 27 secondes. Timeout de réception serveur 65 secondes ; contrôle client de l'absence de pong. Les frames Ping/Pong WebSocket ne sont pas le heartbeat applicatif. Contrôles limités séparément à 10/s pour éviter un flux illimité.

Départ : `{"type":"quit"}` ; l'interface traite `/quit` localement pour émettre ce contrôle sans transmettre de texte utilisateur.

Erreur : `{"type":"error","code":"invalid"}`. Autres codes : `nickname`, `duplicate`, `full`. Saturation avant handshake : fermeture/refus 1008 sans paquet JSON ; taille : 1009 ; client trop lent : 1013. L'interface peut donc afficher une reconnexion générique lorsque le plafond est atteint avant acceptation.

## Messages

```json
{"type":"message","v":1,"room":"#general","nick":"Alice","id":"UUID v4","session":"UUID v4 attribué","seq":1,"ts":"2026-10-23T12:00:00.000Z","iv":"base64 canonique","ciphertext":"base64 canonique"}
```

Champs supplémentaires interdits. `seq` entier strict de 1 à 9007199254740991 ; UUID v4 minuscules ; horodatage UTC ISO avec exactement 3 chiffres millisecondes et date valide. Base64 standard avec padding, réencodage identique exigé. IV : 12 octets ; ciphertext : 17 à 6016 octets, tag GCM de 16 octets inclus à la fin, comme produit par Web Crypto.

AAD = UTF-8 de `JSON.stringify([v,room,nick,ts,session,seq,id])`. Pas d'espaces ajoutés ; ordre fixe. Pseudo et session liés à la connexion serveur. Toute modification authentifiée échoue côté destinataire ; le serveur ne vérifie pas le tag.

5 messages/s/client, fenêtre glissante de 1 seconde. Le client limite à 2000 points de code Unicode et contrôle les 8192 octets sérialisés. Le serveur ne peut pas compter le texte déchiffré ; la borne du chiffré reste impérative et peut réduire la longueur disponible pour les caractères multioctets. Les clients rejettent également un texte déchiffré vide ou supérieur à 2000 caractères.

## Répétitions et ordre

Clients : 4096 identifiants et 512 sessions maximum en mémoire, avec éviction des plus anciens. Rejet des identifiants connus et séquences <= dernière séquence authentifiée. Saut de séquence signalé, message authentifié accepté. État mis à jour après authentification uniquement. Un nouvel arrivant peut commencer à toute séquence ; pas d'historique, donc pas de preuve de messages manquants avant son arrivée. Les évictions, rechargements et redémarrages limitent cette protection. Aucun ordre global garanti contre un serveur malveillant.

Reconnexion avec délai exponentiel (1 à 30 secondes + jitter), nouvelle session et séquence. La clé reste en mémoire, les anciens messages restent uniquement dans la page (maximum 500 éléments d'affichage). Aucun renvoi des messages manqués ou des envois incertains.
