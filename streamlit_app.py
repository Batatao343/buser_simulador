import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# =============================================================================
# Configuração inicial da aplicação
# =============================================================================
st.set_page_config(page_title="Simulação de Cancelamento de Rotas", layout="wide")

# =============================================================================
# Funções de geração e transformação de dados
# =============================================================================
@st.cache_data
def gerar_dados():
    """
    Gera dados de teste para 31 dias: 15 dias no passado e 16 no futuro a partir de hoje,
    para 20 rotas.

    - GMV_baseline: valores aleatórios entre 500 e 2000 por rota/dia.
    - Cash_baseline: valores aleatórios entre -500 e 1000 (permitindo valores negativos).
    - GMV_realizado e Cash_realizado: gerados com base no baseline com algum ruído.

    Retorna um DataFrame com colunas:
      - Data (datetime)
      - Rota (string)
      - GMV_baseline, GMV_realizado
      - Cash_baseline, Cash_realizado
    """
    num_dias_past = 15   # Quantos dias passados
    num_dias_future = 16 # Quantos dias futuros
    total_dias = num_dias_past + num_dias_future
    start_date = datetime.now().date() - timedelta(days=num_dias_past)
    
    # Cria um range de datas (Timestamp do pandas)
    datas = pd.date_range(start=start_date, periods=total_dias, freq="D")
    
    # Número de rotas e nomes
    num_rotas = 20
    rotas = [f"R{i+1}" for i in range(num_rotas)]
    
    dados = []
    # Gera baseline e realizado para GMV e Cash
    for data in datas:
        for rota in rotas:
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
    return df

def definir_valores(df, cutoff):
    """
    Define colunas de GMV_valor / Cash_valor:

    - Para datas < cutoff, usa valor realizado
    - Para datas >= cutoff, usa valor baseline (como projeção)

    Retorna o DataFrame com GMV_valor e Cash_valor.
    """
    df["GMV_valor"] = np.where(df["Data"] < cutoff, df["GMV_realizado"], df["GMV_baseline"])
    df["Cash_valor"] = np.where(df["Data"] < cutoff, df["Cash_realizado"], df["Cash_baseline"])
    return df

