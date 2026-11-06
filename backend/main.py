"""
Elektro akademie – AI zkoušející z matiky (backend pro Railway)

Malý FastAPI server, který drží Anthropic API klíč a přeposílá požadavky
z frontendu (GitHub Pages). Klíč tak nikdy neopustí server.

Novinky oproti první verzi:
  - víc témat úloh, GET /api/temata vrací jejich seznam (frontend z nich nabízí výběr)
  - kontrola výsledků: AI ke každé úloze vrací i "vypocet" (čistý číselný výraz).
    Server ho sám spočítá a úlohu pustí ven jen tehdy, když výsledek sedí.
    Jinak ji zahodí a nechá AI vymyslet novou (max. 3 pokusy).

Env proměnné:
  ANTHROPIC_API_KEY  (povinná)  – klíč z console.anthropic.com
  AI_MODEL           (volitelná) – výchozí claude-haiku-4-5-20251001
  ALLOWED_ORIGINS    (volitelná) – čárkou oddělené originy, výchozí "*"
                       (po nasazení doporučeno zúžit na https://UZIVATEL.github.io)
  DAILY_LIMIT        (volitelná) – max. počet AI dotazů za den, výchozí 300

Start: uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import ast
import json
import math
import operator
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
MAX_POKUSU = 3  # kolikrát nechat AI vymyslet úlohu znovu, když nesedí výsledek

app = FastAPI(title="Elektro akademie – AI zkoušející")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- jednoduchý denní limit (ochrana peněženky) -----------------------------
_usage = {"day": date.today(), "count": 0}


def check_limit(cost: int = 1) -> None:
    if _usage["day"] != date.today():
        _usage["day"] = date.today()
        _usage["count"] = 0
    if _usage["count"] >= DAILY_LIMIT:
        raise HTTPException(429, "Denní limit AI dotazů vyčerpán, zkus to zítra.")
    _usage["count"] += cost


# --- témata úloh -------------------------------------------------------------
TEMATA = {
    "78": [
        "lineární rovnice o jedné neznámé",
        "zlomky – sčítání a násobení",
        "desetinná čísla a zaokrouhlování",
        "procenta (sleva, DPH, úrok)",
        "obvod a obsah obdélníku nebo trojúhelníku",
        "obvod a obsah kruhu (počítej s π = 3,14)",
        "úhly v trojúhelníku a vedlejší a vrcholové úhly",
        "převody jednotek (délka, hmotnost, čas, objem)",
        "přímá a nepřímá úměrnost, trojčlenka",
        "mocniny a druhá odmocnina",
        "dělitelnost, nejmenší společný násobek a největší společný dělitel",
        "aritmetický průměr",
        "slovní úloha o penězích nebo nákupu",
    ],
    "9": [
        "slovní úloha vedoucí na lineární rovnici (styl přijímaček CERMAT)",
        "jednoduchá soustava dvou rovnic",
        "úpravy výrazů a dosazení do výrazu",
        "Pythagorova věta v praktické situaci",
        "procenta a promile ve slovní úloze",
        "poměr a měřítko mapy",
        "obvod a obsah kruhu a složených obrazců (počítej s π = 3,14)",
        "objem a povrch kvádru nebo válce (počítej s π = 3,14)",
        "slovní úloha o pohybu nebo společné práci",
        "mocniny s přirozeným exponentem a druhá odmocnina",
        "aritmetický průměr a čtení dat z tabulky zapsané v zadání",
        "nepřímá úměrnost ve slovní úloze",
    ],
}
LEVEL_TXT = {
    "78": "žáka 7.–8. třídy základní školy",
    "9": "deváťáka, který se připravuje na přijímačky na střední školu (obtížnost testů CERMAT)",
}
VEK_TXT = {"78": "Třináctiletému", "9": "Patnáctiletému"}


class UlohaReq(BaseModel):
    obtiznost: str = "78"
    tema: int | None = None  # index do TEMATA[obtiznost]; None = náhodné téma


class VysvetliReq(BaseModel):
    zadani: str
    kroky: list[str] = []
    uroven: str = "78"


# --- bezpečný výpočet číselného výrazu (žádné eval) --------------------------
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNKCE = {"sqrt": math.sqrt}


def spocitej(vyraz: str) -> float:
    """Spočítá výraz jen z čísel, + - * / **, závorek a sqrt(). Cokoli jiného odmítne."""
    vyraz = str(vyraz).strip().replace("^", "**").replace("·", "*").replace("×", "*").replace(":", "/")
    if not vyraz or len(vyraz) > 200:
        raise ValueError("Výraz je prázdný nebo moc dlouhý.")
    strom = ast.parse(vyraz, mode="eval")

    def ev(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _BINOPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and (abs(b) > 10 or abs(a) > 1e6):
                raise ValueError("Mocnina je mimo rozumný rozsah.")
            return _BINOPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UNOPS:
            return _UNOPS[type(n.op)](ev(n.operand))
        if (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id in _FUNKCE
            and len(n.args) == 1
            and not n.keywords
        ):
            return _FUNKCE[n.func.id](ev(n.args[0]))
        raise ValueError("Ve výrazu je něco jiného než čísla a základní operace.")

    hodnota = ev(strom)
    if not math.isfinite(hodnota):
        raise ValueError("Výsledek výrazu není konečné číslo.")
    return hodnota


def na_cislo(x) -> float:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    return float(s)


def zkontroluj_ulohu(data: dict) -> dict:
    """Ověří úplnost úlohy a že výpočet opravdu dává uvedený výsledek. Vrátí úlohu pro frontend."""
    zadani = str(data.get("zadani", "")).strip()
    kroky = data.get("kroky")
    if not zadani or not isinstance(kroky, list) or not (2 <= len(kroky) <= 6):
        raise ValueError("Neúplná úloha.")
    if "vysledek" not in data or "vypocet" not in data:
        raise ValueError("Chybí výsledek nebo výpočet.")
    vysledek = na_cislo(data["vysledek"])
    spocteno = spocitej(data["vypocet"])
    if not math.isclose(spocteno, vysledek, rel_tol=0.005, abs_tol=0.011):
        raise ValueError(f"Výpočet {data['vypocet']} = {spocteno} nesedí s výsledkem {vysledek}.")
    return {
        "zadani": zadani,
        "vysledek": f"{vysledek:.10g}",
        "jednotka": str(data.get("jednotka", "") or "").strip(),
        "kroky": [str(k).strip() for k in kroky if str(k).strip()],
    }


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
    return {"ok": True, "sluzba": "Elektro akademie – AI zkoušející", "verze": 2}


@app.get("/api/temata")
async def temata():
    return TEMATA


@app.post("/api/uloha")
async def uloha(req: UlohaReq):
    check_limit()
    lvl = req.obtiznost if req.obtiznost in TEMATA else "78"
    if req.tema is not None and 0 <= req.tema < len(TEMATA[lvl]):
        tema = TEMATA[lvl][req.tema]
    else:
        tema = random.choice(TEMATA[lvl])
    prompt = (
        f"Vytvoř jednu matematickou úlohu pro {LEVEL_TXT[lvl]}. Téma: {tema}. "
        "Odpověz POUZE platným JSON objektem bez jakéhokoli dalšího textu a bez markdown, "
        "přesně v tomto tvaru: "
        '{"zadani": "text úlohy česky", '
        '"vysledek": "konečný výsledek jako číslo s desetinnou tečkou, bez jednotky", '
        '"jednotka": "jednotka výsledku, nebo prázdný řetězec", '
        '"vypocet": "jeden číselný výraz, který dá přesně výsledek", '
        '"kroky": ["krok 1", "krok 2", "krok 3"]} '
        "Pravidla: výsledek musí být jediné jednoznačné číslo, zaokrouhlené nejvýš na 2 desetinná místa; "
        "\"vypocet\" smí obsahovat jen čísla s desetinnou tečkou, + - * / **, závorky a sqrt(), "
        "žádná písmena ani jednotky, a musí vycházet ze zadání (například \"(1200 - 1200*0.15)*1.21\"); "
        "když počítáš s π, napiš do výpočtu 3.14; "
        "kroky jsou 3 až 5 srozumitelných kroků řešení a poslední krok obsahuje výsledek; "
        "zadání je krátké, jasné a v zadání výslovně řekni, v jaké jednotce má žák odpovědět."
    )
    for _ in range(MAX_POKUSU):
        try:
            return zkontroluj_ulohu(parse_json(await claude(prompt)))
        except (ValueError, TypeError, SyntaxError, ZeroDivisionError, OverflowError, json.JSONDecodeError):
            continue
    raise HTTPException(502, "AI nevrátila úlohu se správně spočítaným výsledkem, zkus to znovu.")


@app.post("/api/vysvetli")
async def vysvetli(req: VysvetliReq):
    check_limit()
    lvl = req.uroven if req.uroven in VEK_TXT else "78"
    kroky = "\n".join(f"- {k}" for k in req.kroky[:8])
    prompt = (
        f"Jsi trpělivý učitel matematiky. {VEK_TXT[lvl]} žákovi vysvětli jednoduše, "
        "krok za krokem, řešení této úlohy:\n\n"
        f"{req.zadani[:1500]}\n\n"
        f"Oficiální postup:\n{kroky}\n\n"
        "Vysvětli to vlastními slovy, jednodušeji než oficiální postup, klidně s příkladem "
        "ze života. Piš česky, stručně (maximálně 8 vět), bez markdown formátování."
    )
    return {"text": await claude(prompt)}
