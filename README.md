# 🏠 Chasseur d'appartements Marseille

Scrape les portails immobiliers avec **Scrapling**, filtre selon des critères précis,
et envoie **une seule notification push (ntfy)** regroupant les nouveaux biens.
Tourne **24/7 en autonomie** via GitHub Actions (cron horaire).

## Critères (modifiables dans `scraper/config.yaml`)

- T3+ (≥ 2 chambres), ≥ 60 m², ≤ 1200 € CC
- Marseille **7e / 8e / 9e** (arrondissements côtiers, « proche mer »)
- Terrasse/balcon/jardin + parking → **flagués « à vérifier »** si non confirmés dans l'annonce
  (passe en rejet strict via `strict_exterior: true` / `strict_parking: true`)
- Heuristique anti-arnaque (prix/m² anormalement bas, contact perso)

## Sources (état réel, testé)

| Site | Statut |
|------|--------|
| **Bien'ici** | ✅ Fonctionne (source primaire) |
| **PAP** | ⚠️ Best-effort — colle des `search_urls` géo dans `config.yaml` |
| **SeLoger** | ❌ Bloqué DataDome (gardé pour bascule IP résidentielle/proxy) |
| **LeBonCoin** | ❌ Bloqué DataDome (idem) |
| **Jinka** | 🔒 Nécessite `JINKA_COOKIE` (login) — agrège SeLoger/LeBonCoin |

## Utilisation locale

```bash
cd /Users/valentingaludec/APPARTS
source scrapling-env/bin/activate
cd apparts-hunter

python scraper/main.py --dry-run        # scrape + filtre + affiche (sans notif/état)
NTFY_TOPIC=mon-topic python scraper/main.py --test-notify   # notif de test
NTFY_TOPIC=mon-topic python scraper/main.py                 # run réel (notifie + maj état)
```

## Déploiement 24/7 (GitHub Actions)

1. Crée un repo **privé** et pousse ce dossier.
2. Repo → **Settings → Secrets and variables → Actions** → ajoute :
   - `NTFY_TOPIC` — ton topic ntfy secret (obligatoire)
   - `NTFY_SERVER` — optionnel (défaut `https://ntfy.sh`)
   - `JINKA_COOKIE` — optionnel (pour activer Jinka)
3. Onglet **Actions** → active les workflows → lance « Chasse appartements Marseille »
   via **Run workflow** pour un premier test.
4. Ensuite, le cron tourne **toutes les heures** automatiquement.

## Notifications (ntfy)

1. Installe l'app **ntfy** (iOS / Android).
2. Abonne-toi à ton topic (`NTFY_TOPIC`).
3. Tu reçois 1 notif batch par run dès qu'il y a du nouveau ; tap = ouvre la 1re annonce,
   le corps liste toutes les annonces avec liens cliquables.

## Architecture

```
scraper/
  main.py        orchestration (--dry-run / --test-notify)
  sites/         un scraper par portail (bienici, pap, seloger, leboncoin, jinka)
  extract.py     extraction d'attributs (regex)
  filters.py     critères durs/souples + anti-arnaque
  notify.py      ntfy (1 message batch)
  state.py       dédoublonnage (state/seen.json, commité par le cron)
  config.yaml    critères + URLs + ntfy
```
