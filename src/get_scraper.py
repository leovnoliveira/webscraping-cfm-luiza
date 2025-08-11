from playwright.sync_api import sync_playwright
import pandas as pd
from time import sleep
import logging
import pickle
import os
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
    # Nome
    nome = card.locator("h4").inner_text().strip()
    campos = {"Nome": nome}
    # Todos os <b> (campos em negrito)
    bolds = card.locator("b")
    for i in range(bolds.count()):
        campo = bolds.nth(i).inner_text().strip(": ")
        # Valor é o texto imediatamente depois do <b>
        valor = bolds.nth(i).evaluate('el => el.nextSibling && el.nextSibling.textContent ? el.nextSibling.textContent.trim() : ""')
        campos[campo] = valor
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
    
    scrap_cfm_uf("CE") # Troque a UF aqui
