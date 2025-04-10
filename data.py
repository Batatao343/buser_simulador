# data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def gerar_dados():
    # (Conteúdo idêntico à função gerar_dados() do código acima)
    num_rotas = 100
    viagens_por_rota = 5
    start_date = datetime.now().date() - timedelta(days=20)
    end_date = datetime.now().date() + timedelta(days=20)
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    
    dados = []
    for rota in [f"R{i+1}" for i in range(num_rotas)]:
        datas_rota = np.random.choice(date_range, size=viagens_por_rota, replace=False)
        for data in datas_rota:
            gmv_base = np.random.randint(500, 2000)
            cash_base = np.random.randint(-500, 1000)
            gmv_real = gmv_base + np.random.randint(-100, 100)
            cash_real = cash_base + np.random.randint(-50, 50)
            dados.append({
                "Data": data,
                "Rota": rota,
                "GMV_baseline": gmv_base,
                "GMV_realizado": gmv_real,
                "Cash_baseline": cash_base,
                "Cash_realizado": cash_real
            })
    df = pd.DataFrame(dados)
    df["Data"] = pd.to_datetime(df["Data"])
    return df
