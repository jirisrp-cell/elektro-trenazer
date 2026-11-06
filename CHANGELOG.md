# Changelog

## 2026-11-06

- `index.html` je nově Elektro akademie (dodaná verze `Elektro-akademie.html`). Původní Elektro trenažér není v repu (zůstává jen lokálně).
- Přidaná kapitola **🧮 Matika na přijímačky** (modul `matika`, samostatný blok `<style>` + `<script>` před blokem „přehled, navigace“): AI zkoušející převzatý ze staré verze, napojený na XP, milníky (`mat-first`, `mat-five`, `mat-nine`) a nastavení adresy serveru v `localStorage` (`elektro-akademie-api`). Statistika úloh je v `S.aiStats`.
- Blok „přehled, navigace“: do `GROUPS` přidaná kapitola `matika`; nový odznak `prijimacky` (10 vyřešených úloh); odznak `all` (Mistr akademie) ignoruje moduly s `optional: true`, aby nebyl závislý na internetu.
- Okno nápovědy: doplněný odstavec „Matika na přijímačky“. Stávající texty a fyzikální obsah beze změny.
- Backend: víc témat, `GET /api/temata`, volba tématu v `POST /api/uloha`, serverová kontrola výsledku přes pole `vypocet` (max. 3 pokusy), věk ve „vysvětli jinak“ podle úrovně.
- Repozitář uklizen: smazán starý `main.py` v kořeni a `backend/__pycache__/`, obnoven `backend/main.py`, přidán `.gitignore`.
- `API_URL` v `index.html` nastaven na `https://elektro-trenazer-production.up.railway.app`.
