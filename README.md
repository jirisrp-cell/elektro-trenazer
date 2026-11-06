# ⚡ Elektro akademie

Interaktivní elektrotechnika pro osmáky a deváťáky: Ohmův zákon, rezistory, Kirchhoff, logická hradla,
zásuvky, jističe, chrániče, síť a kariéra elektrikáře. Navíc kapitola **Matika na přijímačky**
s AI zkoušejícím. Mobile-first, čeština, XP, úrovně a odznaky.

Obsah lekcí připravil známý elektrikář (MK Group). Před úpravami si přečti poznámku
na začátku `index.html`: texty a fyzikální obsah se nemění, jen logika a vzhled,
a každá změna se zapisuje do `CHANGELOG.md`.

## Struktura

```
index.html          – celá aplikace (funguje i offline, kromě kapitoly Matika na přijímačky)
favicon-32.png      – ikonka (dodá autor akademie)
favicon-192.png     – ikonka pro plochu telefonu (dodá autor akademie)
CHANGELOG.md        – seznam změn
old/                – původní Elektro trenažér (jen záloha)
backend/            – FastAPI server pro AI zkoušejícího (Railway)
  main.py
  requirements.txt
  Procfile
```

## 1) Frontend na GitHub Pages

Repo musí být veřejné a `index.html` v kořeni. Settings → Pages → Deploy from a branch → main / (root).
Běží na `https://UZIVATEL.github.io/elektro-trenazer/`. V telefonu v Chromu: menu → Přidat na plochu.

## 2) Backend na Railway

1. Railway → New Project → Deploy from GitHub repo, **Root Directory** `backend/`.
2. Variables:
   - `ANTHROPIC_API_KEY` – klíč z console.anthropic.com (povinné)
   - `ALLOWED_ORIGINS` – `https://UZIVATEL.github.io` (bez lomítka na konci)
   - volitelně `AI_MODEL`, `DAILY_LIMIT` (výchozí 300 dotazů/den)
3. Settings → Networking → Generate Domain, adresu zkopíruj.

Endpointy: `GET /` (stav), `GET /api/temata`, `POST /api/uloha`, `POST /api/vysvetli`.

### Kontrola výsledků

AI ke každé úloze vrací i pole `vypocet`, čistý číselný výraz (např. `1200*0.85`).
Server ho sám spočítá (bezpečně přes `ast`, žádné `eval`) a porovná s uvedeným výsledkem.
Když nesedí, úlohu zahodí a nechá AI vymyslet novou (max. 3 pokusy). `vypocet` se na frontend neposílá.

## 3) Propojení

Adresu backendu vlož do `index.html` do konstanty v bloku „Matika na přijímačky“:

```js
const API_URL = 'https://TVOJE-SLUZBA.up.railway.app';
```

…nebo ji vyplň přímo v aplikaci: Matika na přijímačky → ⚙️ Nastavení spojení (uloží se v prohlížeči).

## Bodování v kapitole Matika na přijímačky

| Akce | XP |
|---|---|
| Vyřešená úloha | 15, +2 za každou správnou v řadě (max +10), −4 za odkrytý krok, −3 za špatný pokus, min. 2 |
| Milník: první úloha | +20 |
| Milník: pět úloh | +40 |
| Milník: úloha z 9. třídy napoprvé a bez nápovědy | +40 |
| Odznak 🎓 Připraven na přijímačky | 10 vyřešených úloh |

Kapitola je volitelná, nezapočítává se do odznaku Mistr akademie.

## Náklady a bezpečnost

- Výchozí model je Haiku, jedna úloha stojí zlomek haléře (při zamítnutém výsledku až 3 volání).
- API klíč je jen na serveru, frontend ho nikdy nevidí.
- Na server jde jen obtížnost, téma a text úlohy. Postup a body zůstávají v prohlížeči.

---
*Vyrobeno doma s tátou a AI 🤖, odborně opraveno elektrikářem ⚡*
