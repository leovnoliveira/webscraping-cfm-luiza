# scraper_refactored.py

import re
import logging
import random
from pathlib import Path
from time import sleep
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

# --- Configurações Globais e Logging ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(), # Envia logs para o console
        logging.FileHandler("scraping_pw.log", mode="w", encoding="utf-8") # E para um arquivo
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://portal.cfm.org.br/busca-medicos"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "dados_csv"
LOG_PATH = DATA_DIR / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH.mkdir(parents=True, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20110101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Script injetado no navegador para remover sinais de automação.
ANTI_BOT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt'] });
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
"""

class CFMScraper:
    """
    Um scraper robusto e "humanizado" para o portal do CFM,
    encapsulado em uma classe para melhor organização e gerenciamento de estado.
    """
    def __init__(self, playwright: Playwright, headless: bool = False):
        self.playwright = playwright
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.consecutive_blocks = 0  # Contador de bloqueios consecutivos
        self.last_successful_page = 0  # Última página com sucesso

    def __enter__(self):
        """Inicializa o navegador ao entrar no bloco 'with'."""
        self.browser = self._setup_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que o navegador seja fechado ao sair do bloco 'with'."""
        if self.browser:
            logger.info("Encerrando o navegador...")
            self.browser.close()

    def _setup_browser(self) -> Browser:
        """Configura e lança uma instância do navegador com técnicas anti-detecção."""
        logger.info("Inicializando navegador Chromium...")
        browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1366, 'height': 768},
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
        )
        self.context.add_init_script(ANTI_BOT_SCRIPT)
        self.page = self.context.new_page()
        return browser

    # --- Métodos de "Humanização" ---

    def delay_aleatorio(self, min_seconds: float = 1.5, max_seconds: float = 3.5):
        """Pausa a execução por um tempo aleatório para simular o comportamento humano."""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Aguardando {delay:.2f} segundos...")
        sleep(delay)

    def simula_movimento_do_mouse(self):
        """Move o mouse para coordenadas aleatórias para simular atividade."""
        if self.page:
            for _ in range(random.randint(2, 5)):
                x, y = random.randint(100, 800), random.randint(100, 600)
                self.page.mouse.move(x, y)
                sleep(random.uniform(0.1, 0.3))

    def delay_inteligente(self, page_number: int, base_delay: float = 2.0):
        """
        Aplica um delay que aumenta conforme o número de páginas avança,
        uma técnica crucial para evitar bloqueios em longas sessões de scraping.
        """
        multiplicador = 1.0
        
        # Sistema de delays mais agressivo próximo ao ponto de bloqueio
        if page_number > 90:  # Próximo ao ponto onde para (97)
            multiplicador = 4.0
            logger.warning(f"Zona crítica (p{page_number}) - delay x4")
        elif page_number > 70:
            multiplicador = 3.0
        elif page_number > 50:
            multiplicador = 2.5
        elif 10 < page_number <= 50:
            multiplicador = 1.5

        # Multiplicador adicional se houver bloqueios consecutivos
        if self.consecutive_blocks > 0:
            block_multiplier = 1 + (self.consecutive_blocks * 0.5)
            multiplicador *= block_multiplier
            logger.warning(f"Bloqueios detectados - delay adicional x{block_multiplier:.1f}")

        # Pausa extra a cada 25 páginas para simular um descanso.
        if page_number % 25 == 0 and page_number > 0:
            logger.info(f"Pausa estratégica na página {page_number}. Aguardando mais tempo...")
            multiplicador *= 2.5
            
        # Pausa especial nas páginas críticas
        if page_number in [95, 96, 97, 98, 99, 100]:
            multiplicador *= 3.0
            logger.warning(f"Página crítica {page_number} - delay máximo")

        self.delay_aleatorio(base_delay * multiplicador, base_delay * multiplicador * 1.5)

    # --- Lógica Principal do Scraping ---

    def performa_busca(self, uf: str):
        """Navega até o site, preenche o formulário de busca e inicia a pesquisa."""
        if not self.page:
            raise ConnectionError("A página do navegador não foi inicializada.")

        logger.info(f"Navegando para {BASE_URL}...")
        self.page.goto(BASE_URL, wait_until='domcontentloaded', timeout=60000)
        self.delay_aleatorio()

        logger.info(f"Realizando busca para a UF: {uf}")
        self.simula_movimento_do_mouse()

        uf_selector = self.page.locator('select[name="uf"]')
        uf_selector.hover()
        self.delay_aleatorio(0.5, 1.0)
        uf_selector.select_option(uf)

        self.delay_aleatorio()
        search_button = self.page.locator('button.btn-buscar')
        search_button.hover()
        self.delay_aleatorio(0.5, 1.0)
        search_button.click()

        # Otimização: Em vez de um sleep fixo, esperamos pelo seletor de resultados.
        # Isso reduz os "engasgos" e torna o scraper mais eficiente.
        logger.info("Aguardando o carregamento dos resultados iniciais...")
        self.page.wait_for_selector(
            'div.busca-resultado > div[class^="resultado-item"]',
            timeout=120_000
        )
        logger.info("Resultados carregados.")

    def detectar_bloqueio_ou_fim(self) -> tuple[bool, str]:
        """
        Detecta se a página foi bloqueada ou se chegamos ao fim natural dos resultados.
        Retorna (is_blocked, reason)
        """
        if not self.page:
            return True, "Página não inicializada"
            
        try:
            # Verifica se existe a mensagem "Nenhum resultado a mostrar"
            no_results_selector = self.page.locator('text="Nenhum resultado a mostrar"')
            if no_results_selector.count() > 0:
                logger.info("Detectada mensagem oficial: 'Nenhum resultado a mostrar'")
                return False, "Fim natural dos resultados"
            
            # Verifica outros indicadores de bloqueio
            page_content = self.page.content().lower()
            block_indicators = [
                'blocked', 'captcha', 'verificação', 'bot detected',
                'rate limit', 'too many requests', 'acesso negado',
                'forbidden', 'erro 403', 'erro 429', 'suspeita'
            ]
            
            for indicator in block_indicators:
                if indicator in page_content:
                    logger.warning(f"Indicador de bloqueio detectado: '{indicator}'")
                    return True, f"Bloqueio detectado: {indicator}"
            
            # Verifica se a página foi redirecionada
            current_url = self.page.url
            if BASE_URL not in current_url:
                logger.warning(f"Redirecionamento detectado: {current_url}")
                return True, f"Redirecionado para: {current_url}"
                
            return False, "Página normal"
            
        except Exception as e:
            logger.error(f"Erro ao detectar bloqueio: {e}")
            return True, f"Erro na detecção: {e}"
    
    def scraping_pagina_atual(self) -> List[Dict[str, Optional[str]]]:
        """
        Extrai todos os dados dos médicos da página visível usando regex,
        inspirado no snippet JS para máxima robustez.
        """
        if not self.page:
            return []

        # Primeiro verifica se há bloqueio
        is_blocked, reason = self.detectar_bloqueio_ou_fim()
        if is_blocked:
            logger.error(f"Bloqueio detectado durante extração: {reason}")
            self.consecutive_blocks += 1
            return []

        logger.info("Extraindo dados dos médicos na página...")
        cards_locators = self.page.locator('div.busca-resultado > div[class^="resultado-item"]').all()
        
        if not cards_locators:
            # Verifica novamente se é fim natural ou problema
            is_blocked, reason = self.detectar_bloqueio_ou_fim()
            if not is_blocked and "Nenhum resultado a mostrar" in reason:
                logger.info("Chegamos ao fim natural dos resultados")
                return []  # Fim legítimo
            else:
                logger.warning("Nenhum card de médico encontrado na página.")
                self.consecutive_blocks += 1
                return []

        medicos_data = []
        for card in cards_locators:
            texto = card.text_content()
            
            # Verifica se o card contém "Nenhum resultado a mostrar"
            if "Nenhum resultado a mostrar" in texto:
                logger.info("Card contém mensagem de fim - ignorando")
                continue
                
            medico = {}

            # Função auxiliar para aplicar regex e extrair o primeiro grupo
            def extract(pattern, text):
                match = re.search(pattern, text, re.IGNORECASE)
                return match.group(1).strip() if match else None

            # Aplica as mesmas regex do seu snippet, traduzidas para Python
            medico['nome'] = extract(r"^([^\n]+?)\s+CRM:", texto)
            medico['crm'] = extract(r"CRM:\s*([^\s]+)", texto)
            medico['data_inscricao'] = extract(r"Data de Inscrição:\s*(\d{2}/\d{2}/\d{4})", texto)
            medico['situacao'] = extract(r"Situação:\s*([^\s]+)", texto)
            # Regex crucial para especialidades, que captura tudo até a próxima linha de "Endereço" ou fim
            medico['especialidade'] = extract(r"Especialidades/Áreas de Atuação:\s*([^\n]+?)(?=\s+Endereço|$)", texto)
            medico['instituicao_graduacao'] = extract(r"Instituição de Graduação:\s*([^\n]+)", texto)
            medico['ano_formatura'] = extract(r"Ano de Formatura:\s*(\d{4})", texto)
            
            # Só adiciona se pelo menos nome ou CRM foram extraídos
            if medico['nome'] or medico['crm']:
                medicos_data.append(medico)
            
        logger.info(f"Extraídos {len(medicos_data)} registros desta página.")
        
        # Reset consecutive blocks se extraiu dados com sucesso
        if medicos_data:
            self.consecutive_blocks = 0
            
        return medicos_data

    def tentar_recuperacao(self, pagina_atual: int) -> bool:
        """
        Tenta recuperar de um possível bloqueio com estratégias avançadas.
        """
        logger.warning(f"Tentando recuperação na página {pagina_atual}...")
        
        try:
            # Estratégia 1: Pausa longa
            recovery_time = random.uniform(30, 90)
            logger.info(f"Pausa de recuperação: {recovery_time:.1f}s")
            sleep(recovery_time)
            
            # Estratégia 2: Simula atividade humana
            self.simula_movimento_do_mouse()
            self.delay_aleatorio(2, 4)
            
            # Estratégia 3: Recarrega a página atual
            logger.info("Recarregando página...")
            self.page.reload(wait_until='domcontentloaded', timeout=60000)
            self.delay_aleatorio(3, 6)
            
            # Verifica se a recuperação funcionou
            is_blocked, reason = self.detectar_bloqueio_ou_fim()
            if not is_blocked:
                logger.info("Recuperação bem-sucedida!")
                self.consecutive_blocks = 0
                return True
            else:
                logger.error(f"Recuperação falhou: {reason}")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante recuperação: {e}")
            return False

    def navega_para_proxima_pagina(self, pagina_atual: int) -> bool:
        """Tenta clicar no botão da próxima página e retorna True se bem-sucedido."""
        if not self.page:
            return False
        
        # Verifica bloqueio antes de tentar navegar
        is_blocked, reason = self.detectar_bloqueio_ou_fim()
        if is_blocked:
            logger.warning(f"Bloqueio detectado antes de navegar: {reason}")
            # Tenta recuperação
            if self.tentar_recuperacao(pagina_atual):
                # Se recuperou, tenta navegar novamente
                return self.navega_para_proxima_pagina(pagina_atual)
            else:
                return False

        proxima_pagina = pagina_atual + 1
        logger.info(f"Tentando navegar para a página {proxima_pagina}...")

        next_button = self.page.locator(f'#paginacao a:text-is("{proxima_pagina}")')
        if next_button.count() > 0:
            self.simula_movimento_do_mouse()
            next_button.hover()
            self.delay_aleatorio(0.5, 1.2)
            next_button.click()
            
            # Espera inteligente pela atualização dos resultados
            try:
                self.page.wait_for_selector(
                    'div.busca-resultado > div[class^="resultado-item"]',
                    state='attached',
                    timeout=60000
                )
                
                # Verifica se a navegação realmente funcionou
                self.delay_aleatorio(1, 2)
                is_blocked_after, reason_after = self.detectar_bloqueio_ou_fim()
                
                if is_blocked_after:
                    logger.warning(f"Bloqueio detectado após navegação: {reason_after}")
                    return False
                    
                logger.info("Navegação para a próxima página bem-sucedida.")
                self.last_successful_page = proxima_pagina
                return True
                
            except Exception as e:
                logger.warning(f"Timeout ao esperar resultados: {e}")
                # Verifica se é bloqueio ou problema de rede
                is_blocked_timeout, reason_timeout = self.detectar_bloqueio_ou_fim()
                if is_blocked_timeout:
                    logger.error(f"Bloqueio confirmado após timeout: {reason_timeout}")
                return False
        else:
            # Verifica se não tem botão por fim natural ou bloqueio
            is_blocked_no_btn, reason_no_btn = self.detectar_bloqueio_ou_fim()
            if "Nenhum resultado a mostrar" in reason_no_btn:
                logger.info("Fim natural dos resultados confirmado.")
            else:
                logger.warning(f"Botão não encontrado - possível bloqueio: {reason_no_btn}")
            return False

    def run(self, uf: str, max_paginas: Optional[int] = None):
        """
        Orquestra o processo completo de scraping para uma determinada UF.
        """
        if not self.page:
            raise ConnectionError("O scraper não foi inicializado corretamente.")
            
        self.performa_busca(uf)

        all_medicos = []
        page_num = 1
        paginas_vazias_consecutivas = 0

        while True:
            if max_paginas and page_num > max_paginas:
                logger.info(f"Limite de {max_paginas} páginas atingido.")
                break

            logger.info(f"--- Processando Página {page_num} para {uf} ---")
            
            # Delay inteligente antes de processar
            self.delay_inteligente(page_num)
            
            # Simula atividade humana antes de extrair dados
            if page_num > 90:
                logger.info("Zona crítica - comportamento extra cauteloso")
                self.simula_movimento_do_mouse()
                self.delay_aleatorio(2, 4)
            
            medicos_on_page = self.scraping_pagina_atual()
            
            if not medicos_on_page:
                # Verifica se é fim natural ou bloqueio
                is_blocked, reason = self.detectar_bloqueio_ou_fim()
                
                if "Nenhum resultado a mostrar" in reason:
                    logger.info("Fim natural dos resultados detectado.")
                    break
                elif is_blocked:
                    logger.error(f"Bloqueio detectado: {reason}")
                    # Tenta recuperação antes de desistir
                    if self.tentar_recuperacao(page_num):
                        logger.info("Recuperação bem-sucedida, continuando...")
                        continue
                    else:
                        logger.error("Falha na recuperação. Encerrando.")
                        break
                else:
                    paginas_vazias_consecutivas += 1
                    logger.warning(f"Página {page_num} vazia. (Tentativa {paginas_vazias_consecutivas}/3)")
                    if paginas_vazias_consecutivas >= 3:
                        logger.error("Três páginas vazias consecutivas. Verificando se é bloqueio...")
                        if self.consecutive_blocks > 0:
                            logger.error("Bloqueio confirmado após páginas vazias.")
                        break
            else:
                paginas_vazias_consecutivas = 0
                all_medicos.extend(medicos_on_page)
                
                # Salva progresso periodicamente
                if page_num % 20 == 0:
                    self._salvar_progresso_temporario(all_medicos, uf, page_num)

            if not self.navega_para_proxima_pagina(page_num):
                break
            
            page_num += 1

        if all_medicos:
            logger.info(f"Scraping finalizado. Total de {len(all_medicos)} médicos encontrados para {uf}.")
            df = pd.DataFrame(all_medicos)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = CSV_PATH / f"medicos_{uf}_{ts}_refatorado.csv"
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            logger.info(f"Dados salvos com sucesso em: {output_path}")
        else:
            logger.warning(f"Nenhum médico foi salvo para a UF {uf}.")
    
    def _salvar_progresso_temporario(self, medicos: List[Dict], uf: str, pagina: int):
        """Salva progresso temporariamente para evitar perda de dados."""
        try:
            if medicos:
                df = pd.DataFrame(medicos)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_path = CSV_PATH / f"temp_medicos_{uf}_p{pagina}_{ts}.csv"
                df.to_csv(temp_path, index=False, encoding="utf-8-sig")
                logger.info(f"Progresso salvo: {len(medicos)} registros até página {pagina}")
        except Exception as e:
            logger.error(f"Erro ao salvar progresso: {e}")

# --- Ponto de Entrada do Script ---

if __name__ == "__main__":
    UF_PARA_SCRAPEAR = "RR"  # Altere aqui para a UF desejada
    
    logger.info("=== SCRAPER CFM COM DETECÇÃO AVANÇADA DE BLOQUEIOS ===")
    logger.info("🛡️  Melhorias implementadas:")
    logger.info("  ✅ Detecção da mensagem 'Nenhum resultado a mostrar'")
    logger.info("  ✅ Sistema de recuperação de bloqueios")
    logger.info("  ✅ Delays adaptativos próximo à página 97")
    logger.info("  ✅ Salvamento de progresso automático")
    logger.info("  ✅ Filtragem de cards inválidos")
    logger.info("")
    
    try:
        with sync_playwright() as playwright:
            with CFMScraper(playwright, headless=False) as scraper:
                scraper.run(uf=UF_PARA_SCRAPEAR)
    except KeyboardInterrupt:
        logger.info("⏹️  Processo interrompido pelo usuário")
    except Exception as e:
        logger.critical(f"❌ Erro fatal no scraper: {e}", exc_info=True)
    
    logger.info("=== PROCESSO FINALIZADO ===")