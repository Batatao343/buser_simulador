# streamlit_app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Importa funções dos outros módulos
from data import gerar_dados
from simulation import definir_valores, transformar_em_acumulado, calcular_meta_diluida, calcular_baseline_meta_acumulada
from plotting import plot_gmv_acumulado, plot_cash_acumulado

# Configuração da página
st.set_page_config(page_title="Simulação de Cancelamento de Rotas (Acumulado)", layout="wide")

st.title("Simulação de Cancelamento de Rotas (Acumulado)")

# Sidebar para configuração de dados e metas
st.sidebar.header("Configurações")
usar_dados_exemplo = st.sidebar.checkbox("Usar dados de exemplo", value=True)

# Carrega ou gera os dados
if usar_dados_exemplo:
    df = gerar_dados()
else:
    uploaded_file = st.sidebar.file_uploader("Carregue a planilha (CSV ou Excel)", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith("csv"):
                df = pd.read_csv(uploaded_file, parse_dates=["Data"])
            else:
                df = pd.read_excel(uploaded_file, parse_dates=["Data"])
        except Exception as e:
            st.error(f"Erro ao carregar os dados: {e}")
            st.stop()
    else:
        st.info("Carregue uma planilha para prosseguir.")
        st.stop()

df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

# Define cutoff para separar realizado e previsto (apenas viagens futuras podem ser canceladas)
hoje_dt = pd.Timestamp(datetime.now().date())
# Aqui, cutoff = hoje (você pode ajustar se preferir 48h a partir de agora)
cutoff = hoje_dt
df = definir_valores(df, cutoff)

# Seleção de rotas para cancelamento (apenas se aplicável aos dados futuros)
rotas_disponiveis = sorted(df["Rota"].unique())
rotas_canceladas = st.sidebar.multiselect("Selecione rotas a cancelar", rotas_disponiveis)

# Define o período de check para viagens futuras (48 a 72 horas a partir de hoje)
data_atual = pd.Timestamp.now()
check_start = data_atual + pd.Timedelta(hours=48)
check_end = data_atual + pd.Timedelta(hours=72)

# Divide o dataframe em passado (realizado) e futuro (previsto)
df_past = df[df["Data"] < cutoff].copy()
df_future = df[df["Data"] >= cutoff].copy()

# Na parte futura, para a simulação, remove as rotas canceladas
if rotas_canceladas:
    df_future_sim = df_future[~df_future["Rota"].isin(rotas_canceladas)].copy()
else:
    df_future_sim = df_future.copy()

# Agrega os dados diários (não acumulados) do conjunto completo e do cenário simulado
def agrupar_por_data(df_in):
    agg = df_in.groupby("Data", as_index=False).agg({
        "GMV_valor": "sum",
        "Cash_valor": "sum",
        "GMV_baseline": "sum",
        "Cash_baseline": "sum"
    }).sort_values("Data")
    return agg

df_agg_total = df.groupby("Data", as_index=False).agg({
    "GMV_valor": "sum",
    "Cash_valor": "sum",
    "GMV_baseline": "sum",
    "Cash_baseline": "sum"
}).sort_values("Data")
df_agg_future_sim = agrupar_por_data(df_future_sim)

# Converte os dados agregados em acumulado (para os valores realizados/previstos)
df_base_acum = transformar_em_acumulado(df_agg_total, "GMV_valor", "Cash_valor")
df_sim_acum = pd.concat([
    df_agg_total[df_agg_total["Data"] < cutoff],
    df_agg_future_sim
]).sort_values("Data")
df_sim_acum = transformar_em_acumulado(df_sim_acum, "GMV_valor", "Cash_valor")

# Calcula as diferenças acumuladas (apenas para datas futuras)
df_diff = pd.merge(
    df_base_acum[df_base_acum["Data"] >= cutoff][["Data", "GMV_acumulado", "Cash_acumulado"]],
    df_sim_acum[df_sim_acum["Data"] >= cutoff][["Data", "GMV_acumulado", "Cash_acumulado"]].rename(
        columns={"GMV_acumulado": "GMV_acumulado_sim", "Cash_acumulado": "Cash_acumulado_sim"}
    ),
    on="Data",
    how="left"
)
df_diff["GMV_diferenca"] = df_diff["GMV_acumulado_sim"] - df_diff["GMV_acumulado"]
df_diff["Cash_diferenca"] = df_diff["Cash_acumulado_sim"] - df_diff["Cash_acumulado"]

# Calcula baseline histórico e meta histórica diluída acumulados (usando todos os dados)
df_baseline_meta = df.groupby("Data", as_index=False).agg({
    "GMV_baseline": "sum",
    "Cash_baseline": "sum"
}).sort_values("Data")
df_baseline_meta = calcular_baseline_meta_acumulada(df_baseline_meta)

# Sidebar para definir metas
st.sidebar.subheader("Metas Mensais")
meta_mensal_gmv = st.sidebar.number_input("Meta Mensal GMV", min_value=1000, value=600000, step=10000)
meta_mensal_cash = st.sidebar.number_input("Meta Mensal Cash-Repasse", min_value=1000, value=300000, step=10000)

# Para este exemplo, as funções de cálculo de meta histórica diluída estão implementadas em simulation.py
# Já que usamos dados de exemplo para o baseline, esse módulo calcula e retorna os acumulados

# ---------------------------------------------------------------------
# Plotagem dos gráficos – usando as funções definidas em plotting.py
# ---------------------------------------------------------------------
fig_gmv = plot_gmv_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, check_start, check_end, hoje_dt)
fig_cash = plot_cash_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, check_start, check_end, hoje_dt)

st.subheader("Gráficos Interativos")
st.plotly_chart(fig_gmv, use_container_width=True)
st.plotly_chart(fig_cash, use_container_width=True)

# -----------------------------------------------------------------------------
# Comparação de Cenários (salvar e visualizar)
# -----------------------------------------------------------------------------
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
            st.write(f"**Cenário {i+1}:** Rotas Canceladas: " +
                     (", ".join(cen["rotas_canceladas"]) if cen["rotas_canceladas"] else "Nenhuma"))
            st.write("Simulação Acumulada:")
            st.dataframe(cen["df_sim"][["Data", "GMV_acumulado", "Cash_acumulado"]])
            st.write("Diferença Acumulada:")
            st.dataframe(cen["df_diff"][["Data", "GMV_diferenca", "Cash_diferenca"]])
    else:
        st.sidebar.info("Nenhum cenário salvo ainda.")

st.info("Passe o mouse sobre os gráficos para visualizar valores com duas casas decimais.")

