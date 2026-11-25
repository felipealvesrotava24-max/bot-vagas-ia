from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from filtros import motivo_descarte
from fontes.base import Vaga
from pontuacao import extrair_valor_hora, pontuar

CFG = yaml.safe_load((Path(__file__).parent.parent / "config.yaml").read_text(encoding="utf-8"))


def vaga(**kw):
    base = dict(empresa="Meridial", titulo="AI Trainer", link="https://x/1", fonte="Meridial", local="Remote")
    base.update(kw)
    return Vaga(**base)


# ---------------- parser de salário ----------------
@pytest.mark.parametrize("texto, esperado", [
    ("Pay: $25/hr", (25, 25)),
    ("$8‑to‑$65 per hour, with the exact rate", (8, 65)),   # hífen especial do Meridial
    ("Rate: 7 USD per hour (rates vary)", (7, 7)),
    ("US$ 20 – 40 por hora", (20, 40)),
    ("Up to $150+ / hr", (150, 150)),
    ("up to $ 110 /hr", (110, 110)),
    ("R$ 54/hora", (10, 10)),                                           # 54 / 5.40
    ("USD 15.50 hourly", (15.5, 15.5)),
])
def test_extrai_valor_hora(texto, esperado):
    r = extrair_valor_hora(texto, CFG)
    assert r is not None
    assert r[0] == pytest.approx(esperado[0], abs=0.01) and r[1] == pytest.approx(esperado[1], abs=0.01)


@pytest.mark.parametrize("texto", ["$120K – $200K • Offers Equity", "Up to $1,600 total", "Sem valor informado"])
def test_ignora_valores_que_nao_sao_por_hora(texto):
    assert extrair_valor_hora(texto, CFG) is None


# ---------------- filtros ----------------
def test_aceita_vaga_remota_brasil():
    assert motivo_descarte(vaga(local="Brazil", titulo="Coding Specialist (Fluent in Portuguese - Brazil)"), CFG) is None


@pytest.mark.parametrize("kw, motivo", [
    (dict(local="United States of America"), "local"),
    (dict(local="Remote", descricao="This role is US only."), "país"),
    (dict(local="Mexico City", descricao="Location: Must be located in Mexico"), "local"),
    (dict(local="Remote", descricao="Job Type: Freelance. Location: Must be located in Mexico"), "país"),
    (dict(local="Remote", modalidade="OnSite"), "presencial"),
    (dict(local="Remote", descricao="Hours: Monday to Friday, 9am-5pm business hours"), "horário"),
    (dict(local="Remote", descricao="Pague para participar: taxa de inscrição de R$ 50"), "golpe"),
    (dict(local="Remote", descricao="A small registration fee is required"), "golpe"),
    (dict(local="Remote", empresa="XYZ Corretora de Seguros", fonte="XYZ"), "corretora"),
    (dict(local="Remote", titulo="Insurance Sales Agent"), "corretora"),
    (dict(local="Remote", link="https://www.workana.com/job/123"), "workana"),
    (dict(local="San Francisco", jornada="FullTime"), "local"),
    (dict(local="Remote", jornada="FullTime"), "integral"),
    (dict(local="Remote", titulo="Native Spanish Speaker (Dallas)", descricao="Dallas-based native Spanish speakers"), "país"),
    (dict(local="Amsterdam", modalidade="remote"), "local"),          # RWS: "remote" mas exige morar lá
    (dict(local="", descricao="Native European Portuguese speaker in London? Get paid"), "país"),
])
def test_descarta(kw, motivo):
    m = motivo_descarte(vaga(**kw), CFG)
    assert m is not None and motivo in m.lower()


def test_insurance_domain_expert_e_permitido():
    v = vaga(titulo="Insurance Domain Expert - AI Trainer", descricao="insurance broker experience is a plus")
    assert motivo_descarte(v, CFG) is None


def test_local_brasil_explicito_vence_lista_de_cidades():
    assert motivo_descarte(vaga(local="Rio de Janeiro, Rio de Janeiro; Curitiba, Parana"), CFG) is None


def test_html_sem_local_nao_e_descartado():
    assert motivo_descarte(vaga(local="", fonte="DataAnnotation"), CFG) is None


# ---------------- pontuação ----------------
def test_vaga_ideal_tira_nota_alta():
    v = vaga(local="Brazil", titulo="Insurance Specialist (Fluent in Portuguese - Brazil) - Freelance AI Trainer",
             descricao="Flexible, asynchronous, part-time. $30 per hour. Spanish is a plus.",
             publicada=datetime.now(timezone.utc) - timedelta(days=2))
    pontuar(v, CFG)
    # PT+ES 30 + Brasil 20 + valor 20 + domínio 15 + flexível 10 + recente 10 = 105 -> limite 100
    assert v.nota == 100
    assert v.idioma == "PT+ES"
    assert v.valor_hora == 30


def test_nota_baixa_sem_sinais():
    v = vaga(titulo="Generalist", descricao="Help us improve AI.")
    pontuar(v, CFG)
    assert v.nota == 0 and v.idioma == "—"


def test_ingles_fluente_desconta():
    a, b = vaga(descricao="Spanish speakers wanted."), vaga(descricao="Spanish speakers. Native English required.")
    pontuar(a, CFG), pontuar(b, CFG)
    assert a.nota - b.nota == 15


def test_valor_medio_e_portugal_nao_conta_como_ptbr():
    v = vaga(titulo="Coding Specialist (Fluent in Portuguese - Portugal)", descricao="$20 per hour")
    pontuar(v, CFG)
    assert v.idioma == "—"
    assert "valor" in " ".join(v.motivos)
    assert v.nota == 10 + 15  # valor médio + domínio (coding)


def test_portugues_europeu_nao_vira_ptbr_mesmo_citando_sao_paulo():
    v = vaga(titulo="Portuguese (Portugal) Google Workspace AI Reviewer",
             descricao="Native European Portuguese speaker living in São Paulo")
    pontuar(v, CFG)
    assert v.idioma == "—"


def test_ptbr_explicito_ganha_de_portugal():
    v = vaga(titulo="Translator Brazilian Portuguese <> European Portuguese")
    pontuar(v, CFG)
    assert v.idioma == "PT-BR"


def test_outro_idioma_desconta():
    a = vaga(titulo="Insurance Specialist - Freelance AI Trainer", descricao="$30 per hour")
    b = vaga(titulo="Insurance Specialist (Fluent in French) - Freelance AI Trainer", descricao="$30 per hour")
    pontuar(a, CFG), pontuar(b, CFG)
    assert a.nota - b.nota == 20


def test_nota_nunca_negativa():
    v = vaga(descricao="Native English speakers only")
    pontuar(v, CFG)
    assert v.nota == 0
