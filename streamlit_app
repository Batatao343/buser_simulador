import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Dashboard de Simulação de Cancelamento de Rotas")

# Carregamento do arquivo (.csv ou .xlsx)
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

    # Exemplo de colunas esperadas: 'id', 'rota', 'data', 'gmv', 'cash_repasse'
    st.subheader("Dados Carregados")
    st.dataframe(df)

    # Cria uma cópia dos dados para a simulação
    df_sim = df.copy()

    st.markdown("## Selecione as rotas para cancelamento")
    # Lista para armazenar as rotas canceladas
    canceladas = []
    # Itera sobre as rotas e cria uma checkbox para cada uma
    for index, row in df.iterrows():
        checkbox_label = f"Cancelar rota {row['rota']} em {row['data']} (GMV: {row['gmv']}, Cash: {row['cash_repasse']})"
        if st.checkbox(checkbox_label, key=row['id']):
            canceladas.append(row['id'])
            # Lógica de simulação:
            # Exemplo: se cancelada, GMV passa a 0 e o cash_repasse aumenta em 10% (apenas como exemplo)
            df_sim.loc[df_sim['id'] == row['id'], 'gmv'] = 0
            df_sim.loc[df_sim['id'] == row['id'], 'cash_repasse'] *= 1.10

    st.subheader("Dados de Simulação")
    st.dataframe(df_sim)

    # Agregação dos indicadores para comparação
    total_gmv_baseline = df['gmv'].sum()
    total_cash_baseline = df['cash_repasse'].sum()

    total_gmv_sim = df_sim['gmv'].sum()
    total_cash_sim = df_sim['cash_repasse'].sum()

    comparison_df = pd.DataFrame({
        'Indicador': ['GMV', 'Cash-Repasse'],
        'Baseline': [total_gmv_baseline, total_cash_baseline],
        'Simulação': [total_gmv_sim, total_cash_sim]
    })

    st.markdown("## Gráfico Comparativo")
    fig = px.bar(comparison_df, x='Indicador', y=['Baseline', 'Simulação'],
                 barmode='group', title="Comparativo de Indicadores (Baseline vs. Simulação)",
                 labels={'value': 'Valor', 'variable': 'Cenário'})
    st.plotly_chart(fig)

    st.info("A linha de base (baseline) representa os valores históricos (exibidos na tabela original). A simulação (alterada via cancelamento) está refletida nos dados e no gráfico comparativo.")

else:
    st.info("Aguardando o upload da planilha")
