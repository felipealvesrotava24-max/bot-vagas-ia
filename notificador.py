"""Envio pelo Telegram (API HTTP direta, sem bibliotecas extras).

Precisa das variáveis de ambiente TELEGRAM_TOKEN e TELEGRAM_CHAT_ID.
Sem elas, as mensagens só são mostradas no terminal (modo teste).
"""
import html
import logging
import os

import requests

log = logging.getLogger(__name__)
LIMITE = 4000  # o Telegram aceita até 4096 caracteres por mensagem


def _data(valor: str | None) -> str:
    return f"{valor[8:10]}/{valor[5:7]}/{valor[:4]}" if valor else "—"


def formatar_vaga(v, posicao: int | None = None) -> str:
    e = html.escape
    cab = f"{posicao}. " if posicao else ""
    return (f"{cab}<b>[{v['nota']}] {e(v['titulo'])}</b>\n"
            f"🏢 {e(v['empresa'])} · 🗣 {e(v['idioma'] or '—')} · 💵 {e(v['valor_txt'] or 'não informado')}\n"
            f"📅 {_data(v['publicada'])} · <a href=\"{e(v['link'], quote=True)}\">abrir vaga</a>")


def montar_resumo(vagas) -> list[str]:
    if not vagas:
        return ["🤖 <b>Vagas de IA</b>\nNenhuma vaga nova acima da nota mínima hoje."]
    blocos = [f"🤖 <b>Top {len(vagas)} vagas de IA de hoje</b>"]
    blocos += [formatar_vaga(v, i) for i, v in enumerate(vagas, 1)]
    return _dividir(blocos)


def montar_alerta(v) -> str:
    return "🚨 <b>Vaga com nota alta!</b>\n\n" + formatar_vaga(v)


def _dividir(blocos: list[str]) -> list[str]:
    msgs, atual = [], ""
    for b in blocos:
        if len(atual) + len(b) + 2 > LIMITE:
            msgs.append(atual)
            atual = ""
        atual = f"{atual}\n\n{b}" if atual else b
    return msgs + [atual] if atual else msgs


def enviar(texto: str) -> bool:
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.warning("TELEGRAM_TOKEN/TELEGRAM_CHAT_ID não configurados: mostrando a mensagem só no terminal.")
        print("\n----- MENSAGEM (não enviada) -----\n" + texto + "\n----------------------------------")
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=30, data={
            "chat_id": chat, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": "true"})
        if not r.ok:
            log.error("Telegram recusou a mensagem: %s %s", r.status_code, r.text[:200])
        return r.ok
    except requests.RequestException as e:
        log.error("Falha ao enviar para o Telegram: %s", e)
        return False
