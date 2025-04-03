Dashboard de Simulação de Cancelamento de Rotas
Este projeto é um dashboard interativo desenvolvido em Python com Streamlit para simular o impacto de cancelamentos de rotas nas métricas de GMV e cash‑repasse. A ideia é comparar os dados históricos (baseline) com os valores simulados após a aplicação de cancelamentos, permitindo a visualização em tempo real do efeito dos ajustes.

Funcionalidades
Upload de Planilha: Permite que o usuário faça upload de uma planilha (.csv ou .xlsx) contendo os dados de rotas, com colunas como id, rota, data, gmv e cash_repasse.
Exibição dos Dados: Exibe os dados originais (baseline) para conferência.
Simulação de Cancelamento: Para cada rota, o usuário pode marcar uma checkbox para cancelar a rota. Ao marcar, os valores de GMV e cash‑repasse são ajustados automaticamente conforme a lógica definida.
Visualização Comparativa: Apresenta um gráfico comparativo que mostra os totais de GMV e cash‑repasse antes (baseline) e depois da simulação (com cancelamentos).
Feedback Interativo: Informa o usuário sobre o status da simulação e permite confirmar os cancelamentos.

Tecnologias Utilizadas
Python 3.x
Streamlit – Framework para criação de dashboards interativos.
Pandas – Manipulação e análise de dados.
Plotly Express – Visualização interativa de dados.
SQLAlchemy (opcional) – Para integração futura com banco de dados.

Pré-requisitos
Python 3.7 ou superior instalado.
Pacotes Python listados no arquivo requirements.txt.

Instalação
Clone o repositório:
git clone https://github.com/seu-usuario/dashboard-simulacao-cancelamento.git
cd dashboard-simulacao-cancelamento

Crie e ative um ambiente virtual (opcional, mas recomendado):
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate     # Windows

Instale as dependências:
pip install -r requirements.txt

Uso
Inicie o dashboard:
streamlit run app.py

Upload dos Dados:
No dashboard, clique no botão de upload e selecione sua planilha (.csv ou .xlsx) que contenha as colunas obrigatórias: id, rota, data, gmv, cash_repasse.

Simulação de Cancelamentos:
Visualize os dados carregados na tabela.
Marque as checkboxes ao lado de cada rota que deseja cancelar.
Exemplo: Cancelar rota "Rota A" em "2025-04-01" zerará o GMV dessa rota e ajustará o cash‑repasse conforme a regra definida.

Visualização dos Resultados:
Verifique a tabela de simulação atualizada e o gráfico comparativo que mostra os totais de GMV e cash‑repasse do baseline (linha histórica) versus a simulação (linha ajustada).

Confirmação:
Após revisar as alterações, clique no botão de confirmação para registrar os cancelamentos. (Neste exemplo, os dados simulados são salvos em um arquivo CSV local.)

Estrutura do Projeto
dashboard-simulacao-cancelamento/
│
├── app.py                      # Arquivo principal do Streamlit
├── requirements.txt            # Lista de dependências do projeto
├── README.md                   # Este arquivo de documentação

Possíveis Melhorias
Integração com Banco de Dados: Consumir dados em tempo real a partir de um banco de dados utilizando SQLAlchemy ou outro conector.
WebSocket: Implementar WebSocket para atualizações em tempo real sem necessidade de recarregar o dashboard.
Lógica de Simulação Avançada: Refatorar as regras de negócio para refletir cenários mais realistas e complexos.
Autenticação: Adicionar autenticação e controle de acesso se o dashboard manipular dados sensíveis.

Contribuições
Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests com sugestões e melhorias.

