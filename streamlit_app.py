import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# Configuração inicial da página
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Simulação de Cancelamento de Rotas", layout="wide")

# =============================================================================
# Função para gerar dados de teste para 100 rotas com viagens em datas não diárias
# =============================================================================
@st.cache_data
def gerar_dados():
    """
    Gera um DataFrame de viagens com 100 rotas. Para cada rota, simula 5 viagens
    distribuídas aleatoriamente num período de 40 dias (do hoje - 20 dias até hoje + 20 dias).

    - GMV_baseline é gerado aleatoriamente entre 500 e 2000.
    - Cash_baseline é gerado aleatoriamente entre -500 e 1000.
    - GMV_realizado e Cash_realizado são gerados com ruído a partir do baseline.
    
    Retorna um DataFrame com as colunas: Data, Rota, GMV_baseline, GMV_realizado,
    Cash_baseline, Cash_realizado.
    """
    num_rotas = 100
    viagens_por_rota = 5
    # Período de 40 dias: de hoje -20 dias até hoje +20 dias
    start_date = datetime.now().date() - timedelta(days=20)
    end_date = datetime.now().date() + timedelta(days=20)
    total_dias = (end_date - start_date).days + 1

    # Cria uma lista com todas as possíveis datas
    todas_datas = pd.date_range(start=start_date, periods=total_dias, freq="D")
    
    dados = []
    for rota in [f"R{i+1}" for i in range(num_rotas)]:
        # Escolhe aleatoriamente 5 datas (sem reposição) para os trips desta rota
        datas_rota = np.random.choice(todas_datas, size=viagens_por_rota, replace=False)
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
    # Garantir que a coluna Data esteja no formato datetime do pandas
    df["Data"] = pd.to_datetime(df["Data"])
    return df

# =============================================================================
# Função para definir os valores Realizado/Previsto
# =============================================================================
def definir_valores(df, cutoff):
    """
    Cria as colunas:
      - GMV_valor: usa GMV_realizado se Data < cutoff, senão GMV_baseline.
      - Cash_valor: usa Cash_realizado se Data < cutoff, senão Cash_baseline.
      
    O cutoff aqui representa o "hoje". Assim, viagens com Data > hoje serão consideradas previstas.
    """
    df["GMV_valor"] = np.where(df["Data"] < cutoff, df["GMV_realizado"], df["GMV_baseline"])
    df["Cash_valor"] = np.where(df["Data"] < cutoff, df["Cash_realizado"], df["Cash_baseline"])
    return df

# =============================================================================
# Função para transformar dados diários em valores acumulados
# =============================================================================
def transformar_em_acumulado(df, col_gmv, col_cash):
    """
    Dado um DataFrame com a coluna 'Data' e os valores diários especificados por col_gmv e col_cash,
    ordena por Data e calcula a soma acumulada (cumsum).

    Retorna o DataFrame com as novas colunas 'GMV_acumulado' e 'Cash_acumulado'.
    """
    df_sorted = df.sort_values("Data").copy()
    df_sorted["GMV_acumulado"] = df_sorted[col_gmv].cumsum()
    df_sorted["Cash_acumulado"] = df_sorted[col_cash].cumsum()
    return df_sorted

# =============================================================================
# Função para calcular a meta diluída (diária) e depois transformá-la em acumulado
# =============================================================================
def calcular_meta_diluida(df_agg, meta_gmv, meta_cash):
    """
    Calcula a meta diluída diária com base nos pesos do baseline diário:
      Peso_GMV = GMV_baseline / soma(GMV_baseline)
      GMV_meta_diluida = meta_gmv * Peso_GMV
    (E similarmente para Cash)

    Em seguida, transforma essa meta diária em valores acumulados.
    """
    total_gmv = df_agg["GMV_baseline"].sum()
    if total_gmv == 0:
        df_agg["GMV_meta_diluida"] = 0
    else:
        df_agg["Peso_GMV"] = df_agg["GMV_baseline"] / total_gmv
        df_agg["GMV_meta_diluida"] = meta_gmv * df_agg["Peso_GMV"]

    total_cash = df_agg["Cash_baseline"].sum()
    if total_cash == 0:
        df_agg["Cash_meta_diluida"] = 0
    else:
        df_agg["Peso_Cash"] = df_agg["Cash_baseline"] / total_cash
        df_agg["Cash_meta_diluida"] = meta_cash * df_agg["Peso_Cash"]

    # Calcula os acumulados
    df_agg = df_agg.sort_values("Data").copy()
    df_agg["GMV_meta_acumulado"] = df_agg["GMV_meta_diluida"].cumsum()
    df_agg["Cash_meta_acumulado"] = df_agg["Cash_meta_diluida"].cumsum()
    return df_agg

