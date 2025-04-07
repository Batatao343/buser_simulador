import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
    
    dados = []
    for data in datas:
        for i, rota in enumerate(rotas):
            # Valores fictícios
            gmv_baseline = np.random.randint(1000, 2000)
            cash_baseline = np.random.randint(500, 1500)
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
    df["Dia_da_Semana"] = df["Data"].dt.day_name()
    df["Dia_do_Mes"] = df["Data"].dt.day
    return df

# -------------------------
# Função para calcular a meta diluída para GMV e Cash-Repasse
# -------------------------
def calcular_meta_diluida(df_agg, meta_mensal_gmv, meta_mensal_cash):
    # Cálculo para GMV:
    total_gmv = df_agg["GMV_baseline"].sum()
    df_agg["Peso_GMV"] = df_agg["GMV_baseline"] / total_gmv
    df_agg["GMV_meta_diluida"] = meta_mensal_gmv * df_agg["Peso_GMV"]

    # Cálculo para Cash-Repasse:
    total_cash = df_agg["Cash_baseline"].sum()
    df_agg["Peso_Cash"] = df_agg["Cash_baseline"] / total_cash
    df_agg["Cash_meta_diluida"] = meta_mensal_cash * df_agg["Peso_Cash"]

    return df_agg

# -------------------------
# Carregando os dados (usando dados de exemplo ou upload)
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

st.subheader("Dados Carregados")
st.dataframe(df.head(10))

# -------------------------
# Seleção de Rotas para Cancelamento
# -------------------------
st.sidebar.subheader("Seleção de Rotas para Cancelamento")
rotas_disponiveis = df["Rota"].unique().tolist()
rotas_canceladas = st.sidebar.multiselect("Selecione as rotas a cancelar:", rotas_disponiveis)

# -------------------------
# Filtrar dados para simulação somente no período de check (72 a 48h antes da saída)
# -------------------------
data_atual = datetime.now()
inicio_check = data_atual + timedelta(hours=48)
fim_check = data_atual + timedelta(hours=72)

# Agregação dos indicadores por data
def agregar_indicadores(df_filtrado):
    agg = df_filtrado.groupby("Data").agg({
        "GMV_baseline": "sum",
        "GMV_realizado": "sum",
        "Cash_baseline": "sum",
        "Cash_realizado": "sum"
    }).reset_index()
    agg["Dia_da_Semana"] = agg["Data"].dt.day_name()
    agg["Dia_do_Mes"] = agg["Data"].dt.day
    return agg

# Dados para baseline: todos os dias
df_agg_total = agregar_indicadores(df)

# Dados para simulação: somente dias no período de check e removendo rotas canceladas
df_check = df[(df["Data"] >= inicio_check) & (df["Data"] <= fim_check)]
if rotas_canceladas:
    df_check = df_check[~df_check["Rota"].isin(rotas_canceladas)]
df_agg_sim = agregar_indicadores(df_check)

# -------------------------
# Configuração de Meta e cálculo da Meta Diluída
# -------------------------
st.sidebar.subheader("Configurações de Meta")
meta_mensal_gmv = st.sidebar.number_input("Meta Mensal GMV", min_value=1000, value=30000, step=1000)
meta_mensal_cash = st.sidebar.number_input("Meta Mensal Cash-Repasse", min_value=1000, value=20000, step=1000)

df_agg_total = calcular_meta_diluida(df_agg_total, meta_mensal_gmv, meta_mensal_cash)
df_agg_sim = calcular_meta_diluida(df_agg_sim, meta_mensal_gmv, meta_mensal_cash)

# -------------------------
# Gráficos Interativos com Plotly
# -------------------------
st.subheader("Gráficos Interativos")

# Gráfico de GMV
fig_gmv = go.Figure()

# Linha Baseline Histórico (cinza, tracejado)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_baseline"],
    mode="lines",
    name="Baseline Histórico",
    line=dict(color="gray", dash="dash"),
    opacity=0.6
))

# Linha Meta Diluída (cinza, tracejado)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_meta_diluida"],
    mode="lines",
    name="Meta Diluída",
    line=dict(color="gray", dash="dashdot"),
    opacity=0.8
))

# Linha Realizado (azul escuro)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_realizado"],
    mode="lines",
    name="Realizado",
    line=dict(color="#00008B", width=3)
))

# Linha Simulação (vermelho vibrante), somente para o período de check
fig_gmv.add_trace(go.Scatter(
    x=df_agg_sim["Data"], y=df_agg_sim["GMV_realizado"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

fig_gmv.update_layout(
    title="GMV - Baseline, Meta, Realizado e Simulação",
    xaxis_title="Data",
    yaxis_title="GMV",
    hovermode="x unified"
)
st.plotly_chart(fig_gmv, use_container_width=True)

# Gráfico de Cash-Repasse
fig_cash = go.Figure()

# Linha Baseline Histórico (cinza, tracejado)
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_baseline"],
    mode="lines",
    name="Baseline Histórico",
    line=dict(color="gray", dash="dash"),
    opacity=0.6
))

# Linha Meta Diluída (cinza, tracejado)
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_meta_diluida"],
    mode="lines",
    name="Meta Diluída",
    line=dict(color="gray", dash="dashdot"),
    opacity=0.8
))

# Linha Realizado (azul escuro)
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_realizado"],
    mode="lines",
    name="Realizado",
    line=dict(color="#00008B", width=3)
))

# Linha Simulação (vermelho vibrante)
fig_cash.add_trace(go.Scatter(
    x=df_agg_sim["Data"], y=df_agg_sim["Cash_realizado"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

fig_cash.update_layout(
    title="Cash-Repasse - Baseline, Meta, Realizado e Simulação",
    xaxis_title="Data",
    yaxis_title="Cash-Repasse",
    hovermode="x unified"
)
st.plotly_chart(fig_cash, use_container_width=True)

# -------------------------
# Comparação de Cenários
# -------------------------
st.sidebar.subheader("Comparação de Cenários")

if "cenarios" not in st.session_state:
    st.session_state.cenarios = []

if st.sidebar.button("Salvar Cenário Atual"):
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
            st.dataframe(cen["data_sim"][["Data", "GMV_realizado", "Cash_realizado"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar os valores interativos.")


