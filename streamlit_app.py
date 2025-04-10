import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# =============================================================================
# Configurações iniciais da página Streamlit
# =============================================================================
st.set_page_config(page_title="Simulação de Cancelamento de Rotas (Acumulado)", layout="wide")

# =============================================================================
# 1. Função para gerar dados de teste
# =============================================================================
@st.cache_data
def gerar_dados():
    """
    Gera um DataFrame com 100 rotas, cada rota tendo 5 viagens distribuídas 
    aleatoriamente num período de 40 dias em torno de hoje (-20 dias, +20 dias).

    Colunas principais geradas:
      - Data (datetime)
      - Rota (ex: 'R1' ... 'R100')
      - GMV_baseline (entre 500 e 2000)
      - GMV_realizado (baseline + ruído)
      - Cash_baseline (entre -500 e 1000)
      - Cash_realizado (baseline + ruído)
    
    O baseline será usado para dias futuros, e o realizado para dias passados.
    """
    num_rotas = 100
    viagens_por_rota = 5
    start_date = datetime.now().date() - timedelta(days=20)
    end_date = datetime.now().date() + timedelta(days=20)
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    dados = []
    for rota in [f"R{i+1}" for i in range(num_rotas)]:
        # Escolhe 5 datas aleatórias (sem reposição)
        datas_rota = np.random.choice(date_range, size=viagens_por_rota, replace=False)
        for data in datas_rota:
            gmv_base = np.random.randint(500, 2000)
            cash_base = np.random.randint(-500, 1000)
            gmv_real = gmv_base + np.random.randint(-100, 100)
            cash_real = cash_base + np.random.randint(-50, 50)
            dados.append({
                "Data": data,
                "Rota": rota,
                "GMV_baseline": gmv_base,
                "GMV_realizado": gmv_real,
                "Cash_baseline": cash_base,
                "Cash_realizado": cash_real
            })
    df = pd.DataFrame(dados)
    df["Data"] = pd.to_datetime(df["Data"])
    return df

# =============================================================================
# 2. Definir colunas Realizado vs. Previsto
# =============================================================================
def definir_valores(df, cutoff):
    """
    Cria colunas GMV_valor e Cash_valor:
     - Se Data < cutoff: usa GMV_realizado / Cash_realizado
     - Se Data >= cutoff: usa GMV_baseline / Cash_baseline
    """
    df["GMV_valor"] = np.where(df["Data"] < cutoff, df["GMV_realizado"], df["GMV_baseline"])
    df["Cash_valor"] = np.where(df["Data"] < cutoff, df["Cash_realizado"], df["Cash_baseline"])
    return df

# =============================================================================
# 3. Converter dados em acumulado
# =============================================================================
def transformar_em_acumulado(df, col_gmv, col_cash):
    """
    Ordena por Data, faz cumsum de col_gmv e col_cash para gerar colunas GMV_acumulado e Cash_acumulado.
    """
    df_sorted = df.sort_values("Data").copy()
    df_sorted["GMV_acumulado"] = df_sorted[col_gmv].cumsum()
    df_sorted["Cash_acumulado"] = df_sorted[col_cash].cumsum()
    return df_sorted

# =============================================================================
# 4. Calcular Baseline Histórico e Meta Histórica Diluída
# =============================================================================
def calcular_baseline_meta_acumulada(df):
    """
    Para exibir o baseline histórico e a meta diluída de maneira acumulada, 
    vamos criar duas colunas:
      - GMV_baseline_acumulado: soma cumulativa do GMV_baseline
      - GMV_meta_acumulada: soma cumulativa da meta diluída para GMV (simples)
    
    Nota: a meta diluída, neste exemplo, é fictícia (ex: 600k GMV distribuídos 
    pela proporção do baseline). Para Cash também, se desejar.
    """
    df_sorted = df.sort_values("Data").copy()

    # 4.1 Soma total de baseline
    total_gmv_base = df_sorted["GMV_baseline"].sum()
    total_cash_base = df_sorted["Cash_baseline"].sum()

    # 4.2 Definimos metas fictícias (ou puxamos de um input)
    # Exemplos fixos (pode integrar com sidebar)
    meta_gmv = 600000
    meta_cash = 300000

    # 4.3 Calcula pesos e metas diluídas diárias
    # Para cada data, Peso = GMV_baseline / soma_total
    if total_gmv_base == 0:
        df_sorted["GMV_meta_diluida"] = 0
    else:
        df_sorted["Peso_GMV"] = df_sorted["GMV_baseline"] / total_gmv_base
        df_sorted["GMV_meta_diluida"] = meta_gmv * df_sorted["Peso_GMV"]

    if total_cash_base == 0:
        df_sorted["Cash_meta_diluida"] = 0
    else:
        df_sorted["Peso_Cash"] = df_sorted["Cash_baseline"] / total_cash_base
        df_sorted["Cash_meta_diluida"] = meta_cash * df_sorted["Peso_Cash"]

    # 4.4 Converte para acumulado
    df_sorted["GMV_baseline_acumulado"] = df_sorted["GMV_baseline"].cumsum()
    df_sorted["GMV_meta_acumulada"] = df_sorted["GMV_meta_diluida"].cumsum()

    df_sorted["Cash_baseline_acumulado"] = df_sorted["Cash_baseline"].cumsum()
    df_sorted["Cash_meta_acumulada"] = df_sorted["Cash_meta_diluida"].cumsum()

    return df_sorted

