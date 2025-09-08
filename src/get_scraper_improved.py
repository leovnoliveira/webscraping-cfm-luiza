from playwright.sync_api import sync_playwright
import requests
import pandas as pd
from time import sleep
from datetime import datetime
from pathlib import Path
import logging
import pickle

# Diretório para salvar o arquivo de saída
DATA_DIR = (Path(__file__).resolve().parent / ".." / "data").resolve()
CSV_PATH = DATA_DIR / "dados_csv"
LOG_PATH = DATA_DIR / "logs"
CHECKPOINT_PATH = DATA_DIR / "checkpoints"

for d in (DATA_DIR, CSV_PATH, LOG_PATH, CHECKPOINT_PATH):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH / "scraping_api.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def salvar_checkpoint(medicos, pagina, uf):
    """Salva checkpoint do progresso"""
    checkpoint_data = {
        'medicos': medicos,
        'pagina': pagina,
        'uf': uf,
        'timestamp': datetime.now().isoformat()
    }
    checkpoint_file = CHECKPOINT_PATH / f"checkpoint_{uf}_{pagina}.pkl"
    with open(checkpoint_file, 'wb') as f:
        pickle.dump(checkpoint_data, f)
    print(f"Checkpoint salvo: {len(medicos)} médicos, página {pagina}")

def carregar_checkpoint(uf):
    """Carrega o último checkpoint"""
    checkpoint_files = list(CHECKPOINT_PATH.glob(f"checkpoint_{uf}_*.pkl"))
    if not checkpoint_files:
        return [], 1
    
    # Pega o checkpoint mais recente
    latest_checkpoint = max(checkpoint_files, key=lambda x: x.stat().st_mtime)
    
    try:
        with open(latest_checkpoint, 'rb') as f:
            checkpoint_data = pickle.load(f)
            print(f"Checkpoint carregado: {len(checkpoint_data['medicos'])} médicos, página {checkpoint_data['pagina']}")
            return checkpoint_data['medicos'], checkpoint_data['pagina']
    except Exception as e:
        print(f"Erro ao carregar checkpoint: {e}")
        return [], 1

def salvar_csv_periodicamente(medicos, uf, pagina):
    """Salva CSV a cada 100 páginas"""
    if len(medicos) > 0 and pagina % 100 == 0:
        df = pd.DataFrame(medicos)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_csv = CSV_PATH / f"medicos_{uf}_pagina_{pagina}_{ts}_checkpoint.csv"
        df.to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
        print(f"CSV salvo: {len(medicos)} médicos até página {pagina}")

