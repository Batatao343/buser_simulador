import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configuração da página do Streamlit
st.set_page_config(page_title="Simulação de Cancelamento de Rotas", layout="wide")

# =============================================================================
# Função para gerar dados de teste
# =============================================================================
@st.cache_data
def gerar_dados():
    """
    Gera dados de teste para 31 dias: 15 dias no passado e 16 dias no futuro a partir de hoje,
    para 20 rotas.

    - GMV_baseline: valores aleatórios entre 500 e 2000 por rota/dia.
    - Cash_baseline: valores aleatórios entre -500 e 1000 (permitindo valores negativos).
    - GMV_realizado e Cash_realizado: gerados com base no baseline com algum ruído.
    """
    num_dias_past = 15   # dias no passado
    num_dias_future = 16 # dias no futuro
    total_dias = num_dias_past + num_dias_future  # total de 31 dias

    # Gera datas começando 15 dias atrás e indo até 16 dias depois de hoje
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

            # Para dados passados, geramos "realizado" com algum ruído
            gmv_realizado = gmv_baseline + np.random.randint(-100, 100)
            cash_realizado = cash_baseline + np.random.randint(-50, 50)

            dados.append({
                "Data": data,  # data como Timestamp do Pandas
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

# =============================================================================
# Função para definir os valores Realizado/Previsto
# =============================================================================
def definir_valores(df, cutoff):
    """
    Para datas anteriores ao cutoff, usa os valores realizados;
    para datas a partir do cutoff, usa o valor previsto (igual ao baseline).

    Cria as colunas:
      - GMV_valor: para a linha "Realizado/Previsto" (GMV).
      - Cash_valor: para a linha "Realizado/Previsto" (Cash).
    """
    df["GMV_valor"] = np.where(df["Data"] < cutoff, df["GMV_realizado"], df["GMV_baseline"])
    df["Cash_valor"] = np.where(df["Data"] < cutoff, df["Cash_realizado"], df["Cash_baseline"])
    return df

# =============================================================================
# Função para calcular a meta diluída para GMV e Cash-Repasse
# =============================================================================
def calcular_meta_diluida(df_agg, meta_mensal_gmv, meta_mensal_cash):
    """
    Calcula a meta diluída com base nos pesos dos valores históricos:
      - Peso_GMV = GMV_baseline / soma(GMV_baseline)
      - GMV_meta_diluida = meta_mensal_gmv * Peso_GMV
    Similarmente para Cash:
      - Peso_Cash = Cash_baseline / soma(Cash_baseline)
      - Cash_meta_diluida = meta_mensal_cash * Peso_Cash
    """
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

# =============================================================================
# Início da Aplicação Streamlit
# =============================================================================
st.title("Simulação de Cancelamento de Rotas")
st.sidebar.header("Configurações")

# Escolha: usar dados de exemplo ou carregar arquivo
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
            st.error(f"Erro ao carregar os dados: {str(e)}")
            st.stop()
    else:
        st.info("Carregue uma planilha para prosseguir.")
        st.stop()

# -----------------------------------------------------------------------------
# Define o cutoff (48 horas a partir de agora) e atualiza os valores de Realizado/Previsto
# -----------------------------------------------------------------------------
cutoff = pd.Timestamp(datetime.now() + timedelta(hours=48))
df = definir_valores(df, cutoff)

# -----------------------------------------------------------------------------
# Seleção de rotas para cancelamento
# -----------------------------------------------------------------------------
st.sidebar.subheader("Seleção de Rotas para Cancelamento")
rotas_disponiveis = df["Rota"].unique().tolist()
rotas_canceladas = st.sidebar.multiselect("Selecione as rotas a cancelar:", rotas_disponiveis)

# -----------------------------------------------------------------------------
# Período de check: de 48h (cutoff) a 72h a partir de agora
# -----------------------------------------------------------------------------
data_atual = pd.Timestamp(datetime.now())
inicio_check = data_atual + pd.Timedelta(hours=48)  # igual ao cutoff
fim_check = data_atual + pd.Timedelta(hours=72)

# -----------------------------------------------------------------------------
# Função para agregar indicadores por data
# -----------------------------------------------------------------------------
def agregar_indicadores(df_filtrado):
    """
    Agrupa os dados por Data, somando os valores de:
      - GMV_baseline, GMV_valor, Cash_baseline e Cash_valor.
    Adiciona colunas para Dia_da_Semana e Dia_do_Mes.
    """
    agg = df_filtrado.groupby("Data").agg({
        "GMV_baseline": "sum",
        "GMV_valor": "sum",
        "Cash_baseline": "sum",
        "Cash_valor": "sum"
    }).reset_index()
    agg["Dia_da_Semana"] = agg["Data"].dt.day_name()
    agg["Dia_do_Mes"] = agg["Data"].dt.day
    return agg

# -----------------------------------------------------------------------------
# Agregação dos dados
# -----------------------------------------------------------------------------
df_agg_total = agregar_indicadores(df)

df_check = df[(df["Data"] >= inicio_check) & (df["Data"] <= fim_check)]
if rotas_canceladas:
    df_check = df_check[~df_check["Rota"].isin(rotas_canceladas)]
df_agg_sim = agregar_indicadores(df_check)

# -----------------------------------------------------------------------------
# Configuração de Metas
# -----------------------------------------------------------------------------
st.sidebar.subheader("Configurações de Meta")
meta_mensal_gmv = st.sidebar.number_input("Meta Mensal GMV", min_value=1000, value=600000, step=10000)
meta_mensal_cash = st.sidebar.number_input("Meta Mensal Cash-Repasse", min_value=1000, value=300000, step=10000)

# Calcula as metas diluídas
df_agg_total = calcular_meta_diluida(df_agg_total, meta_mensal_gmv, meta_mensal_cash)
df_agg_sim = calcular_meta_diluida(df_agg_sim, meta_mensal_gmv, meta_mensal_cash)

# -----------------------------------------------------------------------------
# Cálculo da diferença entre Simulação e Realizado/Previsto
# -----------------------------------------------------------------------------
df_diff_gmv = pd.merge(
    df_agg_total[["Data", "GMV_valor"]],
    df_agg_sim[["Data", "GMV_valor"]].rename(columns={"GMV_valor": "GMV_sim"}),
    on="Data",
    how="left"
)
df_diff_gmv["GMV_diferenca"] = df_diff_gmv["GMV_sim"] - df_diff_gmv["GMV_valor"]

df_diff_cash = pd.merge(
    df_agg_total[["Data", "Cash_valor"]],
    df_agg_sim[["Data", "Cash_valor"]].rename(columns={"Cash_valor": "Cash_sim"}),
    on="Data",
    how="left"
)
df_diff_cash["Cash_diferenca"] = df_diff_cash["Cash_sim"] - df_diff_cash["Cash_valor"]

# -----------------------------------------------------------------------------
# Gráficos Interativos
# -----------------------------------------------------------------------------
st.subheader("Gráficos Interativos")

# Convertemos para string ISO para shapes (retângulos) e lines
hoje_iso = pd.Timestamp(datetime.now().date()).isoformat()
inicio_check_iso = inicio_check.isoformat()
fim_check_iso = fim_check.isoformat()

# ==================
# Gráfico de GMV
# ==================
fig_gmv = go.Figure()

# Eixo X como date
fig_gmv.update_xaxes(type="date")

# Faixa cinza entre 72h e 48h
fig_gmv.add_shape(
    type="rect",
    x0=inicio_check_iso, x1=fim_check_iso,
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray",
    opacity=0.2,
    layer="below",
    line_width=0
)

# Linha vertical no dia de hoje
fig_gmv.add_vline(
    x=hoje_iso,
    line=dict(color="black", dash="dash"),
    annotation_text="Hoje",
    annotation_position="top left"
)

# Linha Baseline Histórico
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"],  # datas em formato datetime
    y=df_agg_total["GMV_baseline"],
    mode="lines",
    name="Baseline Histórico",
    line=dict(color="gray", dash="dash"),
    opacity=0.6
))

