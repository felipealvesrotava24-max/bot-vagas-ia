"""Ashby: https://api.ashbyhq.com/posting-api/job-board/{token}"""
from .base import ClienteHttp, Vaga, ler_data

URL = "https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"


def buscar(fonte: dict, http: ClienteHttp) -> list[Vaga]:
    dados = http.get(URL.format(token=fonte["token"])).json()
    vagas = []
    for j in dados.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locais = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        modalidade = j.get("workplaceType") or ("Remote" if j.get("isRemote") else "")
        comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
        vagas.append(Vaga(
            empresa=fonte["nome"],
            titulo=j.get("title", "").strip(),
            link=j.get("jobUrl", ""),
            fonte=fonte["nome"],
            local="; ".join(dict.fromkeys(x for x in locais if x)),
            descricao=j.get("descriptionPlain", "") or "",
            publicada=ler_data(j.get("publishedAt")),
            modalidade=modalidade,
            jornada=j.get("employmentType", "") or "",
            extra=comp,
        ))
    return vagas
