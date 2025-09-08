from playwright.sync_api import sync_playwright
import requests
import pandas as pd
from time import sleep
from datetime import datetime
from pathlib import Path
import logging
import random
import time
import urllib.parse

# Diretório para salvar o arquivo de saída
DATA_DIR = (Path(__file__).resolve().parent / ".." / "data").resolve()
CSV_PATH = DATA_DIR / "dados_csv"
LOG_PATH = DATA_DIR / "logs"

for d in (DATA_DIR, CSV_PATH, LOG_PATH):
            d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH / "scraping_api.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_URL = "https://portal.cfm.org.br/api_rest_php/api/v1/medicos/buscar_medicos"

# Lista de User-Agents realistas para rotação
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def random_delay(min_seconds=1, max_seconds=3):
    """Gera um delay aleatório entre requisições"""
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Aguardando {delay:.2f} segundos...")
    sleep(delay)

def simulate_human_typing(page, selector, text, typing_delay_range=(0.05, 0.15)):
    """Simula digitação humana com delays aleatórios"""
    element = page.locator(selector)
    element.click()
    element.fill('')  # Limpa o campo
    
    for char in text:
        element.type(char)
        sleep(random.uniform(*typing_delay_range))

def simulate_mouse_movement(page):
    """Simula movimentos aleatórios do mouse"""
    try:
        # Move o mouse para posições aleatórias na tela
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            page.mouse.move(x, y)
            sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        logger.warning(f"Erro ao simular movimento do mouse: {e}")

def get_random_user_agent():
    """Retorna um User-Agent aleatório"""
    return random.choice(USER_AGENTS)

def simulate_human_reading(page, min_time=3, max_time=8):
    """Simula leitura humana da página"""
    try:
        # Simula scroll para baixo lentamente
        page_height = page.evaluate("document.body.scrollHeight")
        current_position = 0
        scroll_steps = random.randint(3, 7)
        
        for i in range(scroll_steps):
            # Calcula posição do scroll
            target_position = (i + 1) * (page_height / scroll_steps)
            page.evaluate(f"window.scrollTo({{top: {target_position}, behavior: 'smooth'}})")
            
            # Pausa variável durante o scroll
            sleep(random.uniform(0.8, 2.5))
            
            # Ocasionalmente move o mouse durante o scroll
            if random.random() < 0.6:
                x = random.randint(200, 1000)
                y = random.randint(200, 600)
                page.mouse.move(x, y)
                sleep(random.uniform(0.2, 0.8))
        
        # Volta ao topo ocasionalmente
        if random.random() < 0.3:
            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            sleep(random.uniform(1, 2))
            
    except Exception as e:
        logger.warning(f"Erro ao simular leitura: {e}")
        # Fallback simples
        sleep(random.uniform(min_time, max_time))

def simulate_typing_mistakes(page, selector, text):
    """Simula digitação com erros humanos"""
    try:
        element = page.locator(selector)
        element.click()
        element.fill('')
        
        # Ocasionalmente comete "erros" de digitação
        if random.random() < 0.2 and len(text) > 2:
            # Digita errado primeiro
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            element.type(text[:2] + wrong_char)
            sleep(random.uniform(0.3, 0.8))
            # Corrige com backspace
            element.press('Backspace')
            sleep(random.uniform(0.2, 0.5))
            # Continua digitando certo
            element.type(text[2:])
        else:
            # Digitação normal com variação de velocidade
            for i, char in enumerate(text):
                element.type(char)
                if i < len(text) - 1:  # Não pausa após o último caractere
                    delay = random.uniform(0.05, 0.25)
                    if char == ' ':
                        delay *= 2  # Pausa maior após espaços
                    sleep(delay)
    except Exception as e:
        logger.warning(f"Erro na simulação de digitação: {e}")
        # Fallback para digitação simples
        simulate_human_typing(page, selector, text)

def add_random_browser_noise(page):
    """Adiciona ruído/atividade aleatória do navegador"""
    try:
        # Ocasionalmente abre nova aba em branco (simula comportamento real)
        if random.random() < 0.1:
            new_tab = page.context.new_page()
            sleep(random.uniform(0.5, 1.5))
            new_tab.close()
        
        # Simula verificação de outras abas
        if random.random() < 0.15:
            # Simula Alt+Tab ou Ctrl+Tab
            sleep(random.uniform(0.3, 0.8))
        
        # Move mouse fora da área de trabalho ocasionalmente
        if random.random() < 0.3:
            page.mouse.move(random.randint(50, 150), random.randint(50, 150))
            sleep(random.uniform(0.2, 0.6))
            
    except Exception as e:
        logger.warning(f"Erro no ruído do navegador: {e}")

