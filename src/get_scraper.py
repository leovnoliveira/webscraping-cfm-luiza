from playwright.sync_api import sync_playwright
import pandas as pd
from time import sleep
import logging
import pickle
import os
import re
from datetime import datetime
from pathlib import Path


# Diretório para salvar o arquivo de saída
DATA_DIR = (Path(__file__).resolve().parent / ".." / "data").resolve()
CSV_PATH = DATA_DIR / "dados_csv"
PICKLE_PATH = DATA_DIR / "dados_pickle"
LOG_PATH = DATA_DIR / "logs"

for d in (DATA_DIR, CSV_PATH, PICKLE_PATH, LOG_PATH):
            d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH / "scraping.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def salvar_checkpoint(dados, pagina, uf, arquivo_pickle=None):
    if arquivo_pickle is None:
        arquivo_pickle = PICKLE_PATH / f"checkpoint_{uf}.pkl"
    with open(arquivo_pickle, "wb") as f:
        pickle.dump({"dados": dados, "pagina": pagina}, f)

def carregar_checkpoint(uf, arquivo_pickle=None):
    if arquivo_pickle is None:
        arquivo_pickle = PICKLE_PATH / f"checkpoint_{uf}.pkl"
    if not os.path.exists(arquivo_pickle):
        return [], 1  # Retorna lista vazia e página 1
    with open(arquivo_pickle, "rb") as f:
        checkpoint = pickle.load(f)
        return checkpoint["dados"], checkpoint["pagina"]


def salvar_csv_periodicamente(dados, uf, sufixo=""):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_csv = CSV_PATH / f"medicos_{uf}{sufixo}_{ts}.csv"
    if not os.path.exists(arquivo_csv):
        pd.DataFrame(dados).to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
        logger.info(f"Arquivo {arquivo_csv} criado com {len(dados)} registros.")
    else:
        df_existente = pd.read_csv(arquivo_csv, encoding="utf-8-sig")
        df_novo = pd.DataFrame(dados)
        df_completo = pd.concat([df_existente, df_novo], ignore_index=True)
        df_completo.to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
    

def extrair_campos_card(card):
     # normaliza texto (remove NBSP, trims e colapsa espaços/linhas)
    def norm(s):
        if not s:
            return None
        s = s.replace("\xa0", " ").strip()
        s = re.sub(r"\s+", " ", s)  # múltiplos espaços viram um só
        return s if s else None

    # Nome (título do card)
    nome = card.locator("h4").inner_text().strip()
    campos = {"Nome": nome}

    bolds = card.locator("b")
    n_bolds = bolds.count()
    for i in range(n_bolds):
        b = bolds.nth(i)
        label_raw = b.inner_text().strip()
        label_key = label_raw.rstrip(":")  # chave sem os dois-pontos

        val = None

        # (1) irmão direto <span> ou <a>
        sib_span = b.locator("xpath=following-sibling::*[self::span or self::a][1]")
        if sib_span.count():
            txt = norm(sib_span.inner_text())
            if txt:
                val = txt

        # 2) quando há texto “solto” logo após o <b>LABEL:</b>
        if not val:
            sib_text = b.locator('xpath=following-sibling::text()[1]')
            if sib_text.count():
                txt = norm(sib_text.evaluate("n => n.textContent"))
                if txt:
                    val = txt
        # (3) MESMA LINHA, PRÓXIMA COLUNA
        # label está numa col do grid; o valor costuma estar na col seguinte
        if not val:
            next_col = b.locator(
                'xpath=ancestor::div[contains(@class,"col-")][1]'
                '/following-sibling::div[contains(@class,"col-")][1]'
            )
            if next_col.count():
                raw = next_col.inner_text()
                parts = [norm(x) for x in raw.splitlines()]
                parts = [x for x in parts if x]
                if parts:
                    val = " | ".join(parts) if parts else None

        # (4) ESPECIALIDADES – valor vem no PRÓXIMO .row (não como irmão direto do .row atual)
        if (not val) and label_key.startswith("Especialidades/Áreas de Atuação"):
            prox_div = b.locator(
                'xpath=ancestor::div[contains(@class,"row")][1]'
                '/following-sibling::div[contains(@class,"row")][1]'
                '//div[contains(@class,"col-md-12")][1]'
            )
            if prox_div.count():
                raw = prox_div.inner_text()
                # junta múltiplas linhas (várias especialidades) em uma string única
                parts = [norm(x) for x in raw.splitlines()]
                parts = [x for x in parts if x]
                val = " | ".join(parts) if parts else None

        campos[label_key] = val if val else None
    
    # alias amigável (deixa uma coluna direta "especialidade")
    for k in list(campos.keys()):
        if "Especialidades/Áreas de Atuação" in k:
            campos["especialidade"] = campos[k]
            break

    return campos

