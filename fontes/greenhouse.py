"""Greenhouse: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"""
from .base import ClienteHttp, Vaga, html_para_texto, ler_data

URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"


def buscar(fonte: dict, http: ClienteHttp) -> list[Vaga]:
    dados = http.get(URL.format(token=fonte["token"])).json()
    vagas = []
    for j in dados.get("jobs", []):
        locais = [(j.get("location") or {}).get("name", "")]
        locais += [o.get("name", "") for o in j.get("offices", []) or []]
        vagas.append(Vaga(
            empresa=fonte["nome"],
            titulo=j.get("title", "").strip(),
            link=j.get("absolute_url", ""),
            fonte=fonte["nome"],
            local="; ".join(dict.fromkeys(x for x in locais if x)),
            descricao=html_para_texto(j.get("content")),
            publicada=ler_data(j.get("first_published") or j.get("updated_at")),
        ))
    return vagas