def intelligent_delay(page_number, base_delay=2.0, escalation_factor=1.2):
    """Delay inteligente que aumenta com suspeitas de detecção"""
    # Base delay aumenta com o número da página
    if page_number <= 5:
        multiplier = 1.0
    elif page_number <= 20:
        multiplier = 1.3
    elif page_number <= 50:
        multiplier = 1.8
    elif page_number <= 100:
        multiplier = 2.5
    else:
        multiplier = 3.5  # Muito conservador para páginas altas
    
    # Adiciona variação aleatória significativa
    actual_delay = base_delay * multiplier * random.uniform(0.8, 2.2)
    
    # Delays especiais em marcos importantes
    if page_number % 25 == 0:  # A cada 25 páginas
        actual_delay *= 2  # Pausa dobrada
        logger.info(f"Pausa especial na página {page_number}")
    elif page_number % 10 == 0:  # A cada 10 páginas
        actual_delay *= 1.5
        
    return actual_delay


def get_cookies_after_busca(uf):
    captured_request = None
    captured_response = None
    
    def handle_request(request):
        nonlocal captured_request
        if "buscar_medicos" in request.url:
            # Tenta capturar o post_data de forma diferente
            post_data = None
            try:
                post_data = request.post_data
                if post_data is None:
                    # Tenta capturar o body da requisição
                    post_data = request.body()
            except:
                pass
            
            captured_request = {
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "post_data": post_data
            }
            print("DEBUG - Requisição capturada:")
            print(f"  URL: {captured_request['url']}")
            print(f"  Method: {captured_request['method']}")
            print(f"  Headers: {captured_request['headers']}")
            print(f"  Post Data: {captured_request['post_data']}")
    
    def handle_response(response):
        nonlocal captured_response
        if "buscar_medicos" in response.url:
            try:
                body = response.body()
                captured_response = {
                    "url": response.url,
                    "status": response.status,
                    "headers": response.headers,
                    "body": body.decode('utf-8') if body else None
                }
                print(f"DEBUG - Resposta capturada: {captured_response}")
            except Exception as e:
                print(f"DEBUG - Erro ao capturar resposta: {e}")
    
    with sync_playwright() as p:
        # Usa User-Agent aleatório e configurações mais humanas
        user_agent = get_random_user_agent()
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-extensions-file-access-check',
                '--disable-extensions',
                '--disable-plugins-discovery',
                '--disable-default-apps'
            ]
        )
        context = browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1366, 'height': 768},
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        # Remove sinais de automação
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            window.chrome = {
                runtime: {}
            };
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en'],
            });
            
            const originalQuery = window.navigator.permissions.query;
            return window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        page = context.new_page()
        logger.info(f"Usando User-Agent: {user_agent}")
        
        # Intercepta requisições e respostas
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        print(f"Abrindo página de busca para UF {uf}...")
        # Navegação mais robusta com timeout maior e fallback
        try:
            # Tenta primeiro com networkidle
            page.goto("https://portal.cfm.org.br/busca-medicos", wait_until='networkidle', timeout=60000)
        except Exception as e:
            print(f"DEBUG - Falha com networkidle, tentando com domcontentloaded: {e}")
            try:
                # Fallback para domcontentloaded
                page.goto("https://portal.cfm.org.br/busca-medicos", wait_until='domcontentloaded', timeout=45000)
            except Exception as e2:
                print(f"DEBUG - Falha com domcontentloaded, tentando sem wait_until: {e2}")
                # Último fallback sem wait_until
                page.goto("https://portal.cfm.org.br/busca-medicos", timeout=30000)
        
        random_delay(3, 5)  # Pausa maior após carregamento
        
        # Simula movimento do mouse após carregamento
        simulate_mouse_movement(page)
        random_delay(1, 2)
        
        # Extrai o SECURITYHASH da página - procura em vários locais
        security_hash = None
        try:
            # Procura por input hidden com name="securityhash"
            security_hash_element = page.locator('input[name="securityhash"]')
            if security_hash_element.count() > 0:
                security_hash = security_hash_element.first.get_attribute('value')
                print(f"DEBUG - SECURITYHASH encontrado (input): {security_hash}")
            else:
                # Procura por outros possíveis locais
                # 1. Meta tag
                meta_security = page.locator('meta[name="securityhash"]')
                if meta_security.count() > 0:
                    security_hash = meta_security.first.get_attribute('content')
                    print(f"DEBUG - SECURITYHASH encontrado (meta): {security_hash}")
                else:
                    # 2. Procura no JavaScript da página
                    page_content = page.content()
                    import re
                    security_match = re.search(r'securityhash["\']?\s*[:=]\s*["\']([a-f0-9]+)["\']', page_content, re.IGNORECASE)
                    if security_match:
                        security_hash = security_match.group(1)
                        print(f"DEBUG - SECURITYHASH encontrado (regex): {security_hash}")
                    else:
                        print("DEBUG - SECURITYHASH não encontrado em nenhum local")
        except Exception as e:
            print(f"DEBUG - Erro ao extrair SECURITYHASH: {e}")
        
        # Simula movimento do mouse e interação mais humana
        simulate_mouse_movement(page)
        random_delay(1, 2)
        
        # Seleciona UF com movimento mais natural
        uf_selector = page.locator('select[name="uf"]')
        uf_selector.hover()
        random_delay(0.5, 1)
        uf_selector.select_option(uf)
        
        # Simula leitura da página
        random_delay(2, 4)
        simulate_mouse_movement(page)
        
        # Clica no botão de busca
        search_button = page.locator('button.btn-buscar')
        search_button.hover()
        random_delay(0.5, 1)
        search_button.click()
        
        print("Aguardando resultados carregarem...")
        try:
            page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=120_000)
            print("Resultados carregados! Extraindo cookies...")
        except Exception as e:
            print(f"DEBUG - Erro ao aguardar resultados: {e}")
            # Tenta aguardar qualquer elemento de resultado
            try:
                page.wait_for_selector('.busca-resultado', timeout=60_000)
                print("Página de resultados carregada (sem itens específicos)")
            except:
                print("WARNING - Não foi possível aguardar elementos de resultado, continuando...")
        
        # Simula leitura dos resultados
        simulate_mouse_movement(page)
        random_delay(2, 3)
        
        cookies = context.cookies()
        
        # Tenta fazer a requisição imediatamente, sem fechar o navegador
        print("DEBUG - Tentando requisição imediata com o navegador ainda aberto...")
        try:
            # Usa o payload real capturado
            if captured_request and captured_request.get('post_data'):
                import urllib.parse
                real_payload = urllib.parse.parse_qs(captured_request['post_data'])
                payload_dict = {}
                for key, value_list in real_payload.items():
                    payload_dict[key] = value_list[0] if value_list else ""
                
                # Usa o contexto do navegador para fazer a requisição
                response = page.request.post(API_URL, data=payload_dict, timeout=30)
                print(f"DEBUG - Resposta imediata: {response.json()}")
            else:
                print("DEBUG - Payload real não disponível para requisição imediata")
        except Exception as e:
            print(f"DEBUG - Erro na requisição imediata: {e}")
        
        browser.close()
        
        # Monta string de cookies para requests
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        return cookie_str, captured_request, captured_response, security_hash