# =============================================================================
# 5. Início da aplicação
# =============================================================================
st.title("Simulação de Cancelamento de Rotas (Acumulado)")

st.sidebar.header("Configurações")

# 5.1 Carregar/gerar dados
usar_dados_exemplo = st.sidebar.checkbox("Usar dados de exemplo", value=True)
if usar_dados_exemplo:
    df = gerar_dados()
else:
    uploaded_file = st.sidebar.file_uploader("Carregue arquivo CSV/Excel", type=["csv","xlsx"])
    if uploaded_file:
        if uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file, parse_dates=["Data"])
        else:
            df = pd.read_excel(uploaded_file, parse_dates=["Data"])
    else:
        st.stop()

# Converte Data para datetime
df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

# 5.2 Definir "hoje" e período de check
hoje_dt = pd.Timestamp(datetime.now().date())
cutoff = hoje_dt

# 48h a partir de hoje -> inícios do período de check
check_start = hoje_dt + pd.Timedelta(hours=48)
# 72h a partir de hoje -> fim do período de check
check_end = hoje_dt + pd.Timedelta(hours=72)

# 5.3 Aplica Realizado vs. Previsto
df = definir_valores(df, cutoff)

# 5.4 Sidebar para cancelamento de rotas
rotas_disponiveis = sorted(df["Rota"].unique())
rotas_canceladas = st.sidebar.multiselect("Rotas a Cancelar", rotas_disponiveis)

# 5.5 Dividir DF em passado e futuro
df_past = df[df["Data"] < cutoff].copy()
df_future = df[df["Data"] >= cutoff].copy()

# Selecione apenas as viagens futuras que não foram canceladas
if rotas_canceladas:
    df_future_sim = df_future[~df_future["Rota"].isin(rotas_canceladas)].copy()
else:
    df_future_sim = df_future.copy()

# 5.6 Agrupa por Data -> soma GMV_valor e Cash_valor
def agrupar_data(df_in):
    agg = df_in.groupby("Data", as_index=False).agg({
        "GMV_valor": "sum",
        "Cash_valor": "sum",
        "GMV_baseline": "sum",
        "Cash_baseline": "sum"
    })
    return agg.sort_values("Data")

df_past_agg = agrupar_data(df_past)
df_future_agg = agrupar_data(df_future)
df_future_sim_agg = agrupar_data(df_future_sim)

# 5.7 Concatena passado + futuro base
df_base_agg = pd.concat([df_past_agg, df_future_agg], ignore_index=True).sort_values("Data")
df_sim_agg = pd.concat([df_past_agg, df_future_sim_agg], ignore_index=True).sort_values("Data")

# 5.8 Converte cada um em acumulado
df_base_acum = transformar_em_acumulado(df_base_agg, "GMV_valor", "Cash_valor")
df_sim_acum  = transformar_em_acumulado(df_sim_agg, "GMV_valor", "Cash_valor")

# 5.9 Calcula diferença de acumulados
df_diff = pd.merge(
    df_base_acum[["Data","GMV_acumulado","Cash_acumulado"]],
    df_sim_acum[["Data","GMV_acumulado","Cash_acumulado"]].rename(columns={
        "GMV_acumulado":"GMV_acumulado_sim",
        "Cash_acumulado":"Cash_acumulado_sim"
    }),
    on="Data", how="left"
)
df_diff["GMV_diferenca"] = df_diff["GMV_acumulado_sim"] - df_diff["GMV_acumulado"]
df_diff["Cash_diferenca"] = df_diff["Cash_acumulado_sim"] - df_diff["Cash_acumulado"]

