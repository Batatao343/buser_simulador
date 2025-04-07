import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Simulação de Cancelamento de Rotas", layout="wide")

# -------------------------
# Função para gerar dados de teste
# -------------------------
@st.cache_data
def gerar_dados():
    """
    Gera dados para 31 dias (janeiro), com 20 rotas.
    GMV_baseline varia de 900 a 1200 por rota/dia,
    Cash_baseline varia de -100 a 500, podendo ficar negativo.
    Assim, somando 20 rotas, o total diário fica numa faixa próxima
    para que a meta mensal (inserida pelo usuário) fique coerente.
    """
    datas = pd.date_range(start="2023-01-01", end="2023-01-31", freq="D")
    num_rotas = 20
    rotas = [f"R{i+1}" for i in range(num_rotas)]
    regionais = [f"Regional {(i % 3) + 1}" for i in range(num_rotas)]  # Exemplo de regionais

    dados = []
    for data in datas:
        for i, rota in enumerate(rotas):
            gmv_baseline = np.random.randint(200, 1200)  # Faixa de 900 a 1200
            # Alguns valores de Cash podem ser negativos
            cash_baseline = np.random.randint(-300, 1000)

            # Realizado com base no baseline + algum ruído
            gmv_realizado = gmv_baseline + np.random.randint(-100, 100)
            cash_realizado = cash_baseline + np.random.randint(-50, 50)

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
    # Cálculo de pesos para GMV:
    total_gmv = df_agg["GMV_baseline"].sum()
    if total_gmv == 0:
        df_agg["GMV_meta_diluida"] = 0
    else:
        df_agg["Peso_GMV"] = df_agg["GMV_baseline"] / total_gmv
        df_agg["GMV_meta_diluida"] = meta_mensal_gmv * df_agg["Peso_GMV"]

    # Cálculo de pesos para Cash:
    total_cash = df_agg["Cash_baseline"].sum()
    if total_cash == 0:
        df_agg["Cash_meta_diluida"] = 0
    else:
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

# -------------------------
# Seleção de Rotas para Cancelamento
# -------------------------
st.sidebar.subheader("Seleção de Rotas para Cancelamento")
rotas_disponiveis = df["Rota"].unique().tolist()
rotas_canceladas = st.sidebar.multiselect("Selecione as rotas a cancelar:", rotas_disponiveis)

# -------------------------
# Filtro para o período de check (72 a 48h antes da saída)
# -------------------------
data_atual = datetime.now()
inicio_check = data_atual + timedelta(hours=48)
fim_check = data_atual + timedelta(hours=72)

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

# Dados para baseline (todos os dias, sem cancelamento)
df_agg_total = agregar_indicadores(df)

# Dados de simulação: somente para o período de check, excluindo rotas canceladas
df_check = df[(df["Data"] >= inicio_check) & (df["Data"] <= fim_check)]
if rotas_canceladas:
    df_check = df_check[~df_check["Rota"].isin(rotas_canceladas)]
df_agg_sim = agregar_indicadores(df_check)

# -------------------------
# Configuração de Metas
# -------------------------
st.sidebar.subheader("Configurações de Meta")
meta_mensal_gmv = st.sidebar.number_input("Meta Mensal GMV", min_value=1000, value=600000, step=10000)
meta_mensal_cash = st.sidebar.number_input("Meta Mensal Cash-Repasse", min_value=1000, value=300000, step=10000)

df_agg_total = calcular_meta_diluida(df_agg_total, meta_mensal_gmv, meta_mensal_cash)
df_agg_sim = calcular_meta_diluida(df_agg_sim, meta_mensal_gmv, meta_mensal_cash)

# -------------------------
# Gráficos Interativos
# -------------------------
st.subheader("Gráficos Interativos")

# Gráfico de GMV
fig_gmv = go.Figure()

# Baseline Histórico (cinza, tracejado)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_baseline"],
    mode="lines",
    name="Baseline Histórico",
    line=dict(color="gray", dash="dash"),
    opacity=0.6
))

# Meta Diluída (verde)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_meta_diluida"],
    mode="lines",
    name="Meta Diluída",
    line=dict(color="green", dash="dot"),
    opacity=0.8
))

# Realizado (azul escuro)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_realizado"],
    mode="lines",
    name="Realizado",
    line=dict(color="#00008B", width=3)
))

# Simulação (vermelho), apenas para o período de check
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

# Baseline Histórico (cinza, tracejado)
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_baseline"],
    mode="lines",
    name="Baseline Histórico",
    line=dict(color="gray", dash="dash"),
    opacity=0.6
))

# Meta Diluída (verde)
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_meta_diluida"],
    mode="lines",
    name="Meta Diluída",
    line=dict(color="green", dash="dot"),
    opacity=0.8
))

# Realizado (azul escuro)
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_realizado"],
    mode="lines",
    name="Realizado",
    line=dict(color="#00008B", width=3)
))

# Simulação (vermelho), apenas para o período de check
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



