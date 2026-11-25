"""Regras que DESCARTAM uma vaga. motivo_descarte() devolve o motivo, ou None se a vaga passou."""
import re

from fontes.base import Vaga
from regex_util import achar, normalizar


def motivo_descarte(v: Vaga, cfg: dict) -> str | None:
    f, p = cfg["filtros"], cfg["palavras"]
    texto = v.texto_completo
    titulo_empresa = f"{v.titulo} {v.empresa}"

    # 1. Plataformas bloqueadas (Workana)
    if achar(f["plataformas_bloqueadas"], f"{v.link} {v.empresa} {v.fonte}"):
        return "Plataforma bloqueada (Workana)"

    # 2. Golpes
    if m := achar(f["golpe"], texto):
        return f"Possível golpe: '{m.group(0)}'"

    # 3. Corretora de seguros (conflito de interesse). Domain expert em empresa de IA é permitido.
    if m := achar(f["corretora_empresa"], v.empresa):
        return f"Empresa é corretora de seguros: '{m.group(0)}'"
    if (m := achar(f["corretora_cargo"], v.titulo)) and not achar(f["corretora_excecao"], v.titulo):
        return f"Vaga de corretora de seguros: '{m.group(0)}'"

    # 4. Localização (campo 'local' da API). Atenção: algumas APIs marcam "remote" mas exigem
    #    morar na cidade listada (ex.: RWS "Amsterdam" + remote), por isso só vale o texto do local.
    local = v.local.strip()
    brasil_no_local = bool(achar(p["brasil_latam"] + p["cidades_brasil"], local))
    if local and not brasil_no_local:
        if achar(f["locais_estrangeiros"], local):
            return f"Local fora do Brasil: {local[:80]}"
        if not achar(p["remoto"], local):
            return f"Local fora do Brasil / não remota: {local[:80]}"

    # 5. Restrição de país escrita no texto ("US only", "must reside in USA")
    if not brasil_no_local and (m := achar(f["restricao_pais"], texto)):
        return f"Restrita a outro país: '{m.group(0)[:60]}'"

    # 6. Presencial / híbrida
    modalidade = re.sub(r"[^a-z]", "", normalizar(v.modalidade))
    if modalidade in {"onsite", "hybrid", "inoffice"}:
        return f"Presencial/híbrida ({v.modalidade})"
    if m := achar(f["presencial"], f"{v.titulo} {v.descricao}"):
        return f"Presencial: '{m.group(0)}'"

    # 7. Horário comercial fixo
    if m := achar(f["horario_fixo"], texto):
        return f"Horário fixo: '{m.group(0)}'"

    # 8. Tempo integral (só quando a API diz isso e o texto não fala em flexibilidade)
    jornada = re.sub(r"[^a-z]", "", normalizar(v.jornada))
    if f.get("descartar_tempo_integral") and jornada == "fulltime" and not achar(p["flexivel"], texto):
        return "Tempo integral"

    return None
