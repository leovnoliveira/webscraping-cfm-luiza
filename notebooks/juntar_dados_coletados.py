# merge_cfm_csvs.py
# from _future_ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class CsvMergeConfig:
    csv_dir: Path
    output_path: Path
    recursive: bool = True
    encoding_priority: List[str] = field(default_factory=lambda: ["utf-8-sig", "utf-8", "latin1", "ISO-8859-1"])
    priority_cols: List[str] = field(default_factory=lambda: [
        "nome", "crm", "uf", "situacao", "especialidade", "especialidade_secundaria",
        "area_atuacao", "cidade", "bairro", "endereco", "cep", "telefone", "email",
        "inscricao", "cpf"
    ])
    # padrões (regex) -> nome canônico
    canonical_map: Dict[str, str] = field(default_factory=lambda: {
        r"^nome( completo)?$": "nome",
        r"^crm(\/uf)?$": "crm",
        r"^uf$": "uf",
        r"^situacao$": "situacao",
        r"^especialidade(s)?( principal)?$": "especialidade",
        r"^especialidade(s)? secundaria(s)?$": "especialidade_secundaria",
        r"^area de atuacao$": "area_atuacao",
        r"^endereco$": "endereco",
        r"^bairro$": "bairro",
        r"^cidade$": "cidade",
        r"^cep$": "cep",
        r"^telefone(s)?$": "telefone",
        r"^email$": "email",
        r"^inscricao$": "inscricao",
        r"^cpf$": "cpf",
    })
    # heurística: se passar deste nº de colunas, tentar separador ';'
    too_many_cols_threshold: int = 60


class CsvMerger:
    def __init__(self, config: CsvMergeConfig):
        self.cfg = config
        self.log = logging.getLogger(self.__class__.__name__)

    # ---------- utils de normalização ----------
    @staticmethod
    def _strip_accents(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

    def normalizar_header(self, col: str) -> str:
        col = str(col)
        col = self._strip_accents(col).strip().lower()
        col = re.sub(r"\s+", " ", col)
        col = col.replace(" :", "").replace(":", "")
        return col

    def canoniza_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        new_cols = []
        for c in df.columns:
            nc = self.normalizar_header(c)
            mapped = None
            for pat, tgt in self.cfg.canonical_map.items():
                if re.fullmatch(pat, nc):
                    mapped = tgt
                    break
            new_cols.append(mapped or nc)
        df.columns = new_cols
        return df

    def limpa_linha(self, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            v = re.sub(r"\s+", " ", v)
            return v
        return v

    # ---------- leitura robusta ----------
    def le_csv_robusto(self, path: Path) -> pd.DataFrame:
        last_err = None
        df: Optional[pd.DataFrame] = None

        # tenta encodings com sep=","
        for enc in self.cfg.encoding_priority:
            try:
                df = pd.read_csv(path, sep=",", dtype=str, low_memory=False,
                                 on_bad_lines="skip", encoding=enc)
                break
            except Exception as e:
                last_err = e

        if df is None:
            raise RuntimeError(f"Falha lendo {path} com encodings {self.cfg.encoding_priority}: {last_err}")

        # heurística: se muitas colunas, experimente ';'
        if df.shape[1] > self.cfg.too_many_cols_threshold:
            for enc in self.cfg.encoding_priority:
                try:
                    df2 = pd.read_csv(path, sep=";", dtype=str, low_memory=False,
                                      on_bad_lines="skip", encoding=enc)
                    # escolha a variante com menos colunas (provável parse correto)
                    if df2.shape[1] < df.shape[1]:
                        df = df2
                    break
                except Exception:
                    continue

        return df

    # ---------- descoberta de arquivos ----------
    def descobre_csvs(self) -> List[Path]:
        if self.cfg.recursive:
            files = sorted([p for p in self.cfg.csv_dir.rglob("*.csv") if p.is_file()])
        else:
            files = sorted([p for p in self.cfg.csv_dir.glob("*.csv") if p.is_file()])

        self.log.info("CSV(s) encontrados: %d", len(files))
        for p in files[:10]:
            self.log.debug(" - %s", p)
        return files

    # ---------- pipeline principal ----------
    def merge(self) -> Path:
        files = self.descobre_csvs()
        if not files:
            raise SystemExit(f"Nenhum CSV encontrado em: {self.cfg.csv_dir}")

        dfs: List[pd.DataFrame] = []
        for f in files:
            try:
                df = self.le_csv_robusto(f)
                df = self.canoniza_headers(df)
                df = df.dropna(axis=1, how="all")
                dfs.append(df)
            except Exception as e:
                self.log.warning("Falha lendo %s: %s", f, e)

        if not dfs:
            raise SystemExit("Nenhum CSV legível após tentativas.")

        full = pd.concat(dfs, ignore_index=True, sort=False)

        # normaliza tipos/strings
        for c in full.columns:
            full[c] = full[c].astype(str).replace({"nan": np.nan, "None": np.nan})

        # reordena: prioritárias primeiro
        ordered = [c for c in self.cfg.priority_cols if c in full.columns] + \
                  [c for c in full.columns if c not in self.cfg.priority_cols]
        full = full[ordered]

        # dedup: (crm, uf) -> (nome, uf) -> geral
        if {"crm", "uf"}.issubset(full.columns):
            full = full.drop_duplicates(subset=["crm", "uf"], keep="first")
        elif {"nome", "uf"}.issubset(full.columns):
            full = full.drop_duplicates(subset=["nome", "uf"], keep="first")
        else:
            full = full.drop_duplicates(keep="first")

        # limpeza de espaços múltiplos
        full = full.applymap(self.limpa_linha)

        # salva
        self.cfg.output_path.parent.mkdir(parents=True, exist_ok=True)
        full.to_csv(self.cfg.output_path, index=False, encoding="utf-8-sig")

        self.log.info("Merge concluído: %s | linhas=%d | colunas=%d",
                      self.cfg.output_path, full.shape[0], full.shape[1])
        return self.cfg.output_path


def build_default_config(base_dir: Optional[Path] = None) -> CsvMergeConfig:
    """
    Considera a estrutura:
    <SCRIPT_AQUI>/
      data/
        dados_csv/   <-- CSVs
    """
    base = base_dir or (Path(__file__).resolve().parent / "..").resolve()
    data_dir = base / "data"
    csv_dir = data_dir / "dados_csv"
    out = base / "dados_medicos_por_uf.csv"
    return CsvMergeConfig(csv_dir=csv_dir, output_path=out)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    cfg = build_default_config()
    merger = CsvMerger(cfg)
    output = merger.merge()
    print(f"Arquivo final salvo em: {output.resolve()}")