"""Banco SQLite: guarda as vagas, evita duplicatas e lembra o que já foi enviado."""
import sqlite3
from datetime import datetime, timezone

from fontes.base import Vaga

ESQUEMA = """
CREATE TABLE IF NOT EXISTS vagas (
    hash          TEXT PRIMARY KEY,
    empresa       TEXT, titulo TEXT, link TEXT, fonte TEXT, local TEXT,
    idioma        TEXT, valor_hora REAL, valor_txt TEXT,
    publicada     TEXT, nota INTEGER, motivos TEXT,
    primeira_vez  TEXT, ultima_vez TEXT,
    ativa         INTEGER DEFAULT 1,
    enviada       INTEGER DEFAULT 0,
    alertada      INTEGER DEFAULT 0
);
"""


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Banco:
    def __init__(self, caminho: str = "vagas.db"):
        self.con = sqlite3.connect(caminho)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)

    def salvar(self, v: Vaga, quando: str) -> bool:
        """Insere ou atualiza. Devolve True se a vaga é nova."""
        nova = self.con.execute("SELECT 1 FROM vagas WHERE hash=?", (v.hash,)).fetchone() is None
        self.con.execute("""
            INSERT INTO vagas (hash, empresa, titulo, link, fonte, local, idioma, valor_hora, valor_txt,
                               publicada, nota, motivos, primeira_vez, ultima_vez, ativa)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
            ON CONFLICT(hash) DO UPDATE SET
                local=excluded.local, idioma=excluded.idioma, valor_hora=excluded.valor_hora,
                valor_txt=excluded.valor_txt, publicada=excluded.publicada, nota=excluded.nota,
                motivos=excluded.motivos, ultima_vez=excluded.ultima_vez, ativa=1
        """, (v.hash, v.empresa, v.titulo, v.link, v.fonte, v.local, v.idioma, v.valor_hora, v.valor_txt,
              v.publicada.isoformat() if v.publicada else None, v.nota, ", ".join(v.motivos), quando, quando))
        return nova

    def desativar_sumidas(self, fonte: str, inicio_execucao: str) -> int:
        """Vagas de uma fonte que respondeu bem, mas não apareceram nesta execução, saíram do ar."""
        cur = self.con.execute("UPDATE vagas SET ativa=0 WHERE fonte=? AND ultima_vez < ? AND ativa=1",
                               (fonte, inicio_execucao))
        return cur.rowcount

    def para_alerta(self, nota_min: int) -> list[sqlite3.Row]:
        return self.con.execute("""SELECT * FROM vagas WHERE ativa=1 AND alertada=0 AND enviada=0 AND nota>=?
                                   ORDER BY nota DESC""", (nota_min,)).fetchall()

    def para_resumo(self, limite: int, nota_min: int) -> list[sqlite3.Row]:
        return self.con.execute("""SELECT * FROM vagas WHERE ativa=1 AND enviada=0 AND nota>=?
                                   ORDER BY nota DESC, publicada DESC LIMIT ?""", (nota_min, limite)).fetchall()

    def ativas(self) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM vagas WHERE ativa=1 ORDER BY nota DESC, publicada DESC").fetchall()

    def marcar(self, hashes: list[str], coluna: str) -> None:
        assert coluna in {"enviada", "alertada"}
        self.con.executemany(f"UPDATE vagas SET {coluna}=1 WHERE hash=?", [(h,) for h in hashes])
        self.con.commit()

    def commit(self) -> None:
        self.con.commit()
