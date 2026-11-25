"""Peças comuns a todas as fontes: o modelo Vaga e um cliente HTTP educado."""
from __future__ import annotations

import hashlib
import html
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


@dataclass
class Vaga:
    empresa: str
    titulo: str
    link: str
    fonte: str                      # nome da fonte no config.yaml
    local: str = ""                 # texto de localização (cidade, país, "Remote"...)
    descricao: str = ""             # texto puro da descrição
    publicada: datetime | None = None
    modalidade: str = ""            # remote / onsite / hybrid, quando a API informa
    jornada: str = ""               # full-time / part-time / contract, quando a API informa
    extra: str = ""                 # outros textos úteis (ex.: faixa salarial da API)
    # preenchidos depois pela pontuação
    nota: int = 0
    idioma: str = ""
    valor_hora: float | None = None
    valor_txt: str = ""
    motivos: list[str] = field(default_factory=list)

    @property
    def hash(self) -> str:
        chave = f"{self.empresa}|{self.titulo}|{self.link}".lower().strip()
        return hashlib.sha1(chave.encode("utf-8")).hexdigest()

    @property
    def texto_completo(self) -> str:
        return " \n ".join([self.titulo, self.local, self.modalidade, self.jornada, self.extra, self.descricao])


def html_para_texto(conteudo: str | None) -> str:
    """Converte HTML (às vezes 'escapado', como no Greenhouse) em texto puro."""
    if not conteudo:
        return ""
    texto = BeautifulSoup(html.unescape(conteudo), "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", texto).strip()


def ler_data(valor) -> datetime | None:
    """Aceita ISO 8601 ('2025-06-13T21:37:36-04:00') ou milissegundos (Lever)."""
    if valor in (None, ""):
        return None
    try:
        if isinstance(valor, (int, float)):
            return datetime.fromtimestamp(valor / 1000, tz=timezone.utc)
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OSError):
        return None


class ClienteHttp:
    """requests com User-Agent identificado, robots.txt respeitado e pausa por domínio."""

    def __init__(self, user_agent: str, intervalo: float = 2.0, timeout: int = 30):
        self.sessao = requests.Session()
        self.sessao.headers["User-Agent"] = user_agent
        self.user_agent = user_agent
        self.intervalo = intervalo
        self.timeout = timeout
        self._ultimo: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    def _esperar(self, dominio: str) -> None:
        passou = time.monotonic() - self._ultimo.get(dominio, 0)
        if passou < self.intervalo:
            time.sleep(self.intervalo - passou)
        self._ultimo[dominio] = time.monotonic()

    def permitido(self, url: str) -> bool:
        """Segue a RFC 9309: robots.txt 4xx = sem regras (liberado); 5xx/erro = bloqueado."""
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            self._esperar(p.netloc)
            try:
                r = self.sessao.get(base + "/robots.txt", timeout=self.timeout)
                if r.status_code >= 500:
                    self._robots[base] = RobotFileParser()
                    self._robots[base].disallow_all = True
                elif r.status_code >= 400:
                    self._robots[base] = None
                else:
                    rp = RobotFileParser()
                    rp.parse(r.text.splitlines())
                    self._robots[base] = rp
            except requests.RequestException as e:
                log.warning("Não consegui ler robots.txt de %s (%s); por segurança, não acesso.", base, e)
                rp = RobotFileParser()
                rp.disallow_all = True
                self._robots[base] = rp
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    def get(self, url: str, **kw) -> requests.Response:
        if not self.permitido(url):
            raise PermissionError(f"robots.txt não permite acessar {url}")
        self._esperar(urlparse(url).netloc)
        r = self.sessao.get(url, timeout=self.timeout, **kw)
        r.raise_for_status()
        return r
