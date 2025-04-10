# plotting.py

import plotly.graph_objects as go
import pandas as pd

def plot_gmv_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, check_start, check_end, hoje_dt):
    """
    Cria o gráfico interativo de GMV Acumulado seguindo as regras de negócio:
      - Linha azul sólida para o acumulado realizado até hoje.
      - Linha azul tracejada para a projeção (dados futuros a partir de hoje).
      - A partir de 48h (check_start), a linha simulação (em vermelho) inicia exatamente 
        com o valor acumulado base (cutoff) e pode divergir.
      - Exibe também o Baseline Histórico Acumulado (linha cinza) e a Meta Histórica Diluída Acumulada (linha verde).
      - Uma faixa cinza com o rótulo "Período do check de cancelamento" é exibida no intervalo [check_start, check_end].
      - Uma linha vertical indica o dia de "Hoje".
    
    Parâmetros:
      - df_base_acum: DataFrame com o acumulado do cenário base (Realizado/Previsto)
      - df_sim_acum: DataFrame com o acumulado do cenário simulado (cancelamentos) 
                     (observação: para datas futuras)
      - df_diff: DataFrame com a diferença acumulada entre o cenário simulado e o base
      - df_baseline_meta: DataFrame com os dados de Baseline Histórico e Meta Histórica Diluída (acumulados)
      - check_start: início do período de check de cancelamento (hoje + 48h)
      - check_end: fim do período de check de cancelamento (hoje + 72h)
      - hoje_dt: data de hoje (como pd.Timestamp)
    
    Retorna:
      - fig: figura Plotly com o gráfico de GMV acumulado.
    """
    fig = go.Figure()
    fig.update_xaxes(type="date")
    
    # Adiciona faixa cinza para o período do check de cancelamento (48h a 72h a partir de hoje)
    fig.add_shape(
        type="rect",
        x0=check_start.isoformat(),
        x1=check_end.isoformat(),
        y0=0, y1=1,
        xref="x", yref="paper",
        fillcolor="gray",
        opacity=0.2,
        layer="below",
        line_width=0
    )
    fig.add_annotation(
        x=(check_start + (check_end - check_start) / 2).isoformat(),
        y=1.07,
        xref="x", yref="paper",
        showarrow=False,
        text="Período do check de cancelamento",
        font=dict(color="gray", size=12)
    )
    
    # Linha vertical para "Hoje"
    fig.add_vline(
        x=hoje_dt,  # mantendo hoje_dt como objeto datetime
        line=dict(color="black", dash="dash")
    )
    fig.add_annotation(
        x=hoje_dt,
        y=1.03,
        xref="x", yref="paper",
        showarrow=False,
        text="Hoje",
        font=dict(color="black", size=12)
    )
    
    # Plota o Baseline Histórico Acumulado (linha cinza tracejada)
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_baseline_acumulado"],
        mode="lines",
        name="Baseline Histórico (Acumul.)",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    
    # Plota a Meta Histórica Diluída Acumulada (linha verde pontilhada)
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_meta_acumulada"],
        mode="lines",
        name="Meta Hist. Diluída (Acumul.)",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))
    
    # Linha Realizado/Previsto Acumulado:
    # Divide em duas partes: passado (linha sólida) e futuro (linha tracejada)
    df_base_past = df_base_acum[df_base_acum["Data"] < hoje_dt]
    df_base_future = df_base_acum[df_base_acum["Data"] >= hoje_dt]
    fig.add_trace(go.Scatter(
        x=df_base_past["Data"],
        y=df_base_past["GMV_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Passado)",
        line=dict(color="#00008B", width=3, dash="solid")
    ))
    fig.add_trace(go.Scatter(
        x=df_base_future["Data"],
        y=df_base_future["GMV_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Futuro)",
        line=dict(color="#00008B", width=3, dash="dash")
    ))
    
    # Alinha a simulação: a partir do cutoff (hoje), a linha de simulação deve iniciar
    # com o mesmo valor acumulado do base
    base_cutoff = df_base_acum[df_base_acum["Data"] < hoje_dt]["GMV_acumulado"].max()
    df_future_sim = df_sim_acum[df_sim_acum["Data"] >= hoje_dt].copy()
    if not df_future_sim.empty:
        primeiro_valor_sim = df_future_sim.iloc[0]["GMV_acumulado"]
        # Ajusta a série para começar em base_cutoff
        df_future_sim["GMV_acumulado_alinhado"] = base_cutoff + (df_future_sim["GMV_acumulado"] - primeiro_valor_sim)
    else:
        df_future_sim["GMV_acumulado_alinhado"] = df_future_sim["GMV_acumulado"]
    
    fig.add_trace(go.Scatter(
        x=df_future_sim["Data"],
        y=df_future_sim["GMV_acumulado_alinhado"],
        mode="lines",
        name="Simulação (Canceladas)",
        line=dict(color="red", width=3)
    ))
    
    # Linha de Diferença Acumulada: diferença entre o acumulado simulado (alinhado) e o acumulado base para datas futuras
    df_diff_future = df_diff[df_diff["Data"] >= hoje_dt].copy()
    if not df_future_sim.empty and not df_diff_future.empty:
        df_diff_future["GMV_diferenca_alinhada"] = df_future_sim["GMV_acumulado_alinhado"].values - df_diff_future["GMV_acumulado"].values
    else:
        df_diff_future["GMV_diferenca_alinhada"] = df_diff_future["GMV_diferenca"]
    
    fig.add_trace(go.Scatter(
        x=df_diff_future["Data"],
        y=df_diff_future["GMV_diferenca_alinhada"],
        mode="lines",
        name="Diferença Acumulada",
        line=dict(color="red", width=2, dash="dot")
    ))
    
    fig.update_layout(
        title="GMV Acumulado - Base vs. Simulação",
        xaxis_title="Data",
        yaxis_title="GMV Acumulado",
        hovermode="x unified"
    )
    
    # Formata o hover para duas casas decimais
    for trace in fig.data:
        trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"
    
    return fig

def plot_cash_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, check_start, check_end, hoje_dt):
    """
    Cria o gráfico interativo de Cash Acumulado com a mesma lógica do GMV:
      - Linha sólida para o acumulado realizado (passado) e tracejada para o previsto (futuro).
      - A partir do cutoff, a simulação (canceladas) é realinhada para iniciar no mesmo valor
        do acumulado base, e a diferença é calculada e exibida.
      - São exibidos também o Baseline Histórico Acumulado (Cash) e a Meta Histórica Diluída Acumulada (Cash).
      - A faixa cinza e a linha vertical "Hoje" também estão presentes.
    """
    fig = go.Figure()
    fig.update_xaxes(type="date")
    
    # Faixa cinza para o período do check de cancelamento
    fig.add_shape(
        type="rect",
        x0=check_start.isoformat(),
        x1=check_end.isoformat(),
        y0=0, y1=1,
        xref="x", yref="paper",
        fillcolor="gray", opacity=0.2,
        layer="below",
        line_width=0
    )
    fig.add_annotation(
        x=(check_start + (check_end - check_start)/2).isoformat(),
        y=1.07,
        xref="x", yref="paper",
        showarrow=False,
        text="Período do check de cancelamento",
        font=dict(color="gray", size=12)
    )
    
    # Linha vertical para "Hoje"
    fig.add_vline(
        x=hoje_dt,
        line=dict(color="black", dash="dash")
    )
    fig.add_annotation(
        x=hoje_dt,
        y=1.03,
        xref="x", yref="paper",
        showarrow=False,
        text="Hoje",
        font=dict(color="black", size=12)
    )
    
    # Baseline Histórico Acumulado (Cash) – linha cinza
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["Cash_baseline_acumulado"],
        mode="lines",
        name="Baseline Histórico (Acumul.)",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    
    # Meta Histórica Diluída Acumulada (Cash) – linha verde pontilhada
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["Cash_meta_acumulada"],
        mode="lines",
        name="Meta Hist. Diluída (Acumul.)",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))
    
    # Linha Realizado/Previsto (Cash Acumulado)
    df_base_past = df_base_acum[df_base_acum["Data"] < hoje_dt]
    df_base_future = df_base_acum[df_base_acum["Data"] >= hoje_dt]
    fig.add_trace(go.Scatter(
        x=df_base_past["Data"],
        y=df_base_past["Cash_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Passado)",
        line=dict(color="#00008B", width=3, dash="solid")
    ))
    fig.add_trace(go.Scatter(
        x=df_base_future["Data"],
        y=df_base_future["Cash_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Futuro)",
        line=dict(color="#00008B", width=3, dash="dash")
    ))
    
    # Linha Simulação (Cash Acumulado) – para datas futuras, realinhada
    df_sim_future = df_sim_acum[df_sim_acum["Data"] >= hoje_dt].copy()
    if not df_sim_future.empty:
        primeiro_valor_sim = df_sim_future.iloc[0]["Cash_acumulado"]
        base_cutoff_cash = df_base_acum[df_base_acum["Data"] < hoje_dt]["Cash_acumulado"].max()
        df_sim_future["Cash_acumulado_alinhado"] = base_cutoff_cash + (df_sim_future["Cash_acumulado"] - primeiro_valor_sim)
    else:
        df_sim_future["Cash_acumulado_alinhado"] = df_sim_future["Cash_acumulado"]
    
    fig.add_trace(go.Scatter(
        x=df_sim_future["Data"],
        y=df_sim_future["Cash_acumulado_alinhado"],
        mode="lines",
        name="Simulação (Canceladas)",
        line=dict(color="red", width=3)
    ))
    
    # Linha de Diferença Acumulada (Cash) – diferença entre simulação realinhada e acumulado base, para datas futuras
    df_diff_future = df_diff[df_diff["Data"] >= hoje_dt].copy()
    if not df_diff_future.empty and not df_sim_future.empty:
        df_diff_future["Cash_diferenca_alinhada"] = df_sim_future["Cash_acumulado_alinhado"].values - df_diff_future["Cash_acumulado"].values
    else:
        df_diff_future["Cash_diferenca_alinhada"] = df_diff_future["Cash_diferenca"]
    
    fig.add_trace(go.Scatter(
        x=df_diff_future["Data"],
        y=df_diff_future["Cash_diferenca_alinhada"],
        mode="lines",
        name="Diferença Acumulada",
        line=dict(color="red", width=2, dash="dot")
    ))
    
    fig.update_layout(
        title="Cash Acumulado - Base vs. Simulação",
        xaxis_title="Data",
        yaxis_title="Cash Acumulado",
        hovermode="x unified"
    )
    for trace in fig.data:
        trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"
    return fig