def scrap_cfm_api_hibrido(uf, delay=1.5, max_paginas=None):
    logger.info(f"Iniciando scraping híbrido via Playwright+requests para UF {uf}")
    cookie_str, captured_request, captured_response, security_hash = get_cookies_after_busca(uf)
    
    # Debug: mostra o que o navegador realmente retornou
    if captured_response:
        print(f"DEBUG - Resposta real do navegador: {captured_response.get('body', 'N/A')}")
    
    # Debug: mostra o payload real que o navegador enviou
    if captured_request and captured_request.get('post_data'):
        print(f"DEBUG - Payload real do navegador: {captured_request['post_data']}")
        # Tenta usar o payload real do navegador
        try:
            import urllib.parse
            real_payload = urllib.parse.parse_qs(captured_request['post_data'])
            print(f"DEBUG - Payload parseado: {real_payload}")
        except Exception as e:
            print(f"DEBUG - Erro ao parsear payload real: {e}")
    
    # Usa Session para manter a sessão
    session = requests.Session()
    
    # Se temos os headers reais do navegador, usa eles
    if captured_request and captured_request.get('headers'):
        print("DEBUG - Usando headers reais do navegador")
        real_headers = captured_request['headers'].copy()
        # Remove headers que podem causar problemas
        headers_to_remove = ['content-length', 'host']
        for header in headers_to_remove:
            real_headers.pop(header, None)
        # Atualiza User-Agent para um aleatório
        real_headers['User-Agent'] = get_random_user_agent()
        session.headers.update(real_headers)
        logger.info(f"Usando User-Agent atualizado: {real_headers['User-Agent']}")
    else:
        print("DEBUG - Usando headers padrão")
        # Headers padrão com User-Agent aleatório
        random_user_agent = get_random_user_agent()
        session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": random_user_agent,
            "Referer": "https://portal.cfm.org.br/busca-medicos",
            "Origin": "https://portal.cfm.org.br",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Not;A=Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        })
        logger.info(f"Usando User-Agent padrão: {random_user_agent}")
    
    # Adiciona cookies à sessão
    for cookie in cookie_str.split('; '):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            session.cookies.set(name, value, domain='portal.cfm.org.br')
    
    # Tenta usar o payload real capturado do navegador
    real_payload_data = None
    if captured_request and captured_request.get('post_data'):
        try:
            import urllib.parse
            real_payload_data = urllib.parse.parse_qs(captured_request['post_data'])
            print(f"DEBUG - Usando payload real do navegador: {real_payload_data}")
        except Exception as e:
            print(f"DEBUG - Erro ao processar payload real: {e}")
    
    # Se temos o payload real, usa ele imediatamente
    if real_payload_data:
        print("DEBUG - Fazendo requisição imediata com payload real...")
        payload = {}
        for key, value_list in real_payload_data.items():
            payload[key] = value_list[0] if value_list else ""
        
        # Adiciona o SECURITYHASH conhecido ao payload real
        known_security_hash = "9e47994169b1ec0a0de80233de70a610"
        payload["securityhash"] = known_security_hash
        print(f"DEBUG - Adicionando SECURITYHASH conhecido ao payload real: {known_security_hash}")
        
        try:
            print(f"DEBUG - Payload real enviado: {payload}")
            print(f"DEBUG - Headers da sessão: {dict(session.headers)}")
            print(f"DEBUG - Cookies da sessão: {dict(session.cookies)}")
            resp = session.post(API_URL, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            #print(f"DEBUG - Resposta da API com payload real: {data}")
            print(f"DEBUG - Status da resposta: {resp.status_code}")
            print(f"DEBUG - Headers da resposta: {dict(resp.headers)}")
            
            # Se funcionou, continua com o loop normal
            todos_medicos = []
            if data.get("dados") and data.get("dados") is not None:
                print("DEBUG - Payload real funcionou! Continuando...")
                medicos = data.get("dados", [])
                todos_medicos.extend(medicos)
                pagina = 2  # Começa da página 2
            else:
                print("DEBUG - Payload real não funcionou, tentando abordagem alternativa...")
                pagina = 1
        except Exception as e:
            print(f"DEBUG - Erro com payload real: {e}")
            pagina = 1
    else:
        pagina = 1
    
    todos_medicos = []
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    while True:
        # Usa o payload real se disponível, senão usa o padrão
        if real_payload_data and pagina > 1:
            payload = {}
            for key, value_list in real_payload_data.items():
                payload[key] = value_list[0] if value_list else ""
            # Atualiza a página
            payload["pagina"] = str(pagina)
            print(f"DEBUG - Payload baseado no navegador (página {pagina}): {payload}")
        else:
            # Payload padrão
            payload = {
                "uf": uf,
                "pagina": str(pagina),
                "nome": "",
                "crm": "",
                "municipio": "",
                "especialidade": "",
                "area_atuacao": "",
                "tipo_inscricao": "",
                "situacao": "",
                "situacao_2": "",
            }
            
                    # Adiciona o SECURITYHASH - usa o que sabemos que funciona
        known_security_hash = "9e47994169b1ec0a0de80233de70a610"
        payload["securityhash"] = known_security_hash
        print(f"DEBUG - Adicionando SECURITYHASH conhecido: {known_security_hash}")
        
        try:
            print(f"DEBUG - Payload enviado: {payload}")
            
            # Adiciona delay aleatório antes da requisição
            random_delay(1.5, 3.5)
            
            resp = session.post(API_URL, data=payload, timeout=30)
            resp.raise_for_status()
            
            # Verifica se a resposta é válida
            if resp.status_code != 200:
                raise Exception(f"Status code inválido: {resp.status_code}")
                
            try:
                data = resp.json()
            except ValueError as e:
                raise Exception(f"Resposta não é JSON válido: {e}")
                
            print(f"DEBUG - Resposta da API: {data}")
            consecutive_failures = 0  # Reset contador de falhas
            
        except requests.exceptions.RequestException as e:
            consecutive_failures += 1
            logger.error(f"Erro de requisição na página {pagina}: {e} (tentativa {consecutive_failures})")
            print(f"DEBUG - Erro na requisição: {e}")
            
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"Muitas falhas consecutivas ({consecutive_failures}). Encerrando.")
                break
            
            # Pausa mais longa em caso de erro
            print(f"Aguardando antes de tentar novamente...")
            random_delay(5, 10)
            continue
            
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"Erro geral na página {pagina}: {e} (tentativa {consecutive_failures})")
            print(f"DEBUG - Erro geral: {e}")
            
            # Se for erro de bloqueio/captcha, pausa mais longa
            error_msg = str(e).lower()
            if any(term in error_msg for term in ['blocked', 'captcha', 'rate limit', 'too many requests']):
                logger.warning("Possível bloqueio detectado. Pausando por mais tempo...")
                random_delay(30, 60)
            else:
                random_delay(5, 10)
                
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"Muitas falhas consecutivas ({consecutive_failures}). Encerrando.")
                break
            
            continue
        medicos = data.get("dados", [])
        if not medicos or medicos is None:
            logger.info(f"Nenhum médico encontrado na página {pagina}. Encerrando scraping.")
            break
        logger.info(f"Página {pagina}: {len(medicos)} médicos encontrados.")
        todos_medicos.extend(medicos)
        if max_paginas and pagina >= max_paginas:
            logger.info(f"Máximo de páginas {max_paginas} atingido.")
            break
        pagina += 1
        
        # Rotaciona User-Agent ocasionalmente para parecer mais humano
        if pagina % 5 == 0:  # A cada 5 páginas
            new_user_agent = get_random_user_agent()
            session.headers.update({'User-Agent': new_user_agent})
            logger.info(f"User-Agent rotacionado para: {new_user_agent}")
            
        # Delay variável - páginas posteriores têm delays maiores
        base_delay = delay
        if pagina > 10:
            base_delay = delay * 1.5
        elif pagina > 20:
            base_delay = delay * 2
            
        # Adiciona variação aleatória ao delay
        actual_delay = random.uniform(base_delay, base_delay * 1.8)
        logger.info(f"Pausando {actual_delay:.2f}s antes da próxima página...")
        sleep(actual_delay)
    if todos_medicos:
        df = pd.DataFrame(todos_medicos)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_csv = CSV_PATH / f"medicos_{uf}_{ts}_api.csv"
        df.to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
        print(f"Salvo {len(df)} médicos em {arquivo_csv}")
        logger.info(f"Salvo {len(df)} médicos em {arquivo_csv}")
        return df
    else:
        print("Nenhum médico encontrado.")
        logger.info("Nenhum médico encontrado.")
        return None

