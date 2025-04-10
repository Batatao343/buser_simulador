## plotting.py

import plotly.graph_objects as go
import pandas as pd

def plot_gmv_acumulado(
    df_base_acum,    # DF acumulado do cenário base (Realizado/Previsto)
    df_sim_acum,     # DF acumulado do cenário simulado (cancelamentos)
    df_diff,         # Diferença acumulada entre simulação e base
    df_baseline_meta,# DF com baseline histórico acumulado e meta histórica diluída acumulada
    check_start,     # Início do período do check (hoje + 48h)
    check_end,       # Fim do período do check (hoje + 72h)
    hoje_dt,         # Dia de hoje (Timestamp)
    rotas_canceladas = []  # Lista de rotas canceladas (pode estar vazia)
):
    """
    Cria o gráfico de GMV Acumulado com as seguintes regras:
      - Linha azul sólida até hoje (Realizado);
      - Linha azul tracejada de hoje em diante (Previsto);
      - A partir de check_start, a linha de Simulação (vermelha) inicia,
        alinhada ao acumulado base no check_start; se não houver cancelamento,
        ela coincide com a linha azul.
      - Exibe Baseline Histórico (linha cinza) e Meta Histórica Diluída (linha verde);
      - Adiciona uma faixa cinza para o período do check de cancelamento e uma linha vertical em "Hoje".
    Os nomes dos traces seguem o padrão utilizado na função para Cash:
      "Baseline Histórico", "Meta Ajustada", "Realizado", "Previsto",
      "Simulação - Check de cancelamento" e "Diferença Acumulada".
    """

    fig = go.Figure()
    fig.update_xaxes(type="date")

    # Faixa cinza: Período do check de cancelamento [check_start, check_end]
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

    # Linha vertical em "Hoje"
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

    # Baseline Histórico Acumulado (GMV) e Meta Histórica Diluída Acumulada
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_baseline_acumulado"],
        mode="lines",
        name="Baseline Histórico",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["GMV_meta_acumulada"],
        mode="lines",
        name="Meta Ajustada",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))

    # Linha Azul - Realizado/Previsto Acumulado
    # Dividimos em duas partes: "Realizado" (passado) e "Previsto" (futuro)
    df_base_past = df_base_acum[df_base_acum["Data"] < hoje_dt]
    df_base_future = df_base_acum[df_base_acum["Data"] >= hoje_dt]

    fig.add_trace(go.Scatter(
        x=df_base_past["Data"],
        y=df_base_past["GMV_acumulado"],
        mode="lines",
        name="Realizado",
        line=dict(color="#00008B", width=3, dash="solid")
    ))
    fig.add_trace(go.Scatter(
        x=df_base_future["Data"],
        y=df_base_future["GMV_acumulado"],
        mode="lines",
        name="Previsto",
        line=dict(color="#00008B", width=3, dash="dash")
    ))

    # Linha Vermelha (Simulação): deve começar a partir de check_start,
    # alinhando seu primeiro ponto ao valor acumulado do base no momento de check_start.
    df_base_before_check = df_base_acum[df_base_acum["Data"] < check_start]
    if not df_base_before_check.empty:
        base_cutoff_gmv = df_base_before_check["GMV_acumulado"].max()
    else:
        base_cutoff_gmv = 0

    # Filtra a simulação somente para datas >= check_start
    df_sim_check = df_sim_acum[df_sim_acum["Data"] >= check_start].copy()

    if len(rotas_canceladas) == 0:
        # Sem cancelamento: a linha de simulação coincide com a linha azul prevista
        if not df_sim_check.empty:
            df_sim_check["GMV_acumulado_alinhado"] = df_sim_check["GMV_acumulado"]
        else:
            df_sim_check["GMV_acumulado_alinhado"] = df_sim_check["GMV_acumulado"]
    else:
        # Com cancelamento: realinha para iniciar no base_cutoff
        if not df_sim_check.empty:
            primeiro_valor_sim = df_sim_check.iloc[0]["GMV_acumulado"]
            df_sim_check["GMV_acumulado_alinhado"] = base_cutoff_gmv + (df_sim_check["GMV_acumulado"] - primeiro_valor_sim)
        else:
            df_sim_check["GMV_acumulado_alinhado"] = df_sim_check["GMV_acumulado"]

    fig.add_trace(go.Scatter(
        x=df_sim_check["Data"],
        y=df_sim_check["GMV_acumulado_alinhado"],
        mode="lines",
        name="Simulação - Check de cancelamento",
        line=dict(color="red", width=3)
    ))

    # Linha de Diferença Acumulada: a partir de check_start
    df_diff_check = df_diff[df_diff["Data"] >= check_start].copy()
    if not df_diff_check.empty and not df_sim_check.empty:
        df_diff_check = df_diff_check.merge(
            df_sim_check[["Data", "GMV_acumulado_alinhado"]],
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
    check_start, check_end, hoje_dt, rotas_canceladas = []
):
    """
    Cria o gráfico de Cash Acumulado com a mesma lógica de GMV:
      - Linha azul sólida até hoje (Realizado) e azul tracejada para o futuro (Previsto),
      - Linha vermelha (Simulação) iniciando em check_start,
      - Exibe Baseline Histórico e Meta Hist. Diluída acumulados,
      - Faixa cinza e linha vertical "Hoje".
    Os nomes dos traces seguem:
      "Baseline Histórico", "Meta Ajustada", "Realizado", "Previsto",
      "Simulação - Check de cancelamento" e "Diferença Acumulada".
    """
    fig = go.Figure()
    fig.update_xaxes(type="date")

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
        name="Baseline Histórico",
        line=dict(color="gray", dash="dash"),
        opacity=0.7
    ))
    fig.add_trace(go.Scatter(
        x=df_baseline_meta["Data"],
        y=df_baseline_meta["Cash_meta_acumulada"],
        mode="lines",
        name="Meta Ajustada",
        line=dict(color="green", dash="dot"),
        opacity=0.7
    ))

    df_base_past = df_base_acum[df_base_acum["Data"] < hoje_dt]
    df_base_future = df_base_acum[df_base_acum["Data"] >= hoje_dt]
    fig.add_trace(go.Scatter(
        x=df_base_past["Data"],
        y=df_base_past["Cash_acumulado"],
        mode="lines",
        name="Realizado",
        line=dict(color="#00008B", width=3, dash="solid")
    ))
    fig.add_trace(go.Scatter(
        x=df_base_future["Data"],
        y=df_base_future["Cash_acumulado"],
        mode="lines",
        name="Previsto",
        line=dict(color="#00008B", width=3, dash="dash")
    ))

    df_base_before_check = df_base_acum[df_base_acum["Data"] < check_start]
    if not df_base_before_check.empty:
        base_cutoff_cash = df_base_before_check["Cash_acumulado"].max()
    else:
        base_cutoff_cash = 0

    df_sim_check = df_sim_acum[df_sim_acum["Data"] >= check_start].copy()

    if len(rotas_canceladas) == 0:
        if not df_sim_check.empty:
            df_sim_check["Cash_acumulado_alinhado"] = df_sim_check["Cash_acumulado"]
        else:
            df_sim_check["Cash_acumulado_alinhado"] = df_sim_check["Cash_acumulado"]
    else:
        if not df_sim_check.empty:
            primeiro_valor_sim = df_sim_check.iloc[0]["Cash_acumulado"]
            df_sim_check["Cash_acumulado_alinhado"] = base_cutoff_cash + (df_sim_check["Cash_acumulado"] - primeiro_valor_sim)
        else:
            df_sim_check["Cash_acumulado_alinhado"] = df_sim_check["Cash_acumulado"]

    fig.add_trace(go.Scatter(
        x=df_sim_check["Data"],
        y=df_sim_check["Cash_acumulado_alinhado"],
        mode="lines",
        name="Simulação - Check de cancelamento",
        line=dict(color="red", width=3)
    ))

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
