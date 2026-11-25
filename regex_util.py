"""Ajudantes para usar as listas de palavras-chave do config.yaml."""
import re
from functools import lru_cache

TRACOS = dict.fromkeys(map(ord, "‐‑‒–—−"), "-")
ESPACOS = dict.fromkeys(map(ord, "    "), " ")


def normalizar(texto: str) -> str:
    """Troca traços e espaços 'especiais' por comuns e passa para minúsculas."""
    return (texto or "").translate(TRACOS).translate(ESPACOS).lower()


@lru_cache(maxsize=None)
def _compilar(padroes: tuple[str, ...]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in padroes), re.IGNORECASE)


def achar(padroes: list[str], texto: str) -> re.Match | None:
    """Primeira ocorrência de qualquer padrão da lista no texto (ou None)."""
    if not padroes or not texto:
        return None
    return _compilar(tuple(padroes)).search(normalizar(texto))
