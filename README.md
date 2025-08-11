# webscraping-cfm-luiza

## Descrição

Este projeto realiza webscraping dos dados de médicos diretamente do site do Conselho Federal de Medicina (CFM). O objetivo é coletar e processar essas informações para utilização na tese de doutorado em Economia da Luiza.

## Tecnologias Utilizadas

- **Python 3.11**: Linguagem principal do projeto.
- **pyenv**: Gerenciador de versões do Python.
- **uv**: Gerenciador de ambientes virtuais e pacotes.
- **pandas**: Manipulação e análise de dados.
- **playwright**: Automação de navegadores para raspagem de dados.
- **notebook**: Criação de notebooks para análise e processamento dos dados.

## Instalação

1. Clone o repositório:
    ```bash
    git clone https://github.com/seu-usuario/webscraping-cfm-luiza.git
    cd webscraping-cfm-luiza
    ```

2. Instale o Python 3.11 com pyenv:
    ```bash
    pyenv install 3.11.0
    pyenv local 3.11.0
    ```

3. Crie e ative o ambiente virtual com uv:
    ```bash
    uv venv .venv
    source .venv/bin/activate  # Linux/macOS
    .venv\Scripts\activate     # Windows
    ```

4. Instale as dependências:
    ```bash
    uv pip install -r requirements.txt
    ```

## Execução do Webscraper

Execute o script principal para iniciar a raspagem dos dados:
```bash
uv run python -m src.get_scraper.py
```

## Notebooks

Os notebooks de análise e processamento dos dados estão disponíveis na pasta `notebooks`.

## Observações

- Certifique-se de ter o [Playwright](https://playwright.dev/python/docs/intro) instalado e configurado corretamente.
- Os dados coletados são utilizados exclusivamente para fins acadêmicos.
- Para dúvidas ou contribuições, abra uma issue ou envie um pull request.