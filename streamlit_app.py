import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Simulação de Cancelamento de Rotas", layout="wide")

@st.cache_data
def gerar_dados():
    """Gera dados de teste para 31 dias: 15 no passado, 16 no futuro."""
    num_dias_past = 15
    num_dias_future = 16
    total_dias = num_dias_past + num_dias_future
    start_date = datetime.now().date() - timedelta(days=num_dias_past)
    datas = pd.date_range(start=start_date, periods=total_dias, freq="D")

    num_rotas = 20
    rotas = [f"R{i+1}" for i in range(num_rotas)]
    regionais = [f"Regional {(i % 3) + 1}" for i in range(num_rotas)]

    dados = []
    for data in datas:
        for i, rota in enumerate(rotas):
            gmv_baseline = np.random.randint(500, 2000)
            cash_baseline = np.random.randint(-500, 1000)
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
    return df

def definir_valores(df, cutoff):
    """Define colunas GMV_valor/Cash_valor como realizado antes do cutoff e baseline depois."""
    df["GMV_valor"] = np.where(df["Data"] < cutoff, df["GMV_realizado"], df["GMV_baseline"])
    df["Cash_valor"] = np.where(df["Data"] < cutoff, df["Cash_realizado"], df["Cash_baseline"])
    return df

def calcular_meta_diluida(df_agg, meta_mensal_gmv, meta_mensal_cash):
    """Calcula a meta diluída para GMV e Cash com base nos pesos do baseline."""
    total_gmv = df_agg["GMV_baseline"].sum()
    if total_gmv == 0:
        df_agg["GMV_meta_diluida"] = 0
    else:
        df_agg["Peso_GMV"] = df_agg["GMV_baseline"] / total_gmv
        df_agg["GMV_meta_diluida"] = meta_mensal_gmv * df_agg["Peso_GMV"]

    total_cash = df_agg["Cash_baseline"].sum()
    if total_cash == 0:
        df_agg["Cash_meta_diluida"] = 0
    else:
        df_agg["Peso_Cash"] = df_agg["Cash_baseline"] / total_cash
        df_agg["Cash_meta_diluida"] = meta_mensal_cash * df_agg["Peso_Cash"]

    return df_agg

st.title("Simulação de Cancelamento de Rotas")
st.sidebar.header("Configurações")

usar_dados_exemplo = st.sidebar.checkbox("Usar dados de exemplo", value=True)
if usar_dados_exemplo:
    df = gerar_dados()
else:
    uploaded_file = st.sidebar.file_uploader("Carregue a planilha", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith("csv"):
                df = pd.read_csv(uploaded_file, parse_dates=["Data"])
            else:
                df = pd.read_excel(uploaded_file, parse_dates=["Data"])
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            st.stop()
    else:
        st.stop()

# Garante que "Data" é datetime
df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

# Definir colunas auxiliares (se quiser)
df["Dia_da_Semana"] = df["Data"].dt.day_name()
df["Dia_do_Mes"] = df["Data"].dt.day

cutoff = pd.Timestamp(datetime.now() + timedelta(hours=48))
df = definir_valores(df, cutoff)

st.sidebar.subheader("Seleção de Rotas para Cancelamento")
rotas_disponiveis = df["Rota"].unique().tolist()
rotas_canceladas = st.sidebar.multiselect("Rotas a cancelar:", rotas_disponiveis)

# Período de check
now_ts = pd.Timestamp.now()
inicio_check = now_ts + pd.Timedelta(hours=48)
fim_check = now_ts + pd.Timedelta(hours=72)

# Filtra para simulação
df_check = df[(df["Data"] >= inicio_check) & (df["Data"] <= fim_check)]
if rotas_canceladas:
    df_check = df_check[~df_check["Rota"].isin(rotas_canceladas)]

def agregar_indicadores(df_filtrado):
    """Agrega baseline, valor para GMV e Cash."""
    agg = df_filtrado.groupby("Data").agg({
        "GMV_baseline": "sum",
        "GMV_valor": "sum",
        "Cash_baseline": "sum",
        "Cash_valor": "sum"
    }).reset_index()
    return agg

df_agg_total = agregar_indicadores(df)
df_agg_sim = agregar_indicadores(df_check)

st.sidebar.subheader("Configurações de Meta")
meta_mensal_gmv = st.sidebar.number_input("Meta Mensal GMV", min_value=1000, value=600000, step=10000)
meta_mensal_cash = st.sidebar.number_input("Meta Mensal Cash", min_value=1000, value=300000, step=10000)

df_agg_total = calcular_meta_diluida(df_agg_total, meta_mensal_gmv, meta_mensal_cash)
df_agg_sim = calcular_meta_diluida(df_agg_sim, meta_mensal_gmv, meta_mensal_cash)

# Diferença
df_diff_gmv = pd.merge(
    df_agg_total[["Data", "GMV_valor"]],
    df_agg_sim[["Data", "GMV_valor"]].rename(columns={"GMV_valor": "GMV_sim"}),
    on="Data", how="left"
)
df_diff_gmv["GMV_diferenca"] = df_diff_gmv["GMV_sim"] - df_diff_gmv["GMV_valor"]

df_diff_cash = pd.merge(
    df_agg_total[["Data", "Cash_valor"]],
    df_agg_sim[["Data", "Cash_valor"]].rename(columns={"Cash_valor": "Cash_sim"}),
    on="Data", how="left"
)
df_diff_cash["Cash_diferenca"] = df_diff_cash["Cash_sim"] - df_diff_cash["Cash_valor"]

# ==============
# Gráfico GMV
# ==============
fig_gmv = go.Figure()
fig_gmv.update_xaxes(type="date")

# Faixa cinza
fig_gmv.add_shape(
    type="rect",
    xref="x", yref="paper",
    x0=inicio_check.isoformat(), x1=fim_check.isoformat(),
    y0=0, y1=1,
    fillcolor="gray",
    opacity=0.2,
    layer="below",
    line_width=0
)

# Linha vertical "hoje"
hoje_dt = pd.Timestamp(datetime.now().date())  # ou .now() se quiser a hora
fig_gmv.add_vline(
    x=hoje_dt,
    line_color="black",
    line_dash="dash"
)
# Para exibir texto no topo, adicionamos manualmente uma anotação
fig_gmv.add_annotation(
    x=hoje_dt,
    y=1.02,  # um pouco acima do gráfico
    xref="x",
    yref="paper",
    showarrow=False,
    text="Hoje",
    font=dict(color="black", size=12)
)

# Baseline
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_baseline"],
    mode="lines", name="Baseline Histórico",
    line=dict(color="gray", dash="dash")
))

