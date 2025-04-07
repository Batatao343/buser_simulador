import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Simulação de Cancelamento de Rotas", layout="wide")

# -------------------------
# Função para gerar dados de teste
# -------------------------
@st.cache_data
def gerar_dados():
    # Gerando datas para um mês (ex: janeiro de 2023)
    datas = pd.date_range(start="2023-01-01", end="2023-01-31", freq="D")
    rotas = ["R1", "R2", "R3"]
    regionais = ["Regional 1", "Regional 2", "Regional 1"]
    
    # Lista para acumular os dados
    dados = []
    for data in datas:
        for i, rota in enumerate(rotas):
            # Gerando valores fictícios
            # Baseline: valores de referência
            gmv_baseline = np.random.randint(1000, 2000)
            cash_baseline = np.random.randint(500, 1500)
            # Realizado: variação do baseline com ruído
            gmv_realizado = gmv_baseline + np.random.randint(-200, 200)
            cash_realizado = cash_baseline + np.random.randint(-100, 100)
            
            dados.append({
                "Data": data,
                "Rota": rota,
                "Regional": regionais[i],
                "GMV_baseline": gmv_baseline,
                "GMV_realizado": gmv_realizado,
                "Cash_baseline": cash_baseline,
                "Cash_realizado": cash_realizado
            })
    df = pd.DataFrame(dados)
    # Adiciona colunas auxiliares para cálculos de pesos
    df["Dia_da_Semana"] = df["Data"].dt.day_name()
    df["Dia_do_Mes"] = df["Data"].dt.day
    return df

# -------------------------
# Função para calcular a meta diluída
# -------------------------
def calcular_meta_diluida(df_agg, meta_mensal):
    # df_agg: DataFrame agregado por Data (somatório de todos os indicadores das rotas)
    # Calcula pesos por dia da semana:
    df_agg["Peso_Semana"] = df_agg.groupby("Dia_da_Semana")["GMV_baseline"].transform("sum")
    peso_total_semana = df_agg["GMV_baseline"].sum()
    df_agg["Peso_Semana"] = df_agg["GMV_baseline"] / peso_total_semana  # peso individual

    # Calcula pesos por dia do mês:
    df_agg["Peso_Mes"] = df_agg.groupby("Dia_do_Mes")["GMV_baseline"].transform("sum")
    peso_total_mes = df_agg["GMV_baseline"].sum()
    df_agg["Peso_Mes"] = df_agg["GMV_baseline"] / peso_total_mes  # peso individual

    # Combina os pesos (aqui usamos média simples; pode ser ajustado conforme necessidade)
    df_agg["Peso_Combinado"] = (df_agg["Peso_Semana"] + df_agg["Peso_Mes"]) / 2
    # Calcula a meta diluída
    df_agg["GMV_meta_diluida"] = meta_mensal * df_agg["Peso_Combinado"]
    # Para Cash, suponha que a meta seja uma porcentagem do GMV meta (ex: 70% do valor da meta GMV)
    df_agg["Cash_meta_diluida"] = df_agg["GMV_meta_diluida"] * 0.7
    return df_agg

# -------------------------
# Carregando os dados (pode substituir por upload de planilha)
# -------------------------
st.title("Simulação de Cancelamento de Rotas")

st.sidebar.header("Configurações")
usar_dados_exemplo = st.sidebar.checkbox("Usar dados de exemplo", value=True)

if usar_dados_exemplo:
    df = gerar_dados()
