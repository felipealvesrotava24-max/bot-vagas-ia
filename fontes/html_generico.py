"""Páginas públicas de vagas (HTML) e feeds RSS, para empresas sem API.

No config.yaml:
  tipo: html  -> url + padrao_link (trecho que todo link de vaga contém)
                 ignorar_link (opcional, regex de links a pular)
  tipo: rss   -> url do feed
"""
import re
from urllib.parse import urljoin

import defusedxml.ElementTree as ET  # versão segura do leitor de XML
from bs4 import BeautifulSoup

from .base import ClienteHttp, Vaga, html_para_texto, ler_data


def buscar(fonte: dict, http: ClienteHttp) -> list[Vaga]:
    r = http.get(fonte["url"])
    sopa = BeautifulSoup(r.content, "html.parser")  # .content: deixa o BS detectar a codificação
    padrao = fonte["padrao_link"]
    ignorar = re.compile(fonte["ignorar_link"]) if fonte.get("ignorar_link") else None
    por_link: dict[str, Vaga] = {}
    for a in sopa.find_all("a", href=True):
        link = urljoin(fonte["url"], a["href"]).split("#")[0]
        if padrao not in link or link.rstrip("/") == fonte["url"].rstrip("/"):
            continue
        if ignorar and ignorar.search(link):
            continue
        texto = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if len(texto) < 6 or texto.lower() in {"apply", "apply now", "view", "learn more"}:
            continue
        if link in por_link:                       # mesmo link repetido: fica o texto mais longo
            if len(texto) > len(por_link[link].descricao):
                por_link[link].descricao = texto
            continue
        titulo = _titulo(a, texto)
        por_link[link] = Vaga(empresa=fonte["nome"], titulo=titulo, link=link,
                              fonte=fonte["nome"], descricao=texto)
    return list(por_link.values())


def _titulo(a, texto: str) -> str:
    """Usa o primeiro cabeçalho dentro do link; senão, o começo do texto."""
    cab = a.find(["h1", "h2", "h3", "h4", "h5", "strong"])
    if cab and cab.get_text(strip=True):
        return cab.get_text(" ", strip=True)[:150]
    return texto[:120]


def buscar_rss(fonte: dict, http: ClienteHttp) -> list[Vaga]:
    raiz = ET.fromstring(http.get(fonte["url"]).content)
    vagas = []
    for item in raiz.iter("item"):
        vagas.append(Vaga(
            empresa=fonte["nome"],
            titulo=(item.findtext("title") or "").strip(),
            link=(item.findtext("link") or "").strip(),
            fonte=fonte["nome"],
            descricao=html_para_texto(item.findtext("description")),
            publicada=_data_rss(item.findtext("pubDate")),
        ))
    return vagas


def _data_rss(texto):
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(texto) if texto else None
    except (TypeError, ValueError):
        return ler_data(texto)
