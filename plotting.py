# plotting.py

import plotly.graph_objects as go
import pandas as pd

def plot_gmv_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, 
                       check_start, check_end, hoje_dt):
    """
    Cria o gráfico de GMV Acumulado seguindo as regras:
      1. Até hoje, linha azul sólida (acumulado realizado).
      2. De hoje até check_start, linha azul tracejada (previsto), sem linha vermelha.
      3. A partir de check_start, inicia a linha vermelha (Simulação),
         partindo do valor acumulado do cenário base no momento check_start.
      4. Exibe Baseline Histórico Acumulado (cinza) e Meta Histórica Diluída Acumulada (verde).
      5. Faixa cinza entre check_start e check_end com rótulo "Período do check de cancelamento".
      6. Linha vertical em 'hoje'.
    """

    fig = go.Figure()
    fig.update_xaxes(type="date")

    # ------------------------------
    # 1) Faixa cinza: check_start -> check_end
    # ------------------------------
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
        x=(check_start + (check_end - check_start)/2).isoformat(),
        y=1.07,
        xref="x",
        yref="paper",
        showarrow=False,
        text="Período do check de cancelamento",
        font=dict(color="gray", size=12)
    )

    # ------------------------------
    # 2) Linha vertical em 'hoje'
    # ------------------------------
    fig.add_vline(
        x=hoje_dt,
        line=dict(color="black", dash="dash")
    )
    fig.add_annotation(
        x=hoje_dt,
        y=1.03,
        xref="x",
        yref="paper",
        showarrow=False,
        text="Hoje",
        font=dict(color="black", size=12)
    )

    # ------------------------------
    # 3) Baseline Histórico (acumulado) e Meta Histórica Diluída (acumulada)
    # ------------------------------
    # Linha cinza (Baseline Histórico) - dash
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_baseline_acumulado"],
        mode="lines",
        name="Baseline Histórico (Acumul.)",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    # Linha verde (Meta Hist. Diluída) - dot
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_meta_acumulada"],
        mode="lines",
        name="Meta Hist. Diluída (Acumul.)",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))

    # ------------------------------
    # 4) Linha Azul (Realizado/Previsto)
    # ------------------------------
    # - Sólida até hoje
    df_base_past = df_base_acum[df_base_acum["Data"] < hoje_dt]
    # - Tracejada de hoje até o fim (ou até check_end, mas aqui usamos todos)
    df_base_future = df_base_acum[df_base_acum["Data"] >= hoje_dt]

    # Linha sólida (passado)
    fig.add_trace(go.Scatter(
        x=df_base_past["Data"],
        y=df_base_past["GMV_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Passado)",
        line=dict(color="#00008B", width=3, dash="solid")
    ))
    # Linha tracejada (futuro) - do hoje até fim
    fig.add_trace(go.Scatter(
        x=df_base_future["Data"],
        y=df_base_future["GMV_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Futuro)",
        line=dict(color="#00008B", width=3, dash="dash")
    ))

    # ------------------------------
    # 5) Linha Vermelha (Simulação) só inicia em check_start
    # ------------------------------
    # Precisamos realinhar a simulação a partir do valor acumulado base no check_start.
    # 5.1 Identificar o valor acumulado do cenário base no check_start.
    #     Precisamos do maior valor do df_base_acum com Data < check_start.
    df_base_before_check = df_base_acum[df_base_acum["Data"] < check_start]
    if not df_base_before_check.empty:
        base_cutoff_gmv = df_base_before_check["GMV_acumulado"].max()
    else:
        # Caso não haja dados antes de check_start, assumimos zero
        base_cutoff_gmv = 0

    # 5.2 Filtrar as datas da simulação a partir de check_start
    df_sim_check = df_sim_acum[df_sim_acum["Data"] >= check_start].copy()
    if not df_sim_check.empty:
        primeiro_valor_sim = df_sim_check.iloc[0]["GMV_acumulado"]
        # Reajusta para alinhar ao base_cutoff_gmv
        df_sim_check["GMV_acumulado_alinhado"] = base_cutoff_gmv + (df_sim_check["GMV_acumulado"] - primeiro_valor_sim)
    else:
        df_sim_check["GMV_acumulado_alinhado"] = df_sim_check["GMV_acumulado"]

    # Plot da linha vermelha (Simulação) - inicia no check_start
    fig.add_trace(go.Scatter(
        x=df_sim_check["Data"],
        y=df_sim_check["GMV_acumulado_alinhado"],
        mode="lines",
        name="Simulação (Canceladas)",
        line=dict(color="red", width=3)
    ))

    # ------------------------------
    # 6) Diferença Acumulada (também a partir de check_start)
    # ------------------------------
    df_diff_check = df_diff[df_diff["Data"] >= check_start].copy()
    if not df_sim_check.empty and not df_diff_check.empty:
        # Precisamos reajustar a diferença usando 'GMV_acumulado_alinhado'
        # do df_sim_check e 'GMV_acumulado' do df_diff_check
        # Alinhar pelo índice ou pela data
        # (assumindo que 'df_sim_check' e 'df_diff_check' têm o mesmo "conjunto" de datas, 
        # caso contrário seria um merge).
        df_diff_check = df_diff_check.merge(
            df_sim_check[["Data","GMV_acumulado_alinhado"]], 
            on="Data", 
            how="left"
        )
        df_diff_check["GMV_diferenca_alinhada"] = df_diff_check["GMV_acumulado_alinhado"] - df_diff_check["GMV_acumulado"]
    else:
        df_diff_check["GMV_diferenca_alinhada"] = df_diff_check["GMV_diferenca"]

    fig.add_trace(go.Scatter(
        x=df_diff_check["Data"],
        y=df_diff_check["GMV_diferenca_alinhada"],
        mode="lines",
        name="Diferença Acumulada",
        line=dict(color="red", width=2, dash="dot")
    ))

    # ------------------------------
    # Layout e Hover
    # ------------------------------
    fig.update_layout(
        title="GMV Acumulado - Base vs. Simulação",
        xaxis_title="Data",
        yaxis_title="GMV Acumulado",
        hovermode="x unified"
    )
    for trace in fig.data:
        trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"

    return fig


def plot_cash_acumulado(df_base_acum, df_sim_acum, df_diff, df_baseline_meta, 
                        check_start, check_end, hoje_dt):
    """
    Gráfico de Cash Acumulado, mesma lógica do GMV:
      - Linha azul sólida até hoje, tracejada até check_start,
      - Linha vermelha inicia só no check_start,
      - Faixa cinza [check_start, check_end], linha vertical 'Hoje',
      - Baseline e Meta Hist. Diluída acumulados.
    """

    fig = go.Figure()
    fig.update_xaxes(type="date")

    # Faixa cinza
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
        x=(check_start + (check_end - check_start)/2).isoformat(),
        y=1.07,
        xref="x",
        yref="paper",
        showarrow=False,
        text="Período do check de cancelamento",
        font=dict(color="gray", size=12)
    )

    # Linha vertical "Hoje"
    fig.add_vline(
        x=hoje_dt,
        line=dict(color="black", dash="dash")
    )
    fig.add_annotation(
        x=hoje_dt,
        y=1.03,
        xref="x", 
        yref="paper",
        showarrow=False,
        text="Hoje",
        font=dict(color="black", size=12)
    )

    # Baseline Histórico Acumulado (Cash) + Meta Hist. Diluída
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

    # Linha Azul: Realizado/Previsto
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

    # Linha Vermelha (Simulação) começando apenas no check_start
    df_base_before_check = df_base_acum[df_base_acum["Data"] < check_start]
    if not df_base_before_check.empty:
        base_cutoff_cash = df_base_before_check["Cash_acumulado"].max()
    else:
        base_cutoff_cash = 0

    df_sim_check = df_sim_acum[df_sim_acum["Data"] >= check_start].copy()
    if not df_sim_check.empty:
        primeiro_valor_sim = df_sim_check.iloc[0]["Cash_acumulado"]
        df_sim_check["Cash_acumulado_alinhado"] = base_cutoff_cash + (df_sim_check["Cash_acumulado"] - primeiro_valor_sim)
    else:
        df_sim_check["Cash_acumulado_alinhado"] = df_sim_check["Cash_acumulado"]

    fig.add_trace(go.Scatter(
        x=df_sim_check["Data"],
        y=df_sim_check["Cash_acumulado_alinhado"],
        mode="lines",
        name="Simulação (Canceladas)",
        line=dict(color="red", width=3)
    ))

    # Diferença Acumulada (Cash)
    df_diff_check = df_diff[df_diff["Data"] >= check_start].copy()
    if not df_diff_check.empty and not df_sim_check.empty:
        df_diff_check = df_diff_check.merge(
            df_sim_check[["Data","Cash_acumulado_alinhado"]], 
            on="Data", 
            how="left"
        )
        df_diff_check["Cash_diferenca_alinhada"] = df_diff_check["Cash_acumulado_alinhado"] - df_diff_check["Cash_acumulado"]
    else:
        df_diff_check["Cash_diferenca_alinhada"] = df_diff_check["Cash_diferenca"]

    fig.add_trace(go.Scatter(
        x=df_diff_check["Data"],
        y=df_diff_check["Cash_diferenca_alinhada"],
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

