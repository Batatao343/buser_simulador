# simulation.py
import numpy as np
import pandas as pd
from datetime import datetime

def definir_valores(df, cutoff):
    df["GMV_valor"] = np.where(df["Data"] < cutoff, df["GMV_realizado"], df["GMV_baseline"])
    df["Cash_valor"] = np.where(df["Data"] < cutoff, df["Cash_realizado"], df["Cash_baseline"])
    return df

def transformar_em_acumulado(df, col_gmv, col_cash):
    df_sorted = df.sort_values("Data").copy()
    df_sorted["GMV_acumulado"] = df_sorted[col_gmv].cumsum()
    df_sorted["Cash_acumulado"] = df_sorted[col_cash].cumsum()
    return df_sorted

def calcular_meta_diluida(df_agg, meta_gmv, meta_cash):
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
    
    df_agg = df_agg.sort_values("Data").copy()
    df_agg["GMV_meta_acumulada"] = df_agg["GMV_meta_diluida"].cumsum()
    df_agg["Cash_meta_acumulada"] = df_agg["Cash_meta_diluida"].cumsum()
    return df_agg

def calcular_baseline_meta_acumulada(df):
    total_gmv = df["GMV_baseline"].sum()
    total_cash = df["Cash_baseline"].sum()
    meta_gmv = 600000  # Exemplo fixo ou pode ser passado como argumento
    meta_cash = 300000
    if total_gmv == 0:
        df["GMV_meta_diluida"] = 0
    else:
        df["Peso_GMV"] = df["GMV_baseline"] / total_gmv
        df["GMV_meta_diluida"] = meta_gmv * df["Peso_GMV"]

    if total_cash == 0:
        df["Cash_meta_diluida"] = 0
    else:
        df["Peso_Cash"] = df["Cash_baseline"] / total_cash
        df["Cash_meta_diluida"] = meta_cash * df["Peso_Cash"]

    df = df.sort_values("Data").copy()
    df["GMV_baseline_acumulado"] = df["GMV_baseline"].cumsum()
    df["Cash_baseline_acumulado"] = df["Cash_baseline"].cumsum()
    df["GMV_meta_acumulada"] = df["GMV_meta_diluida"].cumsum()
    df["Cash_meta_acumulada"] = df["Cash_meta_diluida"].cumsum()
    return df