# Meta
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_meta_diluida"],
    mode="lines", name="Meta Diluída",
    line=dict(color="green", dash="dot")
))

# Realizado/Previsto
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["GMV_valor"],
    mode="lines", name="Realizado/Previsto",
    line=dict(color="#00008B", width=3)
))

# Simulação
fig_gmv.add_trace(go.Scatter(
    x=df_agg_sim["Data"], y=df_agg_sim["GMV_valor"],
    mode="lines", name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

# Diferença
fig_gmv.add_trace(go.Scatter(
    x=df_diff_gmv["Data"], y=df_diff_gmv["GMV_diferenca"],
    mode="lines", name="Diferença (Sim - Real)",
    line=dict(color="#FF0000", width=2, dash="dot")
))

fig_gmv.update_layout(
    title="GMV - Baseline, Meta, Realizado/Previsto, Simulação e Diferença",
    xaxis_title="Data",
    yaxis_title="GMV",
    hovermode="x unified"
)

for trace in fig_gmv.data:
    trace.hovertemplate = f"{trace.name}: {{y:.2f}}<extra></extra>"

st.plotly_chart(fig_gmv, use_container_width=True)

# ==============
# Gráfico Cash
# ==============
fig_cash = go.Figure()
fig_cash.update_xaxes(type="date")

# Faixa cinza
fig_cash.add_shape(
    type="rect",
    xref="x", yref="paper",
    x0=inicio_check.isoformat(), x1=fim_check.isoformat(),
    y0=0, y1=1,
    fillcolor="gray",
    opacity=0.2,
    layer="below",
    line_width=0
)

# Linha vertical "hoje"
fig_cash.add_vline(
    x=hoje_dt,
    line_color="black",
    line_dash="dash"
)
fig_cash.add_annotation(
    x=hoje_dt,
    y=1.02,
    xref="x",
    yref="paper",
    showarrow=False,
    text="Hoje",
    font=dict(color="black", size=12)
)

fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_baseline"],
    mode="lines", name="Baseline Histórico",
    line=dict(color="gray", dash="dash")
))

fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_meta_diluida"],
    mode="lines", name="Meta Diluída",
    line=dict(color="green", dash="dot")
))

fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"], y=df_agg_total["Cash_valor"],
    mode="lines", name="Realizado/Previsto",
    line=dict(color="#00008B", width=3)
))

fig_cash.add_trace(go.Scatter(
    x=df_agg_sim["Data"], y=df_agg_sim["Cash_valor"],
    mode="lines", name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

fig_cash.add_trace(go.Scatter(
    x=df_diff_cash["Data"], y=df_diff_cash["Cash_diferenca"],
    mode="lines", name="Diferença (Sim - Real)",
    line=dict(color="#FF0000", width=2, dash="dot")
))

fig_cash.update_layout(
    title="Cash-Repasse - Baseline, Meta, Realizado/Previsto, Simulação e Diferença",
    xaxis_title="Data",
    yaxis_title="Cash-Repasse",
    hovermode="x unified"
)

for trace in fig_cash.data:
    trace.hovertemplate = f"{trace.name}: {{y:.2f}}<extra></extra>"

st.plotly_chart(fig_cash, use_container_width=True)

# =============================
# Comparação de Cenários
# =============================
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
            st.write(
                f"**Cenário {i+1}:** Rotas Canceladas: "
                f"{', '.join(cen['rotas_canceladas']) if cen['rotas_canceladas'] else 'Nenhuma'}"
            )
            st.dataframe(cen["data_sim"][["Data", "GMV_valor", "Cash_valor"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar valores com duas casas decimais.")