# Linha Meta Diluída
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"],
    y=df_agg_total["GMV_meta_diluida"],
    mode="lines",
    name="Meta Diluída",
    line=dict(color="green", dash="dot"),
    opacity=0.8
))

# Linha Realizado/Previsto
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"],
    y=df_agg_total["GMV_valor"],
    mode="lines",
    name="Realizado/Previsto",
    line=dict(color="#00008B", width=3)
))

# Simulação (apenas período de check)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_sim["Data"],
    y=df_agg_sim["GMV_valor"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

# Diferença
fig_gmv.add_trace(go.Scatter(
    x=df_diff_gmv["Data"],
    y=df_diff_gmv["GMV_diferenca"],
    mode="lines",
    name="Diferença (Sim - Real)",
    line=dict(color="#FF0000", width=2, dash="dot")
))

fig_gmv.update_layout(
    title="GMV - Baseline, Meta, Realizado/Previsto, Simulação e Diferença",
    xaxis_title="Data",
    yaxis_title="GMV",
    hovermode="x unified"
)

for trace in fig_gmv.data:
    trace.hovertemplate = "%{y:.2f}<extra>" + trace.name + "</extra>"

st.plotly_chart(fig_gmv, use_container_width=True)

# ==================
# Gráfico de Cash
# ==================
fig_cash = go.Figure()

# Eixo X como date
fig_cash.update_xaxes(type="date")

# Faixa cinza
fig_cash.add_shape(
    type="rect",
    x0=inicio_check_iso, x1=fim_check_iso,
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray",
    opacity=0.2,
    layer="below",
    line_width=0
)

# Linha vertical hoje
fig_cash.add_vline(
    x=hoje_iso,
    line=dict(color="black", dash="dash"),
    annotation_text="Hoje",
    annotation_position="top left"
)

# Linha Baseline Histórico
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"],
    y=df_agg_total["Cash_baseline"],
    mode="lines",
    name="Baseline Histórico",
    line=dict(color="gray", dash="dash"),
    opacity=0.6
))

