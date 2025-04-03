import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Simulação de Cancelamento de Rotas")

# Carregamento do arquivo CSV ou XLSX
uploaded_file = st.file_uploader("Carregue sua planilha (.csv ou .xlsx)", type=["csv", "xlsx"])
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        st.stop()
    
    # Verifica se as colunas necessárias existem
    required_cols = {"id", "rota", "data", "gmv", "cash_repasse"}
    if not required_cols.issubset(df.columns):
        st.error(f"Arquivo deve conter as colunas: {required_cols}")
        st.stop()
    
    # Guarda uma cópia dos dados originais para o gráfico baseline
    baseline_df = df.copy()
    # Cria uma cópia para a simulação (será atualizada)
    df_sim = df.copy()

    st.subheader("Selecione as rotas para cancelamento (selecione as que deseja cancelar)")
    
    # Exibe o cabeçalho da tabela com colunas definidas
    cols = st.columns([1,2,2,2,2])
    cols[0].markdown("**Cancelar**")
    cols[1].markdown("**Rota**")
    cols[2].markdown("**Data**")
    cols[3].markdown("**GMV**")
    cols[4].markdown("**Cash‑Repasse**")
    
    # Loop pelas linhas para exibir cada rota com seus dados e checkbox
    for index, row in df_sim.iterrows():
        c1, c2, c3, c4, c5 = st.columns([1,2,2,2,2])
        
        with c1:
            cancel = st.checkbox("", key=f"cancel_{row['id']}")
        with c2:
            st.write(row["rota"])
        with c3:
            st.write(row["data"])
        with c4:
            st.write(row["gmv"])
        with c5:
            st.write(row["cash_repasse"])
        
        # Se o usuário marcar o cancelamento, atualiza os valores diretamente
        if cancel:
            df_sim.at[index, "gmv"] = 0
            df_sim.at[index, "cash_repasse"] = 0

    # Agrega os totais para o gráfico comparativo
    totals_baseline = {
        "GMV": baseline_df["gmv"].sum(),
        "Cash‑Repasse": baseline_df["cash_repasse"].sum()
    }
    totals_sim = {
        "GMV": df_sim["gmv"].sum(),
        "Cash‑Repasse": df_sim["cash_repasse"].sum()
    }
    
    totals_df = pd.DataFrame({
        "Indicador": ["GMV", "Cash‑Repasse"],
        "Baseline": [totals_baseline["GMV"], totals_baseline["Cash‑Repasse"]],
        "Simulação": [totals_sim["GMV"], totals_sim["Cash‑Repasse"]]
    })
    
    st.subheader("Gráfico Comparativo dos Totais")
    fig = px.bar(totals_df, x="Indicador", y=["Baseline", "Simulação"],
                 barmode="group",
                 title="Totais: Baseline vs. Simulação",
                 labels={"value": "Total", "variable": "Cenário"})
    st.plotly_chart(fig)
else:
    st.info("Aguardando o upload da planilha")