# 5.10 Calcula baseline histórico e meta histórica diluída (acumulada)
# A ideia é pegar TUDO (df, sem separar passado/futuro), e ver baseline
df_baseline_meta = df.groupby("Data", as_index=False).agg({
    "GMV_baseline":"sum",
    "Cash_baseline":"sum"
}).sort_values("Data")
df_baseline_meta = calcular_baseline_meta_acumulada(df_baseline_meta)

# =============================================================================
# 6. Criação dos gráficos
# =============================================================================
st.subheader("Gráfico Interativo - GMV Acumulado")

fig_gmv = go.Figure()
fig_gmv.update_xaxes(type="date")

# 6.1 Faixa cinza (check_start até check_end)
fig_gmv.add_shape(
    type="rect",
    x0=check_start.isoformat(),
    x1=check_end.isoformat(),
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray", opacity=0.2,
    layer="below",
    line_width=0
)
fig_gmv.add_annotation(
    x=(check_start + (check_end - check_start)/2).isoformat(),
    y=1.07,
    xref="x", yref="paper",
    showarrow=False,
    text="Período do check de cancelamento",
    font=dict(color="gray", size=12)
)

# 6.2 Linha vertical em "Hoje"
fig_gmv.add_vline(
    x=hoje_dt,
    line=dict(color="black", dash="dash")
)
fig_gmv.add_annotation(
    x=hoje_dt,
    y=1.03,
    xref="x", yref="paper",
    showarrow=False,
    text="Hoje",
    font=dict(color="black", size=12)
)

# 6.3 Pegar passado e futuro (base) + sim para plotar
df_base_past = df_base_acum[df_base_acum["Data"]< hoje_dt]
df_base_future = df_base_acum[df_base_acum["Data"]>= hoje_dt]
df_sim_future = df_sim_acum[df_sim_acum["Data"]>= hoje_dt]

# 6.4 Plot baseline histórico acumulado
fig_gmv.add_trace(go.Scatter(
    x=df_baseline_meta["Data"],
    y=df_baseline_meta["GMV_baseline_acumulado"],
    mode="lines",
    name="Baseline Histórico (Acumul.)",
    line=dict(color="gray", dash="dash"),
    opacity=0.7
))

# 6.5 Plot meta diluída acumulada
fig_gmv.add_trace(go.Scatter(
    x=df_baseline_meta["Data"],
    y=df_baseline_meta["GMV_meta_acumulada"],
    mode="lines",
    name="Meta Hist. Diluída (Acumul.)",
    line=dict(color="green", dash="dot"),
    opacity=0.7
))

