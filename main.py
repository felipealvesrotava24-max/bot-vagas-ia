"""Bot de vagas de IA.

Uso:
  python main.py              coleta, pontua, manda alertas (nota >= 80) e gera vagas.html
  python main.py --resumo     faz tudo isso e também manda o Top 10 do dia no Telegram
  python main.py --teste      só coleta e mostra o resultado de cada fonte (não envia nada)
  python main.py --fonte Meridial   roda só uma fonte (útil para testar uma empresa nova)
"""
import argparse
import logging
import os
import sys
from collections import Counter
from pathlib import Path

import yaml

import notificador
import relatorio
from banco import Banco, agora
from filtros import motivo_descarte
from fontes import BUSCADORES
from fontes.base import ClienteHttp
from pontuacao import pontuar

PASTA = Path(__file__).parent
log = logging.getLogger("bot")


def carregar_config(caminho=PASTA / "config.yaml") -> dict:
    return yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))


def coletar(cfg: dict, banco: Banco, so_fonte: str | None = None) -> dict:
    http = ClienteHttp(cfg["user_agent"], cfg["intervalo_por_dominio"], cfg["timeout"])
    inicio = agora()
    resumo = {}
    for fonte in cfg["fontes"]:
        if so_fonte and fonte["nome"].lower() != so_fonte.lower():
            continue
        if not so_fonte and not fonte.get("ativo", True):
            continue
        nome = fonte["nome"]
        try:
            vagas = BUSCADORES[fonte["tipo"]](fonte, http)
        except Exception as e:  # uma fonte com problema não derruba as outras
            log.error("❌ %-22s falhou: %s", nome, e)
            resumo[nome] = {"erro": str(e)[:120]}
            continue

        aprovadas, descartes, novas = 0, Counter(), 0
        for v in vagas:
            if motivo := motivo_descarte(v, cfg):
                descartes[motivo.split(":")[0]] += 1
                continue
            pontuar(v, cfg)
            novas += banco.salvar(v, inicio)
            aprovadas += 1
        sumidas = banco.desativar_sumidas(nome, inicio)
        banco.commit()
        resumo[nome] = {"total": len(vagas), "aprovadas": aprovadas, "novas": novas,
                        "sumidas": sumidas, "descartes": dict(descartes.most_common(4))}
        log.info("✅ %-22s %4d vagas | %3d aprovadas | %3d novas | descartes: %s",
                 nome, len(vagas), aprovadas, novas, dict(descartes.most_common(3)) or "-")
    return resumo


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bot de vagas de IA")
    ap.add_argument("--resumo", action="store_true", help="envia o Top N do dia no Telegram")
    ap.add_argument("--teste", action="store_true", help="não envia nada pelo Telegram")
    ap.add_argument("--fonte", help="roda só a fonte com este nome")
    ap.add_argument("--banco", default=str(PASTA / "vagas.db"))
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")  # emojis e acentos no terminal do Windows

    cfg = carregar_config()
    banco = Banco(args.banco)
    resumo = coletar(cfg, banco, args.fonte)

    ok = [n for n, r in resumo.items() if "erro" not in r]
    log.info("Fontes OK: %d · com erro: %d", len(ok), len(resumo) - len(ok))

    relatorio.gerar(banco.ativas(), str(PASTA / "vagas.html"))
    log.info("Relatório gerado: vagas.html")
    if destino := os.getenv("GITHUB_STEP_SUMMARY"):   # página da execução no GitHub Actions
        with open(destino, "a", encoding="utf-8") as f:
            f.write(relatorio.resumo_markdown(banco.ativas()[:cfg["top_n"]], resumo))

    if args.teste:
        print("\nTop 10 atual (modo teste, nada foi enviado):")
        for i, v in enumerate(banco.ativas()[:10], 1):
            print(f"{i:2}. [{v['nota']:3}] {v['titulo'][:70]} | {v['empresa']} | {v['idioma']} | "
                  f"{v['valor_txt']} | {(v['publicada'] or '—')[:10]}\n      {v['link']}")
        return 0

    alertas = banco.para_alerta(cfg["nota_alerta"])
    enviados = [v["hash"] for v in alertas if notificador.enviar(notificador.montar_alerta(v))]
    banco.marcar(enviados, "alertada")
    banco.marcar(enviados, "enviada")
    if alertas:
        log.info("Alertas: %d de %d enviados", len(enviados), len(alertas))

    if args.resumo:
        top = banco.para_resumo(cfg["top_n"], cfg["nota_minima_resumo"])
        if all([notificador.enviar(m) for m in notificador.montar_resumo(top)]):
            banco.marcar([v["hash"] for v in top], "enviada")
        log.info("Resumo diário: %d vagas", len(top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
