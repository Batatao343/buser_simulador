import streamlit as st
import pandas as pd

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
    
    # Cria colunas para os valores simulados (inicialmente iguais ao baseline)
    df["gmv_sim"] = df["gmv"]
    df["cash_sim"] = df["cash_repasse"]
    
    st.subheader("Ajuste de Cancelamento (Marque as rotas com cash‑repasse negativo)")
    
    # Cabeçalho para a visualização em colunas
    col_check, col_rota, col_data, col_gmv_base, col_cash_base, col_gmv_sim, col_cash_sim = st.columns([1,2,2,2,2,2,2])
    with col_check: st.markdown("**Cancelar**")
    with col_rota: st.markdown("**Rota**")
    with col_data: st.markdown("**Data**")
    with col_gmv_base: st.markdown("**GMV Base**")
    with col_cash_base: st.markdown("**Cash Base**")
    with col_gmv_sim: st.markdown("**GMV Simulado**")
    with col_cash_sim: st.markdown("**Cash Simulado**")
    
    # Loop pelas linhas para exibir cada rota com seus valores e a checkbox
    for index, row in df.iterrows():
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1,2,2,2,2,2,2])
        
        # Checkbox para cancelar a rota
        with col1:
            cancel = st.checkbox("", key=f"cancel_{row['id']}")
        
        with col2:
            st.write(row["rota"])
        
        with col3:
            st.write(row["data"])
        
        with col4:
            st.write(row["gmv"])
        
        with col5:
            st.write(row["cash_repasse"])
        
        # Se marcada a checkbox, atualiza os valores simulados
        if cancel:
            df.at[index, "gmv_sim"] = 0
            df.at[index, "cash_sim"] = row["cash_repasse"] * 1.1  # Exemplo: aumento de 10% no cash
        else:
            df.at[index, "gmv_sim"] = row["gmv"]
            df.at[index, "cash_sim"] = row["cash_repasse"]
        
        with col6:
            st.write(df.at[index, "gmv_sim"])
        
        with col7:
            st.write(df.at[index, "cash_sim"])
    
    st.subheader("Tabela Final: Baseline vs. Simulação")
    st.dataframe(df[["id", "rota", "data", "gmv", "cash_repasse", "gmv_sim", "cash_sim"]])
else:
    st.info("Aguardando o upload da planilha")