def scrap_cfm_uf(uf, max_paginas=None, checkpoint_cada=10, csv_cada=100):

    # Tenta carregar onde parou da última vez
    checkpoint_arquivo = PICKLE_PATH / f"checkpoint_{uf}.pkl"
    dados, pagina = carregar_checkpoint(uf, checkpoint_arquivo)
    logger.info(f"Iniciando da página {pagina} para a UF {uf} ({len(dados)} médicos recuperados do checkpoint)")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://portal.cfm.org.br/busca-medicos")
        # Seleciona UF
        page.locator('select[name="uf"]').select_option(uf)
        sleep(1)
        # Clica no botão BUSCAR (CSS corrigido)
        page.locator('button.btn-buscar').click()
        # Aguarda resultados carregarem
        page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=120_000)

        if pagina > 1:
            for p_idx in range(2, pagina + 1):
                btn = page.locator(f"li.paginationjs-page[data-num='{p_idx}'] a")
                if btn.count() > 0:
                    btn.first.click()
                    sleep(1)
                    page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=60_000)
                    sleep(1.5)
            
        dados = []
        pagina = 1
        while True:
            try:
                logger.info(f"Processando página {pagina}")
                cards = page.locator('div.busca-resultado > div[class^="resultado-item"]')
                n_cards = cards.count()
                logger.info(f"Encontrados {n_cards} médicos!")
                for i in range(n_cards):
                    card = cards.nth(i)
                    campos = extrair_campos_card(card)
                    dados.append(campos)


                # Checkpoints
                if pagina % checkpoint_cada == 0:
                    salvar_checkpoint(dados, pagina, uf, checkpoint_arquivo)
                    logger.info(f"Checkpoint salvo para a página {pagina} da UF {uf} com {len(dados)} médicos.")

                if pagina % csv_cada == 0:
                    salvar_csv_periodicamente(dados, uf, sufixo=f"_backup_{pagina}")
                    logger.info(f"CSV salvo para a página {pagina} da UF {uf} com {len(dados)} médicos.")
                
                # Paginação (se houver)
                pagina += 1
                if max_paginas and pagina > max_paginas:
                    logger.info(f"Máximo de páginas {max_paginas} atingido, encerrando.")
                    break
                next_btn = page.locator(f"li.paginationjs-page[data-num='{pagina}'] a")
                if next_btn.count() > 0:
                    logger.info(f"Indo para a página {pagina}")
                    next_btn.first.click()
                    sleep(1)
                    page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=60000)
                    sleep(1.5)
                else:
                    print("Chegou na última página")
                    break
            except Exception as e:
                logger.error(f"Erro ao processar a página {pagina}: {e}")
                salvar_checkpoint(dados, pagina, uf, checkpoint_arquivo)
                logger.info("Salvando antes de interromper.")
                break

        browser.close()
        salvar_checkpoint(dados, pagina, uf, checkpoint_arquivo)
        df = pd.DataFrame(dados)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        df.to_csv(CSV_PATH / f"medicos_{uf}_{ts}_final.csv", index=False, encoding="utf-8-sig")
        print(f"Salvo {len(df)} médicos em data/csv/medicos_{uf}_{ts}_final.csv")
        return df

if __name__ == "__main__":
    sigla_uf_que_ainda_faltam = [
        'BA', 'CE', 'DF', 'ES', 'GO', 'MG',
    'PA', 'PB', 'PE', 'PR', 'RJ', 'RS', 'SC', 'SP'
    ]
    
    scrap_cfm_uf("PR") # Troque a UF aqui