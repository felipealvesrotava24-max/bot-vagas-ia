# 🤖 Bot de vagas freelance em IA

Todo dia o bot busca vagas de treinamento e avaliação de IA em 16 fontes. Ele descarta as que não servem para você
(fora do Brasil, presenciais, golpes, corretoras de seguros, Workana), dá uma nota de 0 a 100 de acordo com o seu
perfil e envia as melhores no Telegram.

- **Às 17h (Brasília):** envia as 10 vagas novas com maior nota.
- **A cada 3 horas:** se aparecer uma vaga com nota **≥ 80**, manda um alerta na hora.
- **vagas.html:** relatório com todas as vagas ativas, com campo de busca.
- **Sem repetir:** o banco `vagas.db` guarda o que já foi enviado.

**Sem Telegram?** O bot funciona do mesmo jeito. Abra a aba **Actions** do repositório e clique na execução mais
recente: o Top 10 e a situação de cada fonte aparecem na própria página. Em **Artifacts**, baixe o
`relatorio-vagas` para abrir o `vagas.html` completo no navegador. Para ligar o Telegram depois, rode
`.\windows\configurar_telegram.ps1` numa janela do PowerShell.

---

## 1. Criar o bot no Telegram (5 minutos)

1. No Telegram, procure **@BotFather** e envie `/newbot`.
2. Escolha um nome (ex.: *Minhas Vagas IA*) e um usuário terminado em `bot` (ex.: `minhas_vagas_ia_bot`).
3. O BotFather responde com um **token** parecido com `123456789:AAH...`. **Guarde e não compartilhe esse token.**
4. Abra a conversa com o seu bot novo e mande qualquer mensagem (ex.: "oi").
5. Para descobrir o seu **chat_id**, abra no navegador (trocando `SEU_TOKEN`):
   `https://api.telegram.org/botSEU_TOKEN/getUpdates`
   Procure `"chat":{"id":` e anote o número que vem logo depois (ex.: `987654321`).

## 2. Rodar no seu computador (Windows)

