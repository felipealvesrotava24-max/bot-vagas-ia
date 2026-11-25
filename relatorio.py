"""Gera vagas.html: todas as vagas ativas, da maior para a menor nota."""
import html
from datetime import datetime
from zoneinfo import ZoneInfo

MODELO = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vagas de IA</title>
<style>
  :root {{ color-scheme: light dark; --borda: #8884; }}
  body {{ font: 15px/1.45 system-ui, sans-serif; max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ margin: 0 0 .25rem; font-size: 1.5rem; }}
  .sub {{ opacity: .7; margin: 0 0 1.25rem; }}
  input {{ width: 100%; padding: .55rem .75rem; font: inherit; border: 1px solid var(--borda); border-radius: 8px;
          background: transparent; color: inherit; margin-bottom: 1rem; box-sizing: border-box; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--borda); vertical-align: top; }}
  th {{ font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; opacity: .7; }}
  td.n {{ font-weight: 700; font-variant-numeric: tabular-nums; }}
  .alta {{ color: #1a7f37; }} .media {{ color: #9a6700; }} .baixa {{ opacity: .6; }}
  .motivos {{ font-size: .8rem; opacity: .7; }}
  a {{ color: inherit; }}
</style></head><body>
<h1>Vagas de IA para você</h1>
<p class="sub">{total} vagas ativas · atualizado em {quando} (Brasília)</p>
<input id="busca" placeholder="Filtrar por título, empresa, idioma..." oninput="filtrar(this.value)">
<table><thead><tr><th>Nota</th><th>Vaga</th><th>Empresa</th><th>Idioma</th><th>Valor</th><th>Publicada</th><th>Local</th></tr></thead>
<tbody>
{linhas}
</tbody></table>
<script>
function filtrar(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('tbody tr').forEach(tr => tr.hidden = !tr.textContent.toLowerCase().includes(q));
}}
</script>
</body></html>
"""


def resumo_markdown(top, fontes: dict) -> str:
    """Top N + situação das fontes, em Markdown (aparece na página da execução do GitHub Actions)."""
    limpar = lambda s: (s or "—").replace("|", "/")
    linhas = ["## 🤖 Top vagas de IA", "", "| Nota | Vaga | Empresa | Idioma | Valor | Publicada |",
              "|---|---|---|---|---|---|"]
    for v in top:
        pub = f"{v['publicada'][8:10]}/{v['publicada'][5:7]}/{v['publicada'][:4]}" if v["publicada"] else "—"
        linhas.append(f"| **{v['nota']}** | [{limpar(v['titulo'])}]({v['link']}) | {limpar(v['empresa'])} | "
                      f"{limpar(v['idioma'])} | {limpar(v['valor_txt'])} | {pub} |")
    linhas += ["", "### Fontes", "", "| Fonte | Vagas | Aprovadas | Novas |", "|---|---|---|---|"]
    for nome, r in fontes.items():
        linhas.append(f"| {nome} | ❌ {limpar(r['erro'])} | | |" if "erro" in r
                      else f"| {nome} | {r['total']} | {r['aprovadas']} | {r['novas']} |")
    return "\n".join(linhas) + "\n"


def gerar(vagas, caminho: str = "vagas.html") -> str:
    e = html.escape
    linhas = []
    for v in vagas:
        classe = "alta" if v["nota"] >= 70 else "media" if v["nota"] >= 40 else "baixa"
        pub = v["publicada"][:10] if v["publicada"] else "—"
        linhas.append(
            f'<tr><td class="n {classe}">{v["nota"]}</td>'
            f'<td><a href="{e(v["link"], quote=True)}" target="_blank" rel="noopener">{e(v["titulo"])}</a>'
            f'<div class="motivos">{e(v["motivos"] or "")}</div></td>'
            f'<td>{e(v["empresa"])}</td><td>{e(v["idioma"] or "—")}</td><td>{e(v["valor_txt"] or "—")}</td>'
            f'<td>{pub}</td><td>{e((v["local"] or "—")[:60])}</td></tr>')
    quando = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(MODELO.format(total=len(vagas), quando=quando, linhas="\n".join(linhas)))
    return caminho