def scrap_cfm_pure_playwright_improved(uf, delay=2.0, max_paginas=None, usar_checkpoint=True):
    """Scraping melhorado com checkpoint e salvamento periódico"""
    logger.info(f"Iniciando scraping melhorado via Playwright para UF {uf}")
    
    # Carrega checkpoint se solicitado
    todos_medicos = []
    pagina_inicial = 1
    if usar_checkpoint:
        todos_medicos, pagina_inicial = carregar_checkpoint(uf)
        print(f"Continuando de: {len(todos_medicos)} médicos, página {pagina_inicial}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Abrindo página de busca para UF {uf}...")
        page.goto("https://portal.cfm.org.br/busca-medicos")
        
        # Faz a busca inicial
        page.locator('select[name="uf"]').select_option(uf)
        sleep(1)
        page.locator('button.btn-buscar').click()
        print("Aguardando resultados carregarem...")
        page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=120_000)
        print("Resultados carregados!")
        
        # Se tem checkpoint, navega até a página correta
        if pagina_inicial > 1:
            print(f"Navegando para página {pagina_inicial}...")
            for i in range(2, pagina_inicial + 1):
                try:
                    next_button = page.locator(f'xpath=//*[@id="paginacao"]//a[text()="{i}"]')
                    if next_button.count() > 0:
                        next_button.click()
                        sleep(delay)
                    else:
                        # Usa estratégia alternativa
                        next_button_alt = page.locator('xpath=//*[@id="paginacao"]//a[contains(text(), "Próxima") or contains(text(), ">")]')
                        if next_button_alt.count() > 0:
                            next_button_alt.click()
                            sleep(delay)
                except Exception as e:
                    print(f"Erro ao navegar para página {i}: {e}")
                    break
        
        pagina = pagina_inicial
        
        while True:
            print(f"Processando página {pagina}...")
            
            # Verifica se há reCAPTCHA
            try:
                recaptcha = page.locator('iframe[src*="recaptcha"]')
                if recaptcha.count() > 0:
                    print("⚠️  reCAPTCHA detectado! Resolva manualmente e pressione ENTER para continuar...")
                    input("Pressione ENTER após resolver o reCAPTCHA...")
            except:
                pass
            
            # Extrai dados da página atual
            try:
                # Aguarda os resultados carregarem
                page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=30000)
                
                # Extrai dados dos cards de médicos
                medicos_pagina = page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll('div.busca-resultado > div[class^="resultado-item"]');
                        const medicos = [];
                        
                        cards.forEach(card => {
                            const medico = {};
                            const texto = card.textContent;
                            
                            // Extrai nome (primeira linha antes do CRM)
                            const nomeMatch = texto.match(/^([^\\n]+?)\\s+CRM:/);
                            if (nomeMatch) {
                                medico.nome = nomeMatch[1].trim();
                            }
                            
                            // Extrai CRM
                            const crmMatch = texto.match(/CRM:\\s*([^\\s]+)/);
                            if (crmMatch) {
                                medico.crm = crmMatch[1].trim();
                            }
                            
                            // Extrai data de inscrição (apenas a data, não o texto extra)
                            const dataMatch = texto.match(/Data de Inscrição:\\s*([0-9]{2}\\/[0-9]{2}\\/[0-9]{4})/);
                            if (dataMatch) {
                                medico.data_inscricao = dataMatch[1].trim();
                            }
                            
                            // Extrai situação (apenas a palavra, não o texto extra)
                            const situacaoMatch = texto.match(/Situação:\\s*([^\\s]+)/);
                            if (situacaoMatch) {
                                medico.situacao = situacaoMatch[1].trim();
                            }
                            
                            // Extrai especialidade (apenas a especialidade, não o texto extra)
                            const espMatch = texto.match(/Especialidades\\/Áreas de Atuação:\\s*([^\\n]+?)(?=\\s+Endereço|$)/);
                            if (espMatch) {
                                medico.especialidade = espMatch[1].trim();
                            }
                            
                            // Extrai instituição de graduação
                            const instMatch = texto.match(/Instituição de Graduação:\\s*([^\\n]+)/);
                            if (instMatch) {
                                medico.instituicao_graduacao = instMatch[1].trim();
                            }
                            
                            // Extrai ano de formatura
                            const anoMatch = texto.match(/Ano de Formatura:\\s*([0-9]{4})/);
                            if (anoMatch) {
                                medico.ano_formatura = anoMatch[1].trim();
                            }
                            
                            medicos.push(medico);
                        });
                        
                        return medicos;
                    }
                """)
                
                if not medicos_pagina or len(medicos_pagina) == 0:
                    print(f"Nenhum médico encontrado na página {pagina}. Encerrando.")
                    break
                
                print(f"Página {pagina}: {len(medicos_pagina)} médicos encontrados.")
                todos_medicos.extend(medicos_pagina)
                
                # Salva checkpoint a cada 10 páginas
                if pagina % 10 == 0:
                    salvar_checkpoint(todos_medicos, pagina, uf)
                
                # Salva CSV a cada 100 páginas
                salvar_csv_periodicamente(todos_medicos, uf, pagina)
                
                if max_paginas and pagina >= max_paginas:
                    print(f"Máximo de páginas {max_paginas} atingido.")
                    break
                
                # Tenta ir para próxima página usando múltiplas estratégias
                try:
                    # Estratégia 1: Procura por um link que contenha o número da próxima página
                    next_page_number = pagina + 1
                    next_button = page.locator(f'xpath=//*[@id="paginacao"]//a[text()="{next_page_number}"]')
                    
                    if next_button.count() > 0:
                        print(f"Estratégia 1: Indo para página {next_page_number}...")
                        next_button.click()
                        sleep(delay)
                        pagina += 1
                        continue
                    
                    # Estratégia 2: Procura por botão "Próxima" ou ">"
                    next_button_alt = page.locator('xpath=//*[@id="paginacao"]//a[contains(text(), "Próxima") or contains(text(), ">")]')
                    if next_button_alt.count() > 0:
                        print(f"Estratégia 2: Usando botão 'Próxima' para ir para página {next_page_number}...")
                        next_button_alt.click()
                        sleep(delay)
                        pagina += 1
                        continue
                    
                    # Estratégia 3: Procura por qualquer link que seja maior que a página atual
                    next_button_alt2 = page.locator(f'xpath=//*[@id="paginacao"]//a[text()="{next_page_number + 1}" or text()="{next_page_number + 2}" or text()="{next_page_number + 3}"]')
                    if next_button_alt2.count() > 0:
                        print("Estratégia 3: Indo para próxima página disponível...")
                        next_button_alt2.first.click()
                        sleep(delay)
                        pagina += 1
                        continue
                    
                    # Se nenhuma estratégia funcionou
                    print("Nenhuma estratégia de navegação funcionou. Encerrando.")
                    break
                    
                except Exception as e:
                    print(f"Erro ao navegar para próxima página: {e}")
                    break
                    
            except Exception as e:
                print(f"Erro ao processar página {pagina}: {e}")
                break
        
        browser.close()
        
        # Salva os dados finais
        if todos_medicos:
            df = pd.DataFrame(todos_medicos)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_csv = CSV_PATH / f"medicos_{uf}_{ts}_final.csv"
            df.to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
            logger.info(f"Dados finais salvos em {arquivo_csv}")
            print(f"Total de médicos encontrados: {len(todos_medicos)}")
            
            # Remove checkpoints antigos
            for checkpoint_file in CHECKPOINT_PATH.glob(f"checkpoint_{uf}_*.pkl"):
                checkpoint_file.unlink()
            print("Checkpoints antigos removidos.")
        else:
            logger.info("Nenhum médico encontrado.")
            print("Nenhum médico encontrado.")

if __name__ == "__main__":
    # Exemplo de uso com melhorias
    scrap_cfm_pure_playwright_improved("RR", delay=2.0, max_paginas=None, usar_checkpoint=True)
