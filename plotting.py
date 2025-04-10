# plotting.py

import plotly.graph_objects as go
import pandas as pd

def plot_gmv_acumulado(
    df_base_acum,    # DF acumulado do cenário base (Realizado/Previsto)
    df_sim_acum,     # DF acumulado do cenário simulado (cancelamentos)
    df_diff,         # Diferença acumulada entre simulação e base
    df_baseline_meta,# DF com baseline histórico acumulado e meta histórica diluída acumulada
    check_start,     # Início do período de check (hoje + 48h)
    check_end,       # Fim do período de check (hoje + 72h)
    hoje_dt,         # Dia de hoje (Timestamp)
    rotas_canceladas # Lista de rotas canceladas (pode estar vazia ou não)
):
    """
    Cria o gráfico de GMV Acumulado com as regras:
      - Linha azul sólida até hoje (Realizado),
      - Linha azul tracejada de hoje até o fim (Previsto),
      - Linha vermelha começa somente em check_start, 
        coincidindo com a linha azul se NÃO houver cancelamento,
      - Baseline histórico acumulado (cinza) e Meta diluída acumulada (verde),
      - Faixa cinza [check_start, check_end] e linha vertical em hoje.
    """

    fig = go.Figure()
    fig.update_xaxes(type="date")

    # (1) Faixa cinza indicando [check_start, check_end]
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

    # (2) Linha vertical em hoje
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

    # (3) Baseline Histórico Acumulado (GMV) e Meta Hist. Diluída Acumulada
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_baseline_acumulado"],
        mode="lines",
        name="Baseline Histórico (Acumul.)",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_meta_acumulada"],
        mode="lines",
        name="Meta Hist. Diluída (Acumul.)",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))

    # (4) Linha Azul (Realizado/Previsto)
    #     - sólida até hoje
    df_base_past = df_base_acum[df_base_acum["Data"] < hoje_dt]
    #     - tracejada de hoje em diante
    df_base_future = df_base_acum[df_base_acum["Data"] >= hoje_dt]

    # Azul sólida (passado)
    fig.add_trace(go.Scatter(
        x=df_base_past["Data"],
        y=df_base_past["GMV_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Passado)",
        line=dict(color="#00008B", width=3, dash="solid")
    ))
    # Azul tracejada (futuro)
    fig.add_trace(go.Scatter(
        x=df_base_future["Data"],
        y=df_base_future["GMV_acumulado"],
        mode="lines",
        name="Realizado/Previsto (Futuro)",
        line=dict(color="#00008B", width=3, dash="dash")
    ))

    # (5) Linha Vermelha (Simulação) começa em check_start
    #     Precisamos realinhar a partir do valor do cenário base no check_start
    df_base_before_check = df_base_acum[df_base_acum["Data"] < check_start]
    if not df_base_before_check.empty:
        base_cutoff_gmv = df_base_before_check["GMV_acumulado"].max()
    else:
        base_cutoff_gmv = 0

    # Filtra a simulação somente a partir de check_start
    df_sim_check = df_sim_acum[df_sim_acum["Data"] >= check_start].copy()

    if len(rotas_canceladas) == 0:
        # (5.1) Caso não haja cancelamentos, a linha vermelha deve coincidir com a azul
        #       (ou seja, não haverá desvio).
        #       Portanto, definimos "GMV_acumulado_alinhado" = GMV_acumulado base
        #       para que a linha vermelha seja idêntica à linha azul.
        if not df_sim_check.empty:
            # Precisamos saber o acumulado do base no check_start 
            # E também alinhar com a parte futura.
            # df_sim_check = basicamente = df_base_future, 
            # mas vamos garantir o realinhamento idêntico.
            df_sim_check["GMV_acumulado_alinhado"] = df_sim_check["GMV_acumulado"]
        else:
            df_sim_check["GMV_acumulado_alinhado"] = df_sim_check["GMV_acumulado"]
    else:
        # (5.2) Se há cancelamentos, realinha do primeiro valor a base_cutoff_gmv
        if not df_sim_check.empty:
            primeiro_valor_sim = df_sim_check.iloc[0]["GMV_acumulado"]
            df_sim_check["GMV_acumulado_alinhado"] = base_cutoff_gmv + (df_sim_check["GMV_acumulado"] - primeiro_valor_sim)
        else:
            df_sim_check["GMV_acumulado_alinhado"] = df_sim_check["GMV_acumulado"]

    # Plot da linha de simulação (Canceladas), começando no check_start
    fig.add_trace(go.Scatter(
        x=df_sim_check["Data"],
        y=df_sim_check["GMV_acumulado_alinhado"],
        mode="lines",
        name="Simulação (Canceladas)",
        line=dict(color="red", width=3)
    ))

    # (6) Diferença Acumulada (somente datas >= check_start)
    df_diff_check = df_diff[df_diff["Data"] >= check_start].copy()
    if not df_diff_check.empty and not df_sim_check.empty:
        # Precisamos mesclar para ter "GMV_acumulado_alinhado"
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

    # Layout e hover
    fig.update_layout(
        title="GMV Acumulado - Base vs. Simulação",
        xaxis_title="Data",
        yaxis_title="GMV Acumulado",
        hovermode="x unified"
    )
    for trace in fig.data:
        trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"

    return fig


def plot_cash_acumulado(
    df_base_acum, df_sim_acum, df_diff, df_baseline_meta,
    check_start, check_end, hoje_dt, rotas_canceladas
):
    """
    Gráfico de Cash Acumulado com as mesmas regras do GMV:
      - Azul sólido até hoje, azul tracejado até check_start,
      - Vermelho começa em check_start (zero cancelamento => coincide com azul),
      - Baseline histórico e meta diluída exibidos,
      - Faixa cinza e linha vertical "Hoje".
    """

    fig = go.Figure()
    fig.update_xaxes(type="date")

    # Faixa cinza do check
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
        xref="x", yref="paper",
        showarrow=False,
        text="Período do check de cancelamento",
        font=dict(color="gray", size=12)
    )

    # Linha vertical hoje
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

    # Baseline Histórico Acumulado (Cash) e Meta Hist. Diluída (Cash)
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

    # Linha azul: passado sólido, futuro tracejado
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

    # Linha vermelha (Simulação) inicia no check_start
    df_base_before_check = df_base_acum[df_base_acum["Data"] < check_start]
    if not df_base_before_check.empty:
        base_cutoff_cash = df_base_before_check["Cash_acumulado"].max()
    else:
        base_cutoff_cash = 0

    df_sim_check = df_sim_acum[df_sim_acum["Data"] >= check_start].copy()

    if len(rotas_canceladas) == 0:
        # Sem cancelamento => mesma linha que a azul
        if not df_sim_check.empty:
            df_sim_check["Cash_acumulado_alinhado"] = df_sim_check["Cash_acumulado"]
        else:
            df_sim_check["Cash_acumulado_alinhado"] = df_sim_check["Cash_acumulado"]
    else:
        # Com cancelamento => realinha
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

    # Diferença Acumulada (Cash), a partir de check_start
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

    for trace in fig.data:
        trace.hovertemplate = f"{trace.name}: "+"%{y:.2f}"+"<extra></extra>"

    return fig

