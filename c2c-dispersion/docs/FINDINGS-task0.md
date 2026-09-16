# Tâche 0 — l'API Vinted distingue-t-elle « vendu » de « retiré » ?

**Date** : 2026-09-16
**Verdict** : **question non testable en l'état — l'API supposée par la spec n'existe plus.**
**Conséquence** : étude arrêtée avant la tâche 2. Aucun code de collecte écrit.
**Spec concernée** : `docs/superpowers/specs/2026-09-16-c2c-dispersion-design.md`

## Ce qui a été mesuré

| Sonde | Résultat |
|---|---|
| `GET /api/v2/catalog/items?per_page=3`, curl sans session | Page HTML « La page n'existe pas » |
| Même URL, depuis une session navigateur réelle (cookies posés) | Idem — « La page n'existe pas » |
| Requêtes XHR de `www.vinted.fr/catalog` après 2 séries de scroll | 9 requêtes, **aucune de données** : télémétrie (`relay/events`, `metrics.vinted.lt`, `metrics-ingress-web`), anti-bot (`dd.vinted.lt/js` = DataDome), vérifs de connexion |
| `GET /catalog`, curl sans session ni cookie | **HTTP 200, 7,25 Mo** |
| Marqueurs dans ce HTML | `/items/` × 192 · `catalog_id` × 2922 · `is_closed` × 0 · `user_id` × 0 · `brand_id` × 0 · `size_id` × 0 · `total_item_price` × 0 |

## Lecture

1. **Il n'y a plus d'API catalogue publique.** Le chemin `/api/v2/catalog/items`, sur lequel reposent les projets open-source recensés, renvoie une page d'erreur. La page catalogue est rendue côté serveur et n'émet aucun appel de données.

2. **Les annonces restent accessibles.** 192 liens `/items/<id>-<slug>` sont présents dans le HTML. La collecte n'est donc pas impossible.

3. **Mais il n'y a aucun JSON par annonce.** Les 2922 `catalog_id` sont la taxonomie des catégories et des chaînes i18n — le menu de filtres — pas de la donnée d'article. Les cartes n'existent que comme DOM, avec des noms de classes hachés au build (`ItemBox-module-scss-module__NoC3Da__…`), qui changent à chaque déploiement.

4. **DataDome est présent mais n'a rien bloqué ici.** Un `curl` sans cookie ni jeton a obtenu la page catalogue entière en HTTP 200. Les 503 observés côté extension portent sur des hôtes de télémétrie et ne sont pas concluants. Ne pas conclure à un blocage.

## Pourquoi cela arrête l'étude

Deux hypothèses porteuses de la spec tombent, et ce sont exactement celles qui la rendaient bon marché :

- **La vérité terrain labellisée.** Le design suppose un champ de statut séparant vente et retrait (spec §5). Aucun champ de ce type n'est exposé. Sans lui, on n'observe que « disparu », qui confond vente, retrait et suppression — le biais de survie que toute l'étude cherchait à éviter. La mesure de survie, qui est **la** variable du gate, perd son sens.

- **La clé de classe sans expertise.** Le design repose sur le tuple structuré `(brand_id, catalog_id, size_id, status)` fourni par l'API (spec §6.1). Ces champs sont absents du HTML. Les reconstituer exigerait de parser du texte rendu (« Très bon état », « Taille unique ») via des sélecteurs hachés au build — fragile, dépendant de la langue, et à re-maintenir à chaque déploiement Vinted.

Ce second point vide aussi le §4 de la spec : Vinted avait été retenu **contre** Leboncoin parce que son API était accessible et celle de LBC non. Ce critère n'existe plus. Les deux plateformes demandent désormais le même travail : parser du HTML derrière un anti-bot, avec des sélecteurs à maintenir.

## Ce qui n'a pas été fait, délibérément

Aucune recherche d'endpoint alternatif (autres chemins, hôtes `api.vinted.fr`, reconstitution de jeton). L'étape 5 de la tâche 1 du plan interdit le contournement improvisé, et énumérer des surfaces non publiées derrière un anti-bot relève de l'évasion de détection, pas de la collecte de données publiques.

## Options, si l'étude reprend

1. **Ingestion par HTML + sélecteurs.** Coût de maintenance récurrent, contradictoire avec un budget-temps opérationnel quasi nul. Le statut vendu/retiré resterait à valider annonce par annonce.
2. **Changer de terrain.** Une place de marché exposant encore une API structurée avec statut de vente. À vérifier avant de rien écrire.
3. **Abandonner la mesure de survie** et se rabattre sur le détecteur de juste prix pour achat personnel, qui ne dépend que de la médiane de classe — mais qui exige quand même les champs de classe.

Aucune de ces options n'est un ajustement du plan : chacune demande une nouvelle spec et un nouveau gate.