def calcular_meta_diluida(df_agg, meta_gmv, meta_cash):
    """
    Com base nos pesos históricos (baseline), calcula GMV_meta_diluida e Cash_meta_diluida.

    - Peso_GMV = GMV_baseline / soma total do GMV_baseline
    - GMV_meta_diluida = meta_gmv * Peso_GMV
    (o mesmo para Cash)
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
    
    return df_agg

def transformar_em_acumulado(df, col_gmv, col_cash):
    """
    Converte valores diários em valores acumulados por data.
    Importante: a Data deve estar em ordem crescente antes de fazer o cumsum.

    Parâmetros:
      - df: DataFrame com colunas Data, col_gmv e col_cash
      - col_gmv: nome da coluna de GMV a acumular
      - col_cash: nome da coluna de Cash a acumular

    Retorna o DataFrame com as colunas de GMV_acumulado e Cash_acumulado.
    """
    # Ordena por data para garantir a soma cumulativa correta
    df_sorted = df.sort_values("Data").copy()
    df_sorted["GMV_acumulado"] = df_sorted[col_gmv].cumsum()
    df_sorted["Cash_acumulado"] = df_sorted[col_cash].cumsum()
    return df_sorted

def agregar_indicadores(df_filtrado):
    """
    Agrupa por Data e soma as colunas:
      GMV_baseline, GMV_valor, Cash_baseline, Cash_valor.
    Depois converte para acumulado.
    
    Retorna um DataFrame com Data, GMV_baseline, GMV_valor, Cash_baseline, Cash_valor,
    GMV_acumulado, Cash_acumulado.
    """
    agg = df_filtrado.groupby("Data", as_index=False).agg({
        "GMV_baseline": "sum",
        "GMV_valor": "sum",
        "Cash_baseline": "sum",
        "Cash_valor": "sum"
    })
    # Transforma em acumulado
    agg_sorted = transformar_em_acumulado(agg, "GMV_valor", "Cash_valor")
    return agg_sorted

# =============================================================================
# Início da aplicação
# =============================================================================
st.title("Simulação de Cancelamento de Rotas (Acumulado)")

# Barra lateral: configurações
st.sidebar.header("Configurações")

# 1) Carregamento de dados
usar_dados_exemplo = st.sidebar.checkbox("Usar dados de exemplo", value=True)
if usar_dados_exemplo:
    df = gerar_dados()
else:
    uploaded_file = st.sidebar.file_uploader("Carregue a planilha (CSV ou Excel)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, parse_dates=["Data"])
        else:
            df = pd.read_excel(uploaded_file, parse_dates=["Data"])
    else:
        st.stop()

# Garante que Data seja datetime
df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

# Define cutoff (48h a partir de agora)
cutoff = pd.Timestamp.now() + pd.Timedelta(hours=48)
df = definir_valores(df, cutoff)

# 2) Seleção de rotas para cancelamento
rotas_disponiveis = sorted(df["Rota"].unique().tolist())
rotas_canceladas = st.sidebar.multiselect("Selecione rotas para cancelar", rotas_disponiveis)

# 3) Definição do período de check (48h a 72h)
data_atual = pd.Timestamp.now()
inicio_check = data_atual + pd.Timedelta(hours=48)  # mesmo que cutoff
fim_check = data_atual + pd.Timedelta(hours=72)

# Filtra as datas do período de check
df_check = df[(df["Data"] >= inicio_check) & (df["Data"] <= fim_check)]

# Remove as rotas canceladas do período de check
if rotas_canceladas:
    df_check = df_check[~df_check["Rota"].isin(rotas_canceladas)]

# 4) Agrega dados para baseline e simulação
df_agg_total = agregar_indicadores(df)       # Todos os dias (acumulado)
df_agg_sim = agregar_indicadores(df_check)   # Apenas período do check cancelado (acumulado)

# 5) Configuração de metas
st.sidebar.subheader("Metas Mensais")
meta_mensal_gmv = st.sidebar.number_input("Meta Mensal GMV", min_value=1000, value=600000, step=10000)
meta_mensal_cash = st.sidebar.number_input("Meta Mensal Cash-Repasse", min_value=1000, value=300000, step=10000)

# 5.1) Calcula metas diluídas (opcional)
df_agg_total = calcular_meta_diluida(df_agg_total, meta_mensal_gmv, meta_mensal_cash)
df_agg_sim = calcular_meta_diluida(df_agg_sim, meta_mensal_gmv, meta_mensal_cash)

# 6) Calcula diferença no acumulado entre simulação e baseline
# (Podemos mesclar com base em Data para ver a diferença nos valores acumulados)
df_diff = pd.merge(
    df_agg_total[["Data", "GMV_acumulado", "Cash_acumulado"]],
    df_agg_sim[["Data", "GMV_acumulado", "Cash_acumulado"]].rename(columns={
        "GMV_acumulado": "GMV_acumulado_sim",
        "Cash_acumulado": "Cash_acumulado_sim"
    }),
    on="Data",
    how="left"
)
# Diferença no acumulado
df_diff["GMV_diferenca"] = df_diff["GMV_acumulado_sim"] - df_diff["GMV_acumulado"]
df_diff["Cash_diferenca"] = df_diff["Cash_acumulado_sim"] - df_diff["Cash_acumulado"]

# =============================================================================
# Criação dos gráficos
# =============================================================================
st.subheader("Gráfico Interativo - GMV Acumulado")

# Preparamos a figure do GMV
fig_gmv = go.Figure()

# Declara eixo X como tipo data
fig_gmv.update_xaxes(type="date")

# Faixa cinza para o período de check
fig_gmv.add_shape(
    type="rect",
    x0=inicio_check.isoformat(), x1=fim_check.isoformat(),
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray", opacity=0.2, layer="below", line_width=0
)
# Adiciona label na faixa cinza
fig_gmv.add_annotation(
    x=(inicio_check + (fim_check - inicio_check)/2).isoformat(),  # meio da faixa
    y=1.07,
    xref="x",
    yref="paper",
    showarrow=False,
    text="Período do check de cancelamento",
    font=dict(color="gray", size=12)
)

# Linha de GMV acumulado (baseline)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_total["Data"],
    y=df_agg_total["GMV_acumulado"],
    mode="lines",
    name="GMV Acumulado (Baseline)",
    line=dict(color="blue", width=3)
))

# Linha de GMV acumulado simulação (vermelho)
fig_gmv.add_trace(go.Scatter(
    x=df_agg_sim["Data"],
    y=df_agg_sim["GMV_acumulado"],
    mode="lines",
    name="Simulação (Acumulado)",
    line=dict(color="red", width=3, dash="solid")
))

# Linha de diferença (dash dot)
fig_gmv.add_trace(go.Scatter(
    x=df_diff["Data"],
    y=df_diff["GMV_diferenca"],
    mode="lines",
    name="Diferença Acumulada",
    line=dict(color="red", width=2, dash="dot")
))

# Ajustes finais no layout
fig_gmv.update_layout(
    title="GMV Acumulado - Baseline vs. Simulação",
    xaxis_title="Data",
    yaxis_title="GMV Acumulado",
    hovermode="x unified"
)

# Formata hover com duas casas decimais
for trace in fig_gmv.data:
    trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"

st.plotly_chart(fig_gmv, use_container_width=True)

# ============================================================================
# Gráfico de Cash Acumulado
# ============================================================================
st.subheader("Gráfico Interativo - Cash Acumulado")

fig_cash = go.Figure()
fig_cash.update_xaxes(type="date")

# Faixa cinza
fig_cash.add_shape(
    type="rect",
    x0=inicio_check.isoformat(), x1=fim_check.isoformat(),
    y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="gray", opacity=0.2, layer="below", line_width=0
)
# Label na faixa cinza
fig_cash.add_annotation(
    x=(inicio_check + (fim_check - inicio_check)/2).isoformat(),
    y=1.07,
    xref="x",
    yref="paper",
    showarrow=False,
    text="Período do check de cancelamento",
    font=dict(color="gray", size=12)
)

# Linha baseline (Cash acumulado)
fig_cash.add_trace(go.Scatter(
    x=df_agg_total["Data"],
    y=df_agg_total["Cash_acumulado"],
    mode="lines",
    name="Cash Acumulado (Baseline)",
    line=dict(color="blue", width=3)
))

# Linha simulação (Cash acumulado)
fig_cash.add_trace(go.Scatter(
    x=df_agg_sim["Data"],
    y=df_agg_sim["Cash_acumulado"],
    mode="lines",
    name="Simulação (Acumulado)",
    line=dict(color="red", width=3, dash="solid")
))

# Diferença (Cash)
fig_cash.add_trace(go.Scatter(
    x=df_diff["Data"],
    y=df_diff["Cash_diferenca"],
    mode="lines",
    name="Diferença Acumulada",
    line=dict(color="red", width=2, dash="dot")
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
        "df_sim": df_agg_sim.copy(),
        "df_diff": df_diff.copy()
    }
    st.session_state.cenarios.append(scenario)
    st.sidebar.success("Cenário salvo com sucesso!")

if st.sidebar.button("Visualizar Comparação de Cenários"):
    if st.session_state.cenarios:
        st.subheader("Comparação de Cenários Salvos")
        for i, cen in enumerate(st.session_state.cenarios):
            st.write(f"**Cenário {i+1}:** Rotas Canceladas: {', '.join(cen['rotas_canceladas']) if cen['rotas_canceladas'] else 'Nenhuma'}")
            st.write("Simulação Acumulado:")
            st.dataframe(cen["df_sim"][["Data","GMV_acumulado","Cash_acumulado"]])
            st.write("Diferença Acumulada:")
            st.dataframe(cen["df_diff"][["Data","GMV_diferenca","Cash_diferenca"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar valores com duas casas decimais.")