# 6.6 Linha Realizado/Previsto
# Passado (linha sólida)
fig_gmv.add_trace(go.Scatter(
    x=df_base_past["Data"],
    y=df_base_past["GMV_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Passado)",
    line=dict(color="#00008B", width=3, dash="solid")
))
# Futuro (linha tracejada)
fig_gmv.add_trace(go.Scatter(
    x=df_base_future["Data"],
    y=df_base_future["GMV_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Futuro)",
    line=dict(color="#00008B", width=3, dash="dash")
))

# 6.7 Linha Simulação (rotas canceladas)
fig_gmv.add_trace(go.Scatter(
    x=df_sim_future["Data"],
    y=df_sim_future["GMV_acumulado"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="red", width=3, dash="solid")
))

# 6.8 Linha de Diferença
df_diff_future = df_diff[df_diff["Data"]>= hoje_dt].copy() # só para datas >= hoje
fig_gmv.add_trace(go.Scatter(
    x=df_diff_future["Data"],
    y=df_diff_future["GMV_diferenca"],
    mode="lines",
    name="Diferença Acumulada",
    line=dict(color="red", width=2, dash="dot")
))

# Ajustes finais
fig_gmv.update_layout(
    title="GMV Acumulado - Base vs. Simulação",
    xaxis_title="Data",
    yaxis_title="GMV Acumulado",
    hovermode="x unified"
)
for trace in fig_gmv.data:
    trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"

st.plotly_chart(fig_gmv, use_container_width=True)

# ============================================================================
# Gráfico - Cash Acumulado
# ============================================================================
st.subheader("Gráfico Interativo - Cash Acumulado")

fig_cash = go.Figure()
fig_cash.update_xaxes(type="date")

# Faixa cinza para o check
fig_cash.add_shape(
    type="rect",
    x0=check_start.isoformat(),
    x1=check_end.isoformat(),
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray", opacity=0.2,
    layer="below",
    line_width=0
)
fig_cash.add_annotation(
    x=(check_start + (check_end - check_start)/2).isoformat(),
    y=1.07,
    xref="x", yref="paper",
    showarrow=False,
    text="Período do check de cancelamento",
    font=dict(color="gray", size=12)
)

fig_cash.add_vline(
    x=hoje_dt,
    line=dict(color="black", dash="dash")
)
fig_cash.add_annotation(
    x=hoje_dt,
    y=1.03,
    xref="x", yref="paper",
    showarrow=False,
    text="Hoje",
    font=dict(color="black", size=12)
)

df_base_cash_past = df_base_acum[df_base_acum["Data"]< hoje_dt]
df_base_cash_future = df_base_acum[df_base_acum["Data"]>= hoje_dt]
df_sim_cash_future = df_sim_acum[df_sim_acum["Data"]>= hoje_dt]
df_diff_cash_future = df_diff[df_diff["Data"]>= hoje_dt].copy()

# Baseline histórico (acumulado)
fig_cash.add_trace(go.Scatter(
    x=df_baseline_meta["Data"],
    y=df_baseline_meta["Cash_baseline_acumulado"],
    mode="lines",
    name="Baseline Histórico (Acumul.)",
    line=dict(color="gray", dash="dash"),
    opacity=0.7
))

# Meta diluída (acumulada)
fig_cash.add_trace(go.Scatter(
    x=df_baseline_meta["Data"],
    y=df_baseline_meta["Cash_meta_acumulada"],
    mode="lines",
    name="Meta Hist. Diluída (Acumul.)",
    line=dict(color="green", dash="dot"),
    opacity=0.7
))

# Realizado/Previsto - passado e futuro
fig_cash.add_trace(go.Scatter(
    x=df_base_cash_past["Data"],
    y=df_base_cash_past["Cash_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Passado)",
    line=dict(color="#00008B", width=3, dash="solid")
))
fig_cash.add_trace(go.Scatter(
    x=df_base_cash_future["Data"],
    y=df_base_cash_future["Cash_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Futuro)",
    line=dict(color="#00008B", width=3, dash="dash")
))

# Simulação (rotas canceladas)
fig_cash.add_trace(go.Scatter(
    x=df_sim_cash_future["Data"],
    y=df_sim_cash_future["Cash_acumulado"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="red", width=3, dash="solid")
))

# Diferença
fig_cash.add_trace(go.Scatter(
    x=df_diff_cash_future["Data"],
    y=df_diff_cash_future["Cash_diferenca"],
    mode="lines",
    name="Diferença Acumulada",
    line=dict(color="red", width=2, dash="dot")
))

fig_cash.update_layout(
    title="Cash Acumulado - Base vs. Simulação",
    xaxis_title="Data",
    yaxis_title="Cash Acumulado",
    hovermode="x unified"
)
for trace in fig_cash.data:
    trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"

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
        "df_sim": df_sim_acum.copy(),
        "df_diff": df_diff.copy()
    }
    st.session_state.cenarios.append(scenario)
    st.sidebar.success("Cenário salvo com sucesso!")

if st.sidebar.button("Visualizar Comparação de Cenários"):
    if st.session_state.cenarios:
        st.subheader("Comparação de Cenários Salvos")
        for i, cen in enumerate(st.session_state.cenarios):
            st.write(
                f"**Cenário {i+1}:** Rotas Canceladas: " +
                (", ".join(cen['rotas_canceladas']) if cen["rotas_canceladas"] else "Nenhuma")
            )
            st.write("Simulação Acumulada:")
            st.dataframe(cen["df_sim"][["Data", "GMV_acumulado", "Cash_acumulado"]])
            st.write("Diferença Acumulada:")
            st.dataframe(cen["df_diff"][["Data", "GMV_diferenca", "Cash_diferenca"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar valores com duas casas decimais.")