# Linha Meta Diluída
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"],
    y=df_agg_total["Cash_meta_diluida"],
    mode="lines",
    name="Meta Diluída",
    line=dict(color="green", dash="dot"),
    opacity=0.8
))

# Linha Realizado/Previsto
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"],
    y=df_agg_total["Cash_valor"],
    mode="lines",
    name="Realizado/Previsto",
    line=dict(color="#00008B", width=3)
))

# Simulação (apenas período de check)
fig_cash.add_trace(go.Scatter(
    x=df_agg_sim["Data"],
    y=df_agg_sim["Cash_valor"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

# Diferença
fig_cash.add_trace(go.Scatter(
    x=df_diff_cash["Data"],
    y=df_diff_cash["Cash_diferenca"],
    mode="lines",
    name="Diferença (Sim - Real)",
    line=dict(color="#FF0000", width=2, dash="dot")
))

fig_cash.update_layout(
    title="Cash-Repasse - Baseline, Meta, Realizado/Previsto, Simulação e Diferença",
    xaxis_title="Data",
    yaxis_title="Cash-Repasse",
    hovermode="x unified"
)

for trace in fig_cash.data:
    trace.hovertemplate = "%{y:.2f}<extra>" + trace.name + "</extra>"

st.plotly_chart(fig_cash, use_container_width=True)

# =============================================================================
# Comparação de Cenários
# =============================================================================
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
            st.dataframe(cen["data_sim"][["Data", "GMV_valor", "Cash_valor"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar valores com duas casas decimais.")






