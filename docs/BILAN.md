# Bilan local — 23 octobre 2026

## Livré

Socle FastAPI, protocole strict, un salon #general, chiffrement natif navigateur AES-256-GCM/PBKDF2-SHA256 600000, sel public stable par configuration, présence et liste membres, /quit, heartbeat et reconnexion, interface FR/EN, thèmes, mobile, signature Web avec mail. Fichiers de configuration, tests et documentation créés dans CipherChat uniquement. Aucun fichier d'un autre projet modifié.

## Résultats réellement exécutés

- `python -m compileall -q app server.py` : succès.
- `python -m pytest -q` : 24 réussis, 1 avertissement de dépréciation Starlette/AnyIO.
- `npm test` : 5 réussis. Dernière dérivation mesurée : 118,0 ms sur Node.js 20.20.2 dans cet environnement, pas sur mobile.
- `python tests/browser_check.py` : succès, Chromium headless. Vérifications : deux clients avec la même phrase échangent un message ; troisième avec phrase différente voit un échec ; caractères HTML affichés comme texte ; trames envoyées sans texte original ; présence et départ ; /quit ; reconnexion et nouvel envoi ; FR/EN ; sombre/clair ; largeur mobile 390px sans débordement ; panneau membres mobile ; prefers-reduced-motion ; défilement préservé ; aucune erreur JS capturée.
- Captures docs/home-dark.png, docs/home-mobile.png et docs/chat.png prises par le parcours navigateur. Accueil sombre inspecté visuellement dans l'environnement.

## Problèmes rencontrés et corrigés

- Chromium ne démarrait pas : bibliothèques système manquantes installées.
- Premier échange WebSocket échoué : Uvicorn lancé sans backend WebSocket ; installation des requirements avec uvicorn[standard], redémarrage puis retest réussi.
- Compatibilité des dépendances directes stabilisée avec versions fixées ; avertissement AnyIO non bloquant restant.
- Attente par évaluation de chaîne bloquée par CSP dans le test navigateur : remplacée par une assertion CSS Playwright, retest réussi sans désactiver CSP.
- Plafond de connexions étendu aux connexions en attente du paquet join.

## Limites et vérifications restantes

- Pas de test manuel physique ni Firefox/Safari, pas d'audit indépendant ou de scan de vulnérabilités des dépendances.
- Pas de test de charge longue durée, expiration heartbeat par attente complète, ni saturation réelle des files sur réseau lent.
- Vérification du responsive automatisée à 390px, pas de matrice complète de tablettes/téléphones.
- Le contrôle d'accès par phrase est volontairement absent. L'origine ne constitue pas une authentification. Les messages cryptographiquement invalides peuvent être relayés ; seuls les clients les rejettent.
- Les événements de présence ne sont pas chiffrés ni authentifiés par la clé partagée.
- Un plafond atteint avant handshake produit un refus générique et une reconnexion, pas une explication détaillée fiable dans le navigateur.
- La protection contre la répétition est bornée à la mémoire et ne garantit pas un ordre global.
- Confidentialité contre un serveur malveillant distribuant le JavaScript non garantie.
- Pas de disponibilité continue promise, pas de maintien en veille garanti.

## Actions externes restantes

Avec autorisation séparée : créer/configurer GitHub, examiner les fichiers puis commiter/pousser, créer Render, conserver le même CHAT_KDF_SALT et définir l'origine HTTPS réelle, exécuter les vérifications en production, configurer manuellement le moniteur /health. Aucune URL Render ou GitHub obtenue. Aucun commit ni push effectué par l'assistant.

## Mise à jour de la phrase secrète
À la demande du créateur : minimum 5 caractères, avec une lettre ASCII et un chiffre, contrôlé dans le formulaire et le module de dérivation. Test Node ajouté : rejets des phrases trop courtes ou sans les deux catégories, chiffrement/déchiffrement avec abcd1. Régression : 24 tests backend, 6 tests Node et parcours Chromium réussis. Ce minimum accroît nettement le risque de recherche hors ligne ; aucune réduction des itérations PBKDF2.