else:
    uploaded_file = st.sidebar.file_uploader("Carregue a planilha (CSV ou Excel)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith("csv"):
                df = pd.read_csv(uploaded_file, parse_dates=["Data"])
            else:
                df = pd.read_excel(uploaded_file, parse_dates=["Data"])
            df["Dia_da_Semana"] = df["Data"].dt.day_name()
            df["Dia_do_Mes"] = df["Data"].dt.day
        except Exception as e:
            st.error("Erro ao carregar os dados: " + str(e))
            st.stop()
    else:
        st.info("Carregue uma planilha para prosseguir.")
        st.stop()

# -------------------------
# Seleção de Rotas para Cancelamento
# -------------------------
st.sidebar.subheader("Seleção de Rotas para Cancelamento")
rotas_disponiveis = df["Rota"].unique().tolist()
rotas_canceladas = st.sidebar.multiselect("Selecione as rotas a cancelar:", rotas_disponiveis)

# -------------------------
# Agregação dos Indicadores Diários (para todos os dados)
# -------------------------
def agregar_indicadores(df_filtrado):
    # Agrega por Data (somando indicadores de todas as rotas não canceladas)
    agg = df_filtrado.groupby("Data").agg({
        "GMV_baseline": "sum",
        "GMV_realizado": "sum",
        "Cash_baseline": "sum",
        "Cash_realizado": "sum"
    }).reset_index()
    # Adiciona colunas de dia da semana e dia do mês para o cálculo da meta diluída
    agg["Dia_da_Semana"] = agg["Data"].dt.day_name()
    agg["Dia_do_Mes"] = agg["Data"].dt.day
    return agg

# Dados considerando todas as rotas (baseline para comparação)
df_agg_total = agregar_indicadores(df)

# Dados da simulação: excluindo rotas canceladas
if rotas_canceladas:
    df_sim = df[~df["Rota"].isin(rotas_canceladas)]
else:
    df_sim = df.copy()
df_agg_sim = agregar_indicadores(df_sim)

# -------------------------
# Definição de Meta Mensal e Cálculo da Meta Diluída
# -------------------------
st.sidebar.subheader("Configurações de Meta")
meta_mensal_gmv = st.sidebar.number_input("Meta Mensal GMV", min_value=1000, value=30000, step=1000)

# Calcula meta diluída para o baseline (todos os dados) e para a simulação
df_agg_total = calcular_meta_diluida(df_agg_total, meta_mensal_gmv)
df_agg_sim = calcular_meta_diluida(df_agg_sim, meta_mensal_gmv)

# -------------------------
# Gráficos Interativos com Plotly
# -------------------------
st.subheader("Gráficos Interativos")

# Gráfico de GMV
fig_gmv = px.line(df_agg_total, x="Data", y="GMV_baseline", labels={"GMV_baseline": "GMV (Baseline)"},
                  title="GMV - Baseline vs Realizado vs Meta vs Simulação")
# Adiciona a linha do GMV realizado (baseline)
fig_gmv.add_scatter(x=df_agg_total["Data"], y=df_agg_total["GMV_realizado"],
                    mode="lines", name="Realizado")
# Linha da Meta Diluída (baseline)
fig_gmv.add_scatter(x=df_agg_total["Data"], y=df_agg_total["GMV_meta_diluida"],
                    mode="lines", name="Meta Diluída (Baseline)")
# Linha da Simulação (excluindo rotas canceladas)
fig_gmv.add_scatter(x=df_agg_sim["Data"], y=df_agg_sim["GMV_realizado"],
                    mode="lines", name="Simulação (Sem rotas canceladas)")

fig_gmv.update_layout(hovermode="x unified")
st.plotly_chart(fig_gmv, use_container_width=True)

# Gráfico de Cash-Repasse
fig_cash = px.line(df_agg_total, x="Data", y="Cash_baseline", labels={"Cash_baseline": "Cash-Repasse (Baseline)"},
                   title="Cash-Repasse - Baseline vs Realizado vs Meta vs Simulação")
fig_cash.add_scatter(x=df_agg_total["Data"], y=df_agg_total["Cash_realizado"],
                     mode="lines", name="Realizado")
fig_cash.add_scatter(x=df_agg_total["Data"], y=df_agg_total["Cash_meta_diluida"],
                     mode="lines", name="Meta Diluída (Baseline)")
fig_cash.add_scatter(x=df_agg_sim["Data"], y=df_agg_sim["Cash_realizado"],
                     mode="lines", name="Simulação (Sem rotas canceladas)")

fig_cash.update_layout(hovermode="x unified")
st.plotly_chart(fig_cash, use_container_width=True)

# -------------------------
# Comparação de Cenários
# -------------------------
st.sidebar.subheader("Comparação de Cenários")

if "cenarios" not in st.session_state:
    st.session_state.cenarios = []

if st.sidebar.button("Salvar Cenário Atual"):
    # Armazena cenário atual (pode salvar métricas agregadas, por exemplo)
    scenario = {
        "rotas_canceladas": rotas_canceladas,
        "data_sim": df_agg_sim.copy()
    }
    st.session_state.cenarios.append(scenario)
    st.sidebar.success("Cenário salvo com sucesso!")

if st.sidebar.button("Visualizar Comparação de Cenários"):
    if st.session_state.cenarios:
        st.subheader("Comparação de Cenários Salvos")
        for i, cen in enumerate(st.session_state.cenarios):
            st.write(f"**Cenário {i+1}:** Rotas Canceladas: {', '.join(cen['rotas_canceladas']) if cen['rotas_canceladas'] else 'Nenhuma'}")
            # Exibe uma tabela resumo do cenário (ex: data, GMV realizado)
            st.dataframe(cen["data_sim"][["Data", "GMV_realizado", "Cash_realizado"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar os valores interativos.")


