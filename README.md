# ⚡ Elektro trenažér

Výuková apka pro budoucího elektrotechnika: barevné kódy rezistorů, logická hradla,
Ohmův zákon a AI zkoušející na přijímačky. Mobile-first, čeština, bodování s úrovněmi.

## Struktura

```
index.html        – celá aplikace (frontend, funguje i offline kromě AI záložky)
backend/          – FastAPI server pro AI zkoušejícího (Railway)
  main.py
  requirements.txt
  Procfile
```

## 1) Frontend na GitHub Pages

1. Vytvoř nové veřejné repo (např. `elektro-trenazer`) a nahraj obsah této složky.
2. V repu: **Settings → Pages → Source: Deploy from a branch → main / (root)** → Save.
3. Za chvíli poběží na `https://UZIVATEL.github.io/elektro-trenazer/`.
4. V telefonu otevřít v Chromu → menu → **Přidat na plochu**.

Záložky Rezistory, Hradla a Ohm fungují hned; AI test potřebuje backend (krok 2).

## 2) Backend na Railway

1. Railway → **New Project → Deploy from GitHub repo** → vybrat toto repo,
   **Root Directory** nastavit na `backend/`.
2. Variables:
   - `ANTHROPIC_API_KEY` – klíč z console.anthropic.com (povinné)
   - `ALLOWED_ORIGINS` – `https://UZIVATEL.github.io` (doporučeno po ověření, že vše běží)
   - volitelně `AI_MODEL`, `DAILY_LIMIT` (výchozí 300 dotazů/den – ochrana peněženky)
3. Railway detekuje Python a spustí přes `Procfile`. Vygenerovanou veřejnou adresu
   (Settings → Networking → Generate Domain) zkopíruj.

## 3) Propojení

Buď vlož adresu backendu do `index.html` do konstanty:

```js
let API_URL='https://TVOJE-SLUZBA.up.railway.app';
```

…nebo ji jednorázově vyplň přímo v aplikaci: záložka **AI test → Nastavení spojení**.

## Náklady a bezpečnost

- Model je ve výchozím stavu Haiku – jedna úloha stojí zlomek haléře.
- API klíč je jen na serveru, frontend ho nikdy nevidí.
- Denní limit dotazů brání nekonečnému klikání (i kamarádům ze třídy 🙂).

## Bodování

| Akce | Body |
|---|---|
| Rezistor v kvízu | 10 (+bonus za sérii, −3/nápověda) |
| Vyřešený obvod z hradel | 25 (−7/nápověda) |
| Ohmova úloha | 12 (−4/nápověda, −3/špatný pokus) |
| AI úloha | 15 (−4/odkrytý krok, −3/špatný pokus) |

Úrovně: Učeň ⚡ → Bastlíř 🔧 (100 b.) → Technik 🔌 (250) → Inženýr 📐 (500) → Mistr 🏆 (1000) → Elektro guru 🧠 (2000).

---
*Vyrobeno doma s tátou a AI 🤖*
