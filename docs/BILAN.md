# Bilan — comptes et chambres

## Réalisé et testé localement

Comptes SQLite (hachage PBKDF2, sessions cookie HttpOnly), inscription/login/logout, choix de chambre canonique, isolation des membres/messages, code utilisé pour dériver la clé, effacement local au départ. Auth et contrôle Origin côté HTTP/WS. Aucun message enregistré. Erreurs visibles FR/EN. Remplacement des API incompatibles avec iOS 15 et repli dialog.

32 tests pytest réussis, 6 tests crypto Node réussis, parcours Chromium réussi. Le parcours a d'abord révélé que le formulaire restait en mode inscription après création de compte : corrigé, puis tous les tests réexécutés avec succès. Tests manuels sur iPhone réel non exécutés. Le parcours remplace celui des invités, devenu incompatible avec l'authentification obligatoire.

Tests : comptes, mots de passe, doublons, hash non clair, cookies Secure/HttpOnly/SameSite, expiration/logout, limite tentatives/corps, refus origine/session, 50 connexions, liaison identité/chambre/session, paquets/tailles/fréquences, absence historique, persistance des comptes sans table messages. Navigateur : plusieurs profils, même code échange chiffré, autre code isolé, rendu sans HTML, /quit efface uniquement sa page, reconnexion au compte/rechargement, thèmes/FR-EN/mobile/mouvement réduit, APIs modernes supprimées artificiellement, erreurs réseau/503 et cookie indisponible simulés.

Un avertissement de dépréciation Starlette/AnyIO reste présent. Pas d'audit indépendant, tests de charge prolongés, garantie de compatibilité universelle ou disponibilité continue. La robustesse contre tous les blocages navigateur ne peut pas être garantie. Sur Render gratuit, comptes perdables avec le fichier SQLite. Les participants et le serveur connaissant le code peuvent dériver la clé : TP, pas une messagerie confidentielle contre le serveur.

## Livraison

Bundle Git produit avec commit local et son historique. Aucun push GitHub, déploiement Render ou service externe effectué par l'assistant. La page publique ne représente cette évolution qu'après push et déploiement effectifs. Détails d'installation et variables dans README.
