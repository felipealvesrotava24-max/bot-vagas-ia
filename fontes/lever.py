"""Lever: https://api.lever.co/v0/postings/{token}?mode=json"""
from .base import ClienteHttp, Vaga, html_para_texto, ler_data

URL = "https://api.lever.co/v0/postings/{token}?mode=json"


def buscar(fonte: dict, http: ClienteHttp) -> list[Vaga]:
    vagas = []
    for j in http.get(URL.format(token=fonte["token"])).json():
        cat = j.get("categories") or {}
        locais = [cat.get("location", "")] + list(cat.get("allLocations") or [])
        listas = " ".join(f"{l.get('text', '')}: {html_para_texto(l.get('content'))}" for l in j.get("lists") or [])
        salario = j.get("salaryRange") or {}
        extra = ""
        if salario.get("min"):
            extra = f"{salario.get('currency', '')} {salario.get('min')}-{salario.get('max')} {salario.get('interval', '')}"
        vagas.append(Vaga(
            empresa=fonte["nome"],
            titulo=j.get("text", "").strip(),
            link=j.get("hostedUrl", ""),
            fonte=fonte["nome"],
            local="; ".join(dict.fromkeys(x for x in locais if x)),
            descricao=" ".join([j.get("descriptionPlain", ""), listas, j.get("additionalPlain", "")]).strip(),
            publicada=ler_data(j.get("createdAt")),
            modalidade=j.get("workplaceType", "") or "",
            jornada=cat.get("commitment", "") or "",
            extra=extra,
        ))
    return vagas