def detect_blocking_patterns(page):
    """Detecta padrões de bloqueio na página"""
    try:
        content = page.content().lower()
        blocking_indicators = [
            'blocked', 'captcha', 'verificação', 'suspeita', 'bot',
            'rate limit', 'too many requests', 'acesso negado',
            'access denied', 'forbidden', 'erro 403', 'erro 429'
        ]
        
        for indicator in blocking_indicators:
            if indicator in content:
                logger.warning(f"Possível bloqueio detectado: '{indicator}'")
                return True
                
        # Verifica se há elementos de busca na página
        if page.locator('.busca-resultado').count() == 0 and page.locator('select[name="uf"]').count() == 0:
            logger.warning("Página não contém elementos esperados - possível redirecionamento")
            return True
            
        return False
    except Exception as e:
        logger.error(f"Erro ao detectar bloqueio: {e}")
        return False

def save_session_state(todos_medicos, uf, pagina_atual):
    """Salva o estado da sessão para recuperação"""
    try:
        if todos_medicos:
            df = pd.DataFrame(todos_medicos)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_temp = CSV_PATH / f"temp_medicos_{uf}_p{pagina_atual}_{ts}.csv"
            df.to_csv(arquivo_temp, index=False, encoding="utf-8-sig")
            logger.info(f"Estado da sessão salvo: {len(todos_medicos)} médicos até página {pagina_atual}")
            return arquivo_temp
    except Exception as e:
        logger.error(f"Erro ao salvar estado da sessão: {e}")
    return None