# =============================================================================
# Início da Aplicação Streamlit
# =============================================================================
st.title("Simulação de Cancelamento de Rotas (Acumulado)")

st.sidebar.header("Configurações")

# 1. Carregamento de dados (usamos dados de exemplo aqui)
usar_dados_exemplo = st.sidebar.checkbox("Usar dados de exemplo", value=True)
if usar_dados_exemplo:
    df = gerar_dados()
else:
    uploaded_file = st.sidebar.file_uploader("Carregue a planilha", type=["csv", "xlsx"])
    if uploaded_file:
        if uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file, parse_dates=["Data"])
        else:
            df = pd.read_excel(uploaded_file, parse_dates=["Data"])
    else:
        st.stop()

# Garante que a coluna Data esteja como datetime
df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

# 2. Definir cutoff: vamos usar o dia de hoje para separar realizado de previsto.
hoje_dt = pd.Timestamp(datetime.now().date())
cutoff = hoje_dt  # cutoff é o início do dia de hoje
df = definir_valores(df, cutoff)

# 3. Seleção de rotas para cancelamento (aplica-se apenas aos valores futuros)
rotas_disponiveis = sorted(df["Rota"].unique().tolist())
rotas_canceladas = st.sidebar.multiselect("Selecione as rotas a cancelar", rotas_disponiveis)

# 4. Separar os dados em passado e futuro
df_past = df[df["Data"] <= cutoff].copy()   # viagens que já ocorreram
df_future = df[df["Data"] > cutoff].copy()    # viagens futuras

# Para simulação: em df_future, remover as rotas canceladas
if rotas_canceladas:
    df_future_sim = df_future[~df_future["Rota"].isin(rotas_canceladas)].copy()
else:
    df_future_sim = df_future.copy()

# 5. Agregar (somar) os valores por Data para passado e futuro
def agregar_por_data(df_input):
    agg = df_input.groupby("Data", as_index=False).agg({
        "GMV_valor": "sum",
        "Cash_valor": "sum",
        "GMV_baseline": "sum",
        "Cash_baseline": "sum",
        "GMV_meta_diluida": "sum"   # será calculado depois
    })
    return agg

# Agregação para valores diários (não acumulados) 
# Para o baseline (todos os dados), usamos df completo
df_agg_total = df.groupby("Data", as_index=False).agg({
    "GMV_valor": "sum",
    "Cash_valor": "sum",
    "GMV_baseline": "sum",
    "Cash_baseline": "sum"
}).sort_values("Data")

# Agregação apenas para as viagens futuras simuladas
df_agg_future_sim = df_future_sim.groupby("Data", as_index=False).agg({
    "GMV_valor": "sum",
    "Cash_valor": "sum"
}).sort_values("Data")

# Calcula os acumulados para o cenário base (realizado/previsto)
df_agg_total = transformar_em_acumulado(df_agg_total, "GMV_valor", "Cash_valor")

# Para a simulação, precisamos recalcular os acumulados apenas para viagens futuras.
# Obtemos o acumulado para o passado (valor fixo) e para o futuro simulada:
if not df_agg_total[df_agg_total["Data"] <= cutoff].empty:
    base_GMV = df_agg_total[df_agg_total["Data"] <= cutoff]["GMV_acumulado"].max()
    base_Cash = df_agg_total[df_agg_total["Data"] <= cutoff]["Cash_acumulado"].max()
else:
    base_GMV, base_Cash = 0, 0