Instale o [Python 3.11 ou mais novo](https://www.python.org/downloads/) e marque a opção **"Add Python to PATH"**.
Depois, abra o PowerShell **na pasta do projeto** e rode:

```powershell
pip install -r requirements.txt
```

Salve o token e o chat_id como variáveis de ambiente do seu usuário (só precisa fazer uma vez):

```powershell
[Environment]::SetEnvironmentVariable("TELEGRAM_TOKEN", "COLE_SEU_TOKEN", "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", "COLE_SEU_CHAT_ID", "User")
```

**Feche e abra o PowerShell de novo** para as variáveis valerem. Comandos úteis:

| Comando | O que faz |
|---|---|
| `python main.py --teste` | Busca tudo e mostra o Top 10 no terminal, **sem enviar nada** |
| `python main.py` | Busca e manda só os alertas (nota ≥ 80) |
| `python main.py --resumo` | Busca, manda os alertas e o Top 10 do dia |
| `python main.py --teste --fonte Meridial` | Testa uma única fonte |
| `python -m pytest -q` | Roda os testes automáticos |

Sem o token configurado, o bot funciona do mesmo jeito, mas só mostra as mensagens no terminal.

## 3. Agendar de graça no GitHub Actions (recomendado: funciona com o PC desligado)

1. Crie uma conta em [github.com](https://github.com) e um repositório novo, **privado** (ex.: `bot-vagas-ia`).
   Ele precisa ser privado porque o `vagas.db` e o `vagas.html` são salvos no repositório.
2. Envie os arquivos deste projeto para o repositório. O jeito mais fácil é a tela **"uploading an existing file"**.
   A pasta `.github/workflows` precisa ir junto.
3. No repositório, vá em **Settings → Secrets and variables → Actions → New repository secret** e crie:
   - `TELEGRAM_TOKEN`, com o seu token;
   - `TELEGRAM_CHAT_ID`, com o seu chat_id.
4. Vá em **Actions**, clique em **"Bot de vagas de IA" → Run workflow** e marque "Enviar o resumo" para testar.
5. Pronto. A partir daí ele roda sozinho: o resumo sai às 17h e os alertas são verificados a cada 3 horas.

> O GitHub às vezes atrasa os agendamentos em 5 a 30 minutos. Isso é normal.
> Cada execução leva uns 2 minutos, o que fica bem dentro da cota gratuita.

## 4. Alternativa: Agendador de Tarefas do Windows

Use esta opção se preferir não usar o GitHub. O PC precisa estar ligado nos horários agendados.
Abra o PowerShell **na pasta do projeto** e rode os dois comandos:

```powershell
schtasks /Create /TN "BotVagasIA-Resumo" /SC DAILY /ST 17:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"$PWD\windows\rodar_bot.ps1\" -Resumo"
```

```powershell
schtasks /Create /TN "BotVagasIA-Alertas" /SC HOURLY /MO 3 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"$PWD\windows\rodar_bot.ps1\""
```

Os logs ficam na pasta `logs/`. Para remover as tarefas, use `schtasks /Delete /TN "BotVagasIA-Resumo" /F`
(e faça o mesmo para `BotVagasIA-Alertas`).

---

## Como manter o bot

**Ajustar o que importa para você:** tudo fica no `config.yaml`.
- `pesos`: quantos pontos vale cada coisa (PT-BR, valor por hora, flexibilidade...).
- `nota_alerta`: a nota a partir da qual chega o alerta imediato (hoje é 80).
- `nota_minima_resumo`: vagas abaixo dessa nota não aparecem no resumo.
- `palavras`: as palavras que o bot procura. Para incluir uma área, acrescente na lista `dominio`.
- `filtros`: o que faz uma vaga ser descartada.

Depois de mudar qualquer coisa, rode `python main.py --teste` para ver o efeito.

**Quando uma fonte quebrar:** o bot continua com as outras e registra no log, por exemplo:
`❌ Mercor falhou: 404 ...`. Normalmente é porque a empresa trocou de sistema de vagas. Nesse caso, siga o
passo a passo abaixo de novo ou desligue a fonte com `ativo: false`.

**Por que algumas empresas trazem poucas vagas:** as APIs de Scale AI, Mercor, Handshake e outras listam também
as vagas internas da empresa (CLT nos EUA, por exemplo), e o bot descarta essas. As vagas de freelancer costumam
aparecer em Meridial, RWS TrainAI, Alignerr, DataAnnotation e Toloka.

## Como acrescentar uma empresa nova

1. Abra a página de vagas da empresa e veja o endereço quando clicar em uma vaga:
   - `boards.greenhouse.io/NOME` ou `job-boards.greenhouse.io/NOME` → **Greenhouse**, token = `NOME`
   - `jobs.lever.co/NOME` → **Lever**, token = `NOME`
   - `jobs.ashbyhq.com/NOME` → **Ashby**, token = `NOME`
2. Inclua uma linha em `fontes:` no `config.yaml`:
   ```yaml
   - {nome: "Empresa X", tipo: greenhouse, token: NOME, ativo: true}
   ```
3. Se a empresa não usar nenhum desses três, mas tiver uma página pública com a lista de vagas, use `html`.
   O `padrao_link` é um trecho que aparece no endereço de toda vaga:
   ```yaml
   - {nome: "Empresa X", tipo: html, url: "https://empresax.com/vagas", padrao_link: "/vagas/", ativo: true}
   ```
   Se ela tiver feed RSS, use `tipo: rss` com a `url` do feed.
4. Teste com `python main.py --teste --fonte "Empresa X"`.

## Regras de boa convivência (scraping ético)

- O bot lê o `robots.txt` de cada site e não acessa o que ele proíbe. É por isso que o Outlier está desligado.
- Ele se identifica com um User-Agent próprio e espera 2 segundos entre requisições ao mesmo site.
- O bot não acessa sites que proíbem robôs nos termos de uso, como LinkedIn e Indeed.

## Estrutura

```
config.yaml        empresas, pesos, palavras-chave e filtros
main.py            junta tudo (coleta → filtro → nota → banco → Telegram → relatório)
fontes/            greenhouse.py, lever.py, ashby.py, html_generico.py (HTML + RSS), base.py
filtros.py         regras de descarte
pontuacao.py       nota de 0 a 100 e leitor de valor por hora
banco.py           SQLite (vagas.db)
notificador.py     Telegram
relatorio.py       vagas.html
tests/             testes do leitor de salário, dos filtros e da nota
windows/           script para o Agendador de Tarefas
```