def scrap_cfm_pure_playwright(uf, delay=1.5, max_paginas=None, start_page=1):
    """Scraping usando apenas Playwright - sem requests"""
    logger.info(f"Iniciando scraping puro via Playwright para UF {uf} (página inicial: {start_page})")
    
    with sync_playwright() as p:
        # Configurações humanizadas para Playwright
        user_agent = get_random_user_agent()
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-extensions-file-access-check',
                '--disable-extensions',
                '--disable-plugins-discovery',
                '--disable-default-apps'
            ]
        )
        # Viewport mais variável e realista
        viewports = [
            {'width': 1366, 'height': 768},
            {'width': 1920, 'height': 1080},
            {'width': 1440, 'height': 900},
            {'width': 1536, 'height': 864},
            {'width': 1280, 'height': 720}
        ]
        
        context = browser.new_context(
            user_agent=user_agent,
            viewport=random.choice(viewports),
            locale='pt-BR',
            timezone_id='America/Sao_Paulo',
            # Simula conexão mais lenta ocasionalmente
            extra_http_headers={
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': random.choice(['no-cache', 'max-age=0']),
                'DNT': '1',  # Do Not Track
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        # Script mais avançado para remover sinais de automação
        context.add_init_script("""
            // Remove webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Adiciona chrome objeto mais realista
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Plugins mais realistas
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [];
                    plugins[0] = { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' };
                    plugins[1] = { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' };
                    plugins[2] = { name: 'Native Client', filename: 'internal-nacl-plugin' };
                    return plugins;
                },
            });
            
            // Permissões mais realistas
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Adiciona propriedades de hardware mais realistas
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4,
            });
            
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
            });
            
            // Language array mais realista
            Object.defineProperty(navigator, 'languages', {
                get: () => ['pt-BR', 'pt', 'en-US', 'en'],
            });
            
            // Adiciona getBattery se não existir
            if (!navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 0.99
                });
            }
        """)
        
        page = context.new_page()
        logger.info(f"Usando User-Agent: {user_agent}")
        
        print(f"Abrindo página de busca para UF {uf}...")
        # Navegação mais robusta
        try:
            # Tenta primeiro com networkidle
            page.goto("https://portal.cfm.org.br/busca-medicos", wait_until='networkidle', timeout=60000)
        except Exception as e:
            print(f"DEBUG - Falha com networkidle, tentando com domcontentloaded: {e}")
            try:
                # Fallback para domcontentloaded
                page.goto("https://portal.cfm.org.br/busca-medicos", wait_until='domcontentloaded', timeout=45000)
            except Exception as e2:
                print(f"DEBUG - Falha com domcontentloaded, tentando sem wait_until: {e2}")
                # Último fallback sem wait_until
                page.goto("https://portal.cfm.org.br/busca-medicos", timeout=30000)
        
        random_delay(3, 5)  # Pausa maior após carregamento
        simulate_mouse_movement(page)
        random_delay(1, 2)
        
        # Comportamento muito mais humano na busca inicial
        logger.info("Simulando comportamento humano na página...")
        
        # Simula "leitura" da página inicial
        simulate_human_reading(page, 3, 6)
        
        # Ações mais hesitantes e humanas
        simulate_mouse_movement(page)
        random_delay(1, 2)
        
        # Ocasionalmente "explora" outros campos antes de selecionar UF
        if random.random() < 0.3:
            try:
                # Clica em outros campos como se estivesse explorando
                nome_field = page.locator('input[name="nome"]')
                if nome_field.count() > 0:
                    nome_field.click()
                    random_delay(0.8, 1.5)
                    # "Decide" não preencher e clica fora
                    page.mouse.click(500, 300)
                    random_delay(0.5, 1)
            except:
                pass
        
        # Seleciona UF com mais hesitação
        uf_selector = page.locator('select[name="uf"]')
        uf_selector.hover()
        random_delay(1, 2)  # Hesitação maior
        
        # "Pensa" antes de selecionar
        if random.random() < 0.2:
            # Abre o dropdown mas não seleciona imediatamente
            uf_selector.click()
            random_delay(1.5, 3)
        
        uf_selector.select_option(uf)
        logger.info(f"Selecionou UF: {uf}")
        
        # Pausa maior para "pensar" sobre a busca
        random_delay(3, 6)
        simulate_mouse_movement(page)
        
        # Ação mais deliberada no botão
        search_button = page.locator('button.btn-buscar')
        search_button.hover()
        random_delay(1, 2.5)  # Hesitação maior
        
        # Adiciona ruído antes do clique final
        add_random_browser_noise(page)
        
        search_button.click()
        logger.info("Iniciou busca com comportamento humanizado")
        
        print("Aguardando resultados carregarem...")
        try:
            page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=120_000)
            print("Resultados carregados!")
        except Exception as e:
            print(f"DEBUG - Erro ao aguardar resultados: {e}")
            # Tenta aguardar qualquer elemento de resultado
            try:
                page.wait_for_selector('.busca-resultado', timeout=60_000)
                print("Página de resultados carregada (sem itens específicos)")
            except:
                print("WARNING - Não foi possível aguardar elementos de resultado, continuando...")
        
        simulate_mouse_movement(page)
        random_delay(2, 3)
        
        todos_medicos = []
        pagina = start_page
        session_saves = 0
        last_successful_page = 0
        consecutive_empty_pages = 0
        
        while True:
            print(f"Processando página {pagina}...")
            
            # Detecta bloqueios antes de processar
            if detect_blocking_patterns(page):
                logger.error(f"Bloqueio detectado na página {pagina}!")
                
                # Salva progresso antes de parar
                if todos_medicos:
                    save_session_state(todos_medicos, uf, pagina)
                    
                # Estratégia de recuperação
                logger.info("Tentando estratégia de recuperação...")
                
                try:
                    # Pausa longa
                    recovery_delay = random.uniform(60, 120)
                    logger.info(f"Pausa de recuperação: {recovery_delay:.1f}s")
                    sleep(recovery_delay)
                    
                    # Recarrega página
                    page.reload(wait_until='domcontentloaded', timeout=45000)
                    random_delay(3, 6)
                    
                    # Verifica se ainda está bloqueado
                    if detect_blocking_patterns(page):
                        logger.error("Ainda bloqueado após recuperação. Encerrando.")
                        break
                    else:
                        logger.info("Recuperação bem-sucedida!")
                        continue
                        
                except Exception as e:
                    logger.error(f"Falha na recuperação: {e}")
                    break
            
            # Extrai dados da página atual
            try:
                # Simula "ansiedade" humana aguardando resultados
                logger.info(f"Aguardando resultados da página {pagina}...")
                
                # Aguarda os resultados carregarem
                page.wait_for_selector('div.busca-resultado > div[class^="resultado-item"]', timeout=45000)
                
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
                    consecutive_empty_pages += 1
                    print(f"Nenhum médico encontrado na página {pagina}. (Páginas vazias consecutivas: {consecutive_empty_pages})")
                    
                    # Se muitas páginas vazias consecutivas, pode ser fim ou bloqueio
                    if consecutive_empty_pages >= 3:
                        logger.warning(f"Muitas páginas vazias consecutivas ({consecutive_empty_pages}). Verificando bloqueio...")
                        if detect_blocking_patterns(page):
                            logger.error("Bloqueio confirmado após páginas vazias")
                        break
                    
                    # Pausa maior para páginas vazias
                    empty_page_delay = random.uniform(5, 10)
                    logger.info(f"Pausa especial para página vazia: {empty_page_delay:.1f}s")
                    sleep(empty_page_delay)
                else:
                    consecutive_empty_pages = 0  # Reset contador
                    last_successful_page = pagina
                
                print(f"Página {pagina}: {len(medicos_pagina)} médicos encontrados.")
                if medicos_pagina:
                    print("DEBUG - Primeiro médico extraído:")
                    for key, value in medicos_pagina[0].items():
                        print(f"  {key}: {value}")
                todos_medicos.extend(medicos_pagina)
                
                # Simula "leitura" dos resultados
                simulate_human_reading(page, 2, 5)
                
                # Salva progresso periodicamente
                if pagina % 20 == 0:  # A cada 20 páginas
                    save_session_state(todos_medicos, uf, pagina)
                    session_saves += 1
                    
                    # Pausa extra para "simular pausa para café"
                    if session_saves % 3 == 0:  # A cada 60 páginas (3 saves)
                        coffee_break = random.uniform(30, 90)
                        logger.info(f"Pausa para 'café': {coffee_break:.1f}s")
                        sleep(coffee_break)
                
                if max_paginas and pagina >= max_paginas:
                    print(f"Máximo de páginas {max_paginas} atingido.")
                    break
                
                # Tenta ir para próxima página usando múltiplas estratégias
                try:
                    # Debug: mostra quais páginas estão disponíveis
                    available_pages = page.evaluate("""
                        () => {
                            const links = document.querySelectorAll('#paginacao a');
                            const pages = [];
                            links.forEach(link => {
                                const text = link.textContent.trim();
                                if (text && !isNaN(text) && text !== '') {
                                    pages.push(parseInt(text));
                                }
                            });
                            return pages.sort((a, b) => a - b);
                        }
                    """)
                    print(f"DEBUG - Páginas disponíveis: {available_pages}")
                    
                    # Descobre a página atual
                    current_page = page.evaluate("""
                        () => {
                            const activePage = document.querySelector('#paginacao .active, #paginacao .paginationjs-page.active');
                            if (activePage) {
                                return parseInt(activePage.textContent.trim());
                            }
                            return null;
                        }
                    """)
                    if current_page:
                        print(f"DEBUG - Página atual detectada: {current_page}")
                        if current_page != pagina:
                            print(f"DEBUG - Ajustando página de {pagina} para {current_page}")
                            pagina = current_page
                    
                    # Estratégia 1: Procura por um link que contenha o número da próxima página
                    next_page_number = pagina + 1
                    next_button = page.locator(f'xpath=//*[@id="paginacao"]//a[text()="{next_page_number}"]')
                    
                    if next_button.count() > 0:
                        print(f"Estratégia 1: Indo para página {next_page_number}...")
                        
                        # Comportamento muito mais humano na navegação
                        simulate_mouse_movement(page)
                        add_random_browser_noise(page)
                        
                        next_button.hover()
                        random_delay(1, 2.5)  # Hesitação maior
                        next_button.click()
                        
                        # Delay inteligente baseado no número da página
                        smart_delay = intelligent_delay(pagina, delay)
                        logger.info(f"Pausa inteligente: {smart_delay:.2f}s")
                        sleep(smart_delay)
                        
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
                    
                    # Estratégia 4: Procura por botão "Última" ou ">>"
                    last_button = page.locator('xpath=//*[@id="paginacao"]//a[contains(text(), "Última") or contains(text(), ">>")]')
                    if last_button.count() > 0:
                        print("Estratégia 4: Usando botão 'Última' para ir para a última página...")
                        last_button.click()
                        sleep(delay)
                        # Vai para a última página, então precisa descobrir qual é
                        pagina = 999999  # Será ajustado na próxima iteração
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
        
        # Salva os dados
        if todos_medicos:
            df = pd.DataFrame(todos_medicos)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_csv = CSV_PATH / f"medicos_{uf}_{ts}_playwright.csv"
            df.to_csv(arquivo_csv, index=False, encoding="utf-8-sig")
            logger.info(f"Dados salvos em {arquivo_csv}")
            print(f"Total de médicos encontrados: {len(todos_medicos)}")
        else:
            logger.info("Nenhum médico encontrado.")
            print("Nenhum médico encontrado.")

if __name__ == "__main__":
    print("=== SCRAPER CFM SUPER HUMANIZADO ===")
    print("\n🤖 Técnicas implementadas:")
    print("  ✅ Delays inteligentes crescentes")
    print("  ✅ Simulação de leitura e scroll")
    print("  ✅ Movimentos de mouse realistas")
    print("  ✅ Detecção e recuperação de bloqueios")
    print("  ✅ Salvamento de progresso automático")
    print("  ✅ Comportamento humano avançado")
    print()
    
    UF = "RR"
    BASE_DELAY = 3.0  # Delay base mais conservador
    
    try:
        print(f"🚀 Iniciando scraping para {UF} com delay base de {BASE_DELAY}s")
        print("⚠️  Este processo pode ser MUITO lento mas mais resistente a bloqueios")
        print()
        
        # Usa a abordagem mais robusta
        scrap_cfm_pure_playwright(UF, delay=BASE_DELAY, max_paginas=None, start_page=1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO no scraping: {e}")
        logger.error(f"Erro fatal: {e}")
        
    print("\n📊 Verifique os arquivos CSV gerados na pasta data/dados_csv/")
    print("💡 Para continuar de uma página específica, use: start_page=N")