# Acumula os valores futuros (para o cenário base)
df_agg_future = df[df["Data"] > cutoff].groupby("Data", as_index=False).agg({
    "GMV_valor": "sum",
    "Cash_valor": "sum"
}).sort_values("Data")
df_agg_future = transformar_em_acumulado(df_agg_future, "GMV_valor", "Cash_valor")
df_agg_future["GMV_acumulado_full"] = base_GMV + df_agg_future["GMV_acumulado"]
df_agg_future["Cash_acumulado_full"] = base_Cash + df_agg_future["Cash_acumulado"]

# Para o cenário simulado (com cancelamentos)
df_agg_future_sim = df_future_sim.groupby("Data", as_index=False).agg({
    "GMV_valor": "sum",
    "Cash_valor": "sum"
}).sort_values("Data")
df_agg_future_sim = transformar_em_acumulado(df_agg_future_sim, "GMV_valor", "Cash_valor")
df_agg_future_sim["GMV_acumulado_full"] = base_GMV + df_agg_future_sim["GMV_acumulado"]
df_agg_future_sim["Cash_acumulado_full"] = base_Cash + df_agg_future_sim["Cash_acumulado"]

# Combina as partes do passado e do futuro para o cenário base e simulado
df_total_acum = pd.concat([
    df_agg_total[df_agg_total["Data"] <= cutoff],
    df_agg_future
]).sort_values("Data")

df_sim_acum = pd.concat([
    df_agg_total[df_agg_total["Data"] <= cutoff],   # para passado, simulação = base
    df_agg_future_sim
]).sort_values("Data")

# Calcula a linha de diferença para o acumulado (apenas para as datas futuras)
df_diff_acum = pd.merge(
    df_total_acum[df_total_acum["Data"] > cutoff][["Data", "GMV_acumulado", "Cash_acumulado"]],
    df_sim_acum[df_sim_acum["Data"] > cutoff][["Data", "GMV_acumulado", "Cash_acumulado"]].rename(
        columns={"GMV_acumulado": "GMV_acumulado_sim", "Cash_acumulado": "Cash_acumulado_sim"}
    ),
    on="Data",
    how="left"
)
df_diff_acum["GMV_diferenca"] = df_diff_acum["GMV_acumulado_sim"] - df_diff_acum["GMV_acumulado"]
df_diff_acum["Cash_diferenca"] = df_diff_acum["Cash_acumulado_sim"] - df_diff_acum["Cash_acumulado"]

# =============================================================================
# Criação dos Gráficos
# =============================================================================

# --- Gráfico de GMV Acumulado ---
st.subheader("Gráfico Interativo - GMV Acumulado")

fig_gmv = go.Figure()
fig_gmv.update_xaxes(type="date")

# Faixa cinza: Período do check de cancelamento (de hoje até hoje+X dias)
# Neste exemplo, usaremos o intervalo futuro (você pode ajustar se necessário)
# Aqui usamos o período futuro simulado (já que apenas viagens futuras podem ser canceladas)
fig_gmv.add_shape(
    type="rect",
    x0=hoje_dt.isoformat(), x1=df_total_acum["Data"].max().isoformat(),
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray", opacity=0.2, layer="below", line_width=0
)
fig_gmv.add_annotation(
    x= (hoje_dt + (df_total_acum["Data"].max() - hoje_dt)/2).isoformat(),
    y=1.07,
    xref="x", yref="paper",
    showarrow=False,
    text="Período do check de cancelamento",
    font=dict(color="gray", size=12)
)

# Linha vertical para o dia de hoje (sendo exibida)
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

# Dividindo os dados acumulados em passado e futuro
df_total_past = df_total_acum[df_total_acum["Data"] <= hoje_dt]
df_total_future = df_total_acum[df_total_acum["Data"] > hoje_dt]
df_sim_future = df_sim_acum[df_sim_acum["Data"] > hoje_dt]

