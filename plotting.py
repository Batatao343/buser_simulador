# plotting.py
import plotly.graph_objects as go

def plot_gmv_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, check_start, check_end, hoje_dt):
    """
    Cria e retorna a figura do gráfico de GMV acumulado.
    - df_base_acum: acumulado do cenário base (realizado/previsto)
    - df_sim_acum: acumulado do cenário simulado (com cancelamentos)
    - df_diff: diferença acumulada entre simulação e base
    - df_baseline_meta: baseline histórico e meta diluída acumulados
    - check_start, check_end: início e fim do período de check de cancelamento
    - hoje_dt: data de hoje
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
    
    # Plota baseline histórico acumulado
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_baseline_acumulado"],
        mode="lines",
        name="Baseline Histórico (Acumul.)",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    
    # Plota meta histórica diluída acumulada
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_meta_acumulada"],
        mode="lines",
        name="Meta Hist. Diluída (Acumul.)",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))
    
    # Linha Realizado/Previsto: dividida em passado e futuro
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
    
    # Linha da Simulação (cancelamentos) - deve iniciar onde a linha azul termina
    df_sim_future = df_sim_acum[df_sim_acum["Data"] >= hoje_dt]
    fig.add_trace(go.Scatter(
        x=df_sim_future["Data"],
        y=df_sim_future["GMV_acumulado"],
        mode="lines",
        name="Simulação (Canceladas)",
        line=dict(color="red", width=3)
    ))
    
    # Linha de Diferença acumulada (entre simulação e base)
    df_diff_future = df_diff[df_diff["Data"] >= hoje_dt]
    fig.add_trace(go.Scatter(
        x=df_diff_future["Data"],
        y=df_diff_future["GMV_diferenca"],
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
    for trace in fig.data:
        trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"
    return fig

def plot_cash_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, check_start, check_end, hoje_dt):
    """
    Cria e retorna a figura do gráfico de Cash acumulado.
    Parametros e lógica análoga ao do gráfico de GMV.
    """
    fig = go.Figure()
    fig.update_xaxes(type="date")
    
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
    
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["Cash_baseline_acumulado"],
        mode="lines",
        name="Baseline Histórico (Acumul.)",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["Cash_meta_acumulada"],
        mode="lines",
        name="Meta Hist. Diluída (Acumul.)",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))
    
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
    
    df_sim_future = df_sim_acum[df_sim_acum["Data"] >= hoje_dt]
    fig.add_trace(go.Scatter(
        x=df_sim_future["Data"],
        y=df_sim_future["Cash_acumulado"],
        mode="lines",
        name="Simulação (Canceladas)",
        line=dict(color="red", width=3)
    ))
    
    df_diff_future = df_diff[df_diff["Data"] >= hoje_dt]
    fig.add_trace(go.Scatter(
        x=df_diff_future["Data"],
        y=df_diff_future["Cash_diferenca"],
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
