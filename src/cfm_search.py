from bs4 import BeautifulSoup
import pandas as pd
import os

path_html = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pagina_cfm.html"))

# Carregar o HTML baixado
with open(path_html, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Lista para armazenar os médicos
medicos = []

# Localize os cartões de médicos no HTML (exemplo: div.card-medic, ajustar conforme necessário)
cards = soup.find_all("div", class_="card-medic")  # O nome da classe pode variar, ajuste conforme o HTML real

for card in cards:
    # Adapte os seletores conforme o HTML real do cartão
    nome = card.find("h5").text.strip() if card.find("h5") else ""
    # O restante depende do HTML, suponha que cada info está em <li>:
    dados = card.find_all("li")
    info = [d.text.strip() for d in dados]

    # Exemplo de mapeamento se a ordem das <li> for sempre a mesma:
    medico = {
        "Nome": nome,
        "Nº inscrição": info[0] if len(info) > 0 else "",
        "UF inscrição": info[1] if len(info) > 1 else "",
        "Categoria": info[2] if len(info) > 2 else "",
        "Situação": info[3] if len(info) > 3 else "",
        # Continue para as outras colunas
    }
    medicos.append(medico)

# Converter em DataFrame
df = pd.DataFrame(medicos)

# Salvar como CSV
df.to_csv("medicos_cfm.csv", index=False, encoding="utf-8-sig")
print("Salvo: medicos_cfm.csv")
