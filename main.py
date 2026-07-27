"""
Elektro trenažér – AI zkoušející (backend pro Railway)

Malý FastAPI server, který drží Anthropic API klíč a přeposílá požadavky
z frontendu (GitHub Pages). Klíč tak nikdy neopustí server.

Env proměnné:
  ANTHROPIC_API_KEY  (povinná)  – klíč z console.anthropic.com
  AI_MODEL           (volitelná) – výchozí claude-haiku-4-5-20251001
  ALLOWED_ORIGINS    (volitelná) – čárkou oddělené originy, výchozí "*"
                       (po nasazení doporučeno zúžit na https://UZIVATEL.github.io)
  DAILY_LIMIT        (volitelná) – max. počet AI dotazů za den, výchozí 300

Start: uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import json
import os
import random
import re
from datetime import date

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("AI_MODEL", "claude-haiku-4-5-20251001")
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "300"))

app = FastAPI(title="Elektro trenažér – AI zkoušející")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- jednoduchý denní limit (ochrana peněženky) -----------------------------
_usage = {"day": date.today(), "count": 0}


def check_limit() -> None:
    if _usage["day"] != date.today():
        _usage["day"] = date.today()
        _usage["count"] = 0
    if _usage["count"] >= DAILY_LIMIT:
        raise HTTPException(429, "Denní limit AI dotazů vyčerpán, zkus to zítra.")
    _usage["count"] += 1


# --- témata úloh -------------------------------------------------------------
TEMATA = {
    "78": [
        "lineární rovnice o jedné neznámé",
        "zlomky – sčítání a násobení",
        "procenta (sleva, DPH, úrok)",
        "obvod a obsah obdélníku nebo trojúhelníku",
        "převody jednotek (délka, hmotnost, čas)",
        "přímá úměrnost a trojčlenka",
        "slovní úloha o penězích nebo nákupu",
    ],
    "9": [
        "slovní úloha vedoucí na lineární rovnici (styl přijímaček CERMAT)",
        "jednoduchá soustava dvou rovnic",
        "Pythagorova věta v praktické situaci",
        "procenta a promile ve slovní úloze",
        "poměr a měřítko mapy",
        "objem a povrch kvádru nebo válce",
        "slovní úloha o pohybu nebo společné práci",
    ],
}
LEVEL_TXT = {
    "78": "žáka 7.–8. třídy základní školy",
    "9": "deváťáka, který se připravuje na přijímačky na střední školu (obtížnost testů CERMAT)",
}


class UlohaReq(BaseModel):
    obtiznost: str = "78"


class VysvetliReq(BaseModel):
    zadani: str
    kroky: list[str] = []
    uroven: str = "78"


# --- volání Anthropic API ----------------------------------------------------
async def claude(prompt: str, max_tokens: int = 1000) -> str:
    if not API_KEY:
        raise HTTPException(500, "Na serveru chybí ANTHROPIC_API_KEY.")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    if r.status_code != 200:
        raise HTTPException(502, f"Anthropic API vrátilo {r.status_code}")
    data = r.json()
    return "".join(
        b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
    )


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("V odpovědi není JSON.")
    return json.loads(m.group(0))


# --- endpointy ---------------------------------------------------------------
@app.get("/")
async def root():
    return {"ok": True, "sluzba": "Elektro trenažér – AI zkoušející"}


@app.post("/api/uloha")
async def uloha(req: UlohaReq):
    check_limit()
    lvl = req.obtiznost if req.obtiznost in TEMATA else "78"
    tema = random.choice(TEMATA[lvl])
    prompt = (
        f"Vytvoř jednu matematickou úlohu pro {LEVEL_TXT[lvl]}. Téma: {tema}. "
        "Odpověz POUZE platným JSON objektem bez jakéhokoli dalšího textu a bez markdown, "
        "přesně v tomto tvaru: "
        '{"zadani": "text úlohy česky", '
        '"vysledek": "konečný výsledek jako číslo s desetinnou tečkou, bez jednotky", '
        '"jednotka": "jednotka výsledku, nebo prázdný řetězec", '
        '"kroky": ["krok 1", "krok 2", "krok 3"]} '
        "Pravidla: výsledek musí být jediné jednoznačné číslo; "
        "kroky jsou 3 až 5 srozumitelných kroků řešení a poslední krok obsahuje výsledek; "
        "zadání je krátké, jasné a v zadání výslovně řekni, v jaké jednotce má žák odpovědět."
    )
    for _ in range(2):  # jedna oprava, kdyby AI nevrátila čistý JSON
        try:
            data = parse_json(await claude(prompt))
            if not data.get("zadani") or "vysledek" not in data:
                raise ValueError("Neúplná úloha.")
            return data
        except (ValueError, json.JSONDecodeError):
            continue
    raise HTTPException(502, "AI nevrátila platnou úlohu, zkus to znovu.")


@app.post("/api/vysvetli")
async def vysvetli(req: VysvetliReq):
    check_limit()
    kroky = "\n".join(f"- {k}" for k in req.kroky)
    prompt = (
        "Jsi trpělivý učitel matematiky. Třináctiletému žákovi vysvětli jednoduše, "
        "krok za krokem, řešení této úlohy:\n\n"
        f"{req.zadani}\n\n"
        f"Oficiální postup:\n{kroky}\n\n"
        "Vysvětli to vlastními slovy, jednodušeji než oficiální postup, klidně s příkladem "
        "ze života. Piš česky, stručně (maximálně 8 vět), bez markdown formátování."
    )
    return {"text": await claude(prompt)}
