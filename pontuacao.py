"""Dá uma nota de 0 a 100 para cada vaga, com os pesos do config.yaml."""
import re
from datetime import datetime, timedelta, timezone

from fontes.base import Vaga
from regex_util import achar, normalizar

# ---------------- valor por hora ----------------
_NUM = r"(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_MOEDA = r"(r\$|us\$|usd|\$)"
_SEP = r"\s*(?:-\s*to\s*-|-|to|a|até|and)\s*"
_UNIDADE = r"(?:/\s*(?:hr|hour|hora|h)\b|per\s+hour|an\s+hour|hourly|por\s+hora|a\s+hora|/\s*hora)"

# "$25/hr", "$8-to-$65 per hour", "US$ 20 – 40 por hora", "Up to $150+ / hr"
RE_MOEDA_ANTES = re.compile(
    rf"{_MOEDA}\s*{_NUM}\s*\+?(?:{_SEP}(?:r\$|us\$|usd|\$)?\s*{_NUM}\s*\+?)?\s*(?:usd)?\s*{_UNIDADE}")
# "7 USD per hour", "50 reais por hora"
RE_MOEDA_DEPOIS = re.compile(
    rf"{_NUM}(?:{_SEP}{_NUM})?\s*(usd|dólares|dolares|brl|reais)\s*{_UNIDADE}")


def _numero(txt: str) -> float:
    if "," in txt and "." in txt:                  # 1,600.50 ou 1.600,50
        if txt.rfind(",") > txt.rfind("."):
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    elif "," in txt or "." in txt:
        sep = "," if "," in txt else "."
        inteiro, _, dec = txt.rpartition(sep)
        txt = f"{inteiro.replace(sep, '')}{'' if len(dec) == 3 else '.'}{dec}"
    return float(txt)


def extrair_valor_hora(texto: str, cfg: dict) -> tuple[float, float] | None:
    """Devolve (mínimo, máximo) em US$/hora, ou None se não achar valor por hora."""
    t = normalizar(texto)
    achados = []
    for m in RE_MOEDA_ANTES.finditer(t):
        achados.append((m.start(), m.group(1), m.group(2), m.group(3)))
    for m in RE_MOEDA_DEPOIS.finditer(t):
        achados.append((m.start(), m.group(3), m.group(1), m.group(2)))
    if not achados:
        return None
    _, moeda, a, b = min(achados)                  # o primeiro que aparece no texto
    lo = _numero(a)
    hi = _numero(b) if b else lo
    if moeda in {"r$", "brl", "reais"}:
        lo, hi = lo / cfg["cambio_brl_usd"], hi / cfg["cambio_brl_usd"]
    lo, hi = round(min(lo, hi), 2), round(max(lo, hi), 2)
    return lo, hi


def _formatar(lo: float, hi: float) -> str:
    f = lambda x: f"{x:g}"
    return f"US$ {f(lo)}/h" if lo == hi else f"US$ {f(lo)}–{f(hi)}/h"


# ---------------- nota ----------------
def pontuar(v: Vaga, cfg: dict) -> Vaga:
    w, p = cfg["pesos"], cfg["palavras"]
    texto = v.texto_completo
    nota, motivos = 0, []

    def soma(pontos: int, motivo: str):
        nonlocal nota
        nota += pontos
        motivos.append(f"{motivo} {pontos:+d}")

    # Idioma
    brasil = achar(p["brasil_latam"] + p["cidades_brasil"], texto)
    pt = achar(p["portugues_br_explicito"], texto) or (
        achar(p["portugues"], texto) and not achar(p["portugal"], texto))
    es = achar(p["espanhol"], texto)
    if pt and es:
        v.idioma = "PT+ES"
        soma(w["multilingue_pt_es"], "PT+ES")
    elif pt:
        v.idioma = "PT-BR"
        soma(w["portugues_br"], "PT-BR")
    elif es:
        v.idioma = "ES"
        soma(w["espanhol"], "ES")
    else:
        v.idioma = "—"

    if brasil:
        soma(w["elegivel_brasil_latam"], "Brasil/LATAM")

    # Valor por hora
    faixa = extrair_valor_hora(f"{v.extra} \n {v.titulo} \n {v.descricao}", cfg)
    if faixa:
        lo, hi = faixa
        ref = {"minimo": lo, "maximo": hi}.get(cfg.get("valor_referencia"), (lo + hi) / 2)
        v.valor_hora, v.valor_txt = round(ref, 2), _formatar(lo, hi)
        if ref >= cfg["valor_alto_min"]:
            soma(w["valor_alto"], f"valor {v.valor_txt}")
        elif ref >= cfg["valor_medio_min"]:
            soma(w["valor_medio"], f"valor {v.valor_txt}")
    else:
        v.valor_hora, v.valor_txt = None, "não informado"

    if m := achar(p["dominio"], f"{v.titulo} {v.descricao}"):
        soma(w["dominio"], f"domínio '{m.group(0)}'")
    if achar(p["flexivel"], texto):
        soma(w["flexivel"], "flexível")
    if v.publicada and datetime.now(timezone.utc) - v.publicada < timedelta(days=cfg["dias_recente"]):
        soma(w["recente"], "recente")
    if achar(p["ingles_fluente"], texto):
        soma(w["ingles_fluente"], "inglês fluente")
    if v.idioma == "—" and (m := achar(p.get("outro_idioma", []), v.titulo)):
        soma(w.get("outro_idioma", 0), f"exige {m.group(0)}")

    v.nota = max(0, min(100, nota))
    v.motivos = motivos
    return v