# Linha de Realizado/Previsto (acumulado) - passado (solid) + futuro (dashed)
fig_gmv.add_trace(go.Scatter(
    x=df_total_past["Data"],
    y=df_total_past["GMV_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Passado)",
    line=dict(color="#00008B", width=3, dash="solid")
))
fig_gmv.add_trace(go.Scatter(
    x=df_total_future["Data"],
    y=df_total_future["GMV_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Previsto)",
    line=dict(color="#00008B", width=3, dash="dash")
))

# Linha de Simulação (acumulado) - apenas para futuros (solid)
fig_gmv.add_trace(go.Scatter(
    x=df_sim_future["Data"],
    y=df_sim_future["GMV_acumulado"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

# Linha de Diferença (acumulada) - entre simulação e base, para futuros
fig_gmv.add_trace(go.Scatter(
    x=df_diff_acum["Data"],
    y=df_diff_acum["GMV_diferenca"],
    mode="lines",
    name="Diferença Acumulada",
    line=dict(color="#FF0000", width=2, dash="dot")
))

fig_gmv.update_layout(
    title="GMV Acumulado - Baseline vs. Simulação",
    xaxis_title="Data",
    yaxis_title="GMV Acumulado",
    hovermode="x unified"
)
# Ajusta hover para duas casas decimais
for trace in fig_gmv.data:
    trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"

st.plotly_chart(fig_gmv, use_container_width=True)

# --- Gráfico de Cash Acumulado ---
st.subheader("Gráfico Interativo - Cash Acumulado")

fig_cash = go.Figure()
fig_cash.update_xaxes(type="date")

fig_cash.add_shape(
    type="rect",
    x0=hoje_dt.isoformat(), x1=df_total_acum["Data"].max().isoformat(),
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray", opacity=0.2, layer="below", line_width=0
)
fig_cash.add_annotation(
    x=(hoje_dt + (df_total_acum["Data"].max() - hoje_dt)/2).isoformat(),
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

df_total_cash_past = df_total_acum[df_total_acum["Data"] <= hoje_dt]
df_total_cash_future = df_total_acum[df_total_acum["Data"] > hoje_dt]
df_sim_cash_future = df_sim_acum[df_sim_acum["Data"] > hoje_dt]

fig_cash.add_trace(go.Scatter(
    x=df_total_cash_past["Data"],
    y=df_total_cash_past["Cash_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Passado)",
    line=dict(color="#00008B", width=3, dash="solid")
))
fig_cash.add_trace(go.Scatter(
    x=df_total_cash_future["Data"],
    y=df_total_cash_future["Cash_acumulado"],
    mode="lines",
    name="Realizado/Previsto (Previsto)",
    line=dict(color="#00008B", width=3, dash="dash")
))

fig_cash.add_trace(go.Scatter(
    x=df_sim_cash_future["Data"],
    y=df_sim_cash_future["Cash_acumulado"],
    mode="lines",
    name="Simulação (Canceladas)",
    line=dict(color="#FF0000", width=3)
))

fig_cash.add_trace(go.Scatter(
    x=df_diff_acum["Data"],
    y=df_diff_acum["Cash_diferenca"],
    mode="lines",
    name="Diferença Acumulada",
    line=dict(color="#FF0000", width=2, dash="dot")
))

fig_cash.update_layout(
    title="Cash Acumulado - Baseline vs. Simulação",
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
        "df_diff": df_diff_acum.copy()
    }
    st.session_state.cenarios.append(scenario)
    st.sidebar.success("Cenário salvo com sucesso!")

if st.sidebar.button("Visualizar Comparação de Cenários"):
    if st.session_state.cenarios:
        st.subheader("Comparação de Cenários Salvos")
        for i, cen in enumerate(st.session_state.cenarios):
            st.write(
                f"**Cenário {i+1}:** Rotas Canceladas: " +
                (", ".join(cen["rotas_canceladas"]) if cen["rotas_canceladas"] else "Nenhuma")
            )
            st.write("Simulação Acumulada:")
            st.dataframe(cen["df_sim"][["Data", "GMV_acumulado", "Cash_acumulado"]])
            st.write("Diferença Acumulada:")
            st.dataframe(cen["df_diff"][["Data", "GMV_diferenca", "Cash_diferenca"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar valores com duas casas decimais.")



