from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ARQUIVO_PADRAO = Path(__file__).parent / "base_irrigacao_2026.csv"
LIMITE_LACUNA_MIN = 30  # acima disso, considera que o sensor ficou sem enviar dados

# Paleta: água, solo e acionamento da bomba
AGUA = "#8E6BBF"        # lilás: umidade
BOMBA = "#F2B705"       # amarelo: bomba / alerta
SOLO = "#5B8C3E"        # verde folha: apoio
OK = "#4F7942"          # verde escuro
VERDE_CLARO = "#A9C98B"
LILAS_CLARO = "#EFE9F7"
AMARELO_CLARO = "#FBEFB8"
TINTA = "#2D3B2A"

st.set_page_config(page_title="Minha horta", page_icon="🌼", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem;}
      [data-testid="stMetric"] {border-left: 4px solid #F2B705; padding-left: .8rem;}
      [data-testid="stMetricValue"] {font-size: 1.8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Dados
# ----------------------------------------------------------------------------
@st.cache_data
def carregar(fonte) -> pd.DataFrame:
    df = pd.read_csv(fonte, parse_dates=["data_hora"])
    df = df.sort_values("data_hora").reset_index(drop=True)
    df["data"] = df["data_hora"].dt.date
    df["hora"] = df["data_hora"].dt.hour
    df["bomba_on"] = df["estado_bomba"].eq("Ligada")
    df["intervalo_min"] = df["data_hora"].diff().dt.total_seconds() / 60
    # variação da umidade em p.p./hora, só entre leituras seguidas com bomba desligada
    ant_on = df["bomba_on"].shift(fill_value=True)
    ant_um = df["umidade_percentual"].shift()
    valido = (
        ~df["bomba_on"] & ~ant_on & (df["intervalo_min"] <= LIMITE_LACUNA_MIN)
        & df["umidade_percentual"].between(0.01, 99.99) & ant_um.between(0.01, 99.99)
    )
    taxa = (df["umidade_percentual"] - ant_um) / (df["intervalo_min"] / 60)
    df["taxa_pph"] = taxa.where(valido)
    df["periodo_dia"] = pd.cut(
        df["hora"], bins=[-1, 5, 11, 17, 23],
        labels=["Madrugada (0-5h)", "Manhã (6-11h)", "Tarde (12-17h)", "Noite (18-23h)"],
    )
    return df


@st.cache_data
def detectar_eventos(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa leituras consecutivas com a bomba ligada em um único evento de irrigação."""
    novo = (df["bomba_on"] != df["bomba_on"].shift()) | (df["intervalo_min"] > LIMITE_LACUNA_MIN)
    grupo = novo.cumsum()
    linhas = []
    for _, d in df[df["bomba_on"]].groupby(grupo[df["bomba_on"]]):
        i0, i1 = d.index[0], d.index[-1]
        depois = df.loc[i1 + 1, "umidade_percentual"] if i1 + 1 < len(df) else np.nan
        linhas.append(
            {
                "inicio": d["data_hora"].iloc[0],
                "fim": d["data_hora"].iloc[-1],
                "leituras_com_bomba": len(d),
                "segundos_bomba": d["tempo_bomba_segundos"].sum(),
                "umidade_inicial": d["umidade_percentual"].iloc[0],
                "umidade_final": depois,
            }
        )
    ev = pd.DataFrame(linhas)
    if not ev.empty:
        ev["ganho"] = ev["umidade_final"] - ev["umidade_inicial"]
    return ev


def com_lacunas(df: pd.DataFrame) -> pd.DataFrame:
    """Insere NaN nas lacunas para o gráfico de linha não ligar pontos distantes."""
    buracos = df[df["intervalo_min"] > LIMITE_LACUNA_MIN]
    if buracos.empty:
        return df
    vazios = pd.DataFrame(
        {"data_hora": buracos["data_hora"] - pd.Timedelta(minutes=1), "umidade_percentual": np.nan}
    )
    return pd.concat([df, vazios]).sort_values("data_hora")


def estilo(fig, altura=380):
    fig.update_layout(
        height=altura,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(color=TINTA),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,.2)")
    return fig


# ----------------------------------------------------------------------------
# Barra lateral
# ----------------------------------------------------------------------------
st.sidebar.header("Filtros")

fonte = ARQUIVO_PADRAO if ARQUIVO_PADRAO.exists() else None
enviado = st.sidebar.file_uploader("Trocar a base (CSV)", type="csv")
if enviado is not None:
    fonte = enviado
if fonte is None:
    st.warning("Coloque o arquivo `base_irrigacao_2026.csv` na pasta do app ou envie um CSV na barra lateral.")
    st.stop()

base = carregar(fonte)
eventos_todos = detectar_eventos(base)

d_min, d_max = base["data"].min(), base["data"].max()
periodo = st.sidebar.date_input("Período", (d_min, d_max), min_value=d_min, max_value=d_max)
if len(periodo) != 2:
    st.info("Selecione a data inicial e a final.")
    st.stop()

horas = st.sidebar.slider("Faixa de horário", 0, 23, (0, 23))
limiar = st.sidebar.slider("Umidade crítica (%)", 5, 60, 30)
so_bomba = st.sidebar.checkbox("Mostrar só leituras com bomba ligada")

df = base[
    (base["data"] >= periodo[0])
    & (base["data"] <= periodo[1])
    & (base["hora"].between(*horas))
]
if so_bomba:
    df = df[df["bomba_on"]]
if df.empty:
    st.warning("Nenhuma leitura com esses filtros.")
    st.stop()

ev = eventos_todos[
    (eventos_todos["inicio"].dt.date >= periodo[0]) & (eventos_todos["inicio"].dt.date <= periodo[1])
] if not eventos_todos.empty else eventos_todos

# ----------------------------------------------------------------------------
# Cabeçalho e KPIs
# ----------------------------------------------------------------------------
st.title("🌼 Horta: umidade do solo e irrigação")
st.caption(
    f"{len(df)} leituras de {df['data_hora'].min():%d/%m/%Y %H:%M} a {df['data_hora'].max():%d/%m/%Y %H:%M}"
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Umidade média", f"{df['umidade_percentual'].mean():.1f}%")
k2.metric("Umidade mínima", f"{df['umidade_percentual'].min():.1f}%")
k3.metric("Acionamentos", f"{int(df['bomba_on'].sum())}")
k4.metric("Tempo de bomba", f"{df['tempo_bomba_segundos'].sum():.0f} s")
k5.metric(f"Tempo abaixo de {limiar}%", f"{(df['umidade_percentual'] < limiar).mean() * 100:.1f}%")

aba1, aba2, aba_est, aba3, aba4, aba5 = st.tabs(
    ["Visão geral", "Padrões", "Estatísticas", "Eficácia da irrigação", "Qualidade dos dados", "Dados"]
)

# ----------------------------------------------------------------------------
# Visão geral
# ----------------------------------------------------------------------------
with aba1:
    st.subheader("Umidade ao longo do tempo")
    linha = com_lacunas(df)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=linha["data_hora"], y=linha["umidade_percentual"], mode="lines",
            name="Umidade (%)", line=dict(color=AGUA, width=2), connectgaps=False,
        )
    )
    on = df[df["bomba_on"]]
    fig.add_trace(
        go.Scatter(
            x=on["data_hora"], y=on["umidade_percentual"], mode="markers",
            name="Bomba ligada", marker=dict(color=BOMBA, size=9, line=dict(color=TINTA, width=1)),
        )
    )
    fig.add_hline(y=limiar, line_dash="dash", line_color=SOLO,
                  annotation_text=f"crítico ({limiar}%)", annotation_position="bottom right")
    fig.update_yaxes(title="Umidade (%)", range=[-3, 103])
    st.plotly_chart(estilo(fig, 420), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Acionamentos por dia")
        por_dia = df.groupby("data")["bomba_on"].sum().reset_index(name="acionamentos")
        fig = px.bar(por_dia, x="data", y="acionamentos", color_discrete_sequence=[BOMBA])
        fig.update_layout(xaxis_title=None, yaxis_title="Leituras com bomba ligada")
        st.plotly_chart(estilo(fig), width="stretch")
    with c2:
        st.subheader("Umidade média e mínima por dia")
        resumo = df.groupby("data")["umidade_percentual"].agg(media="mean", minima="min").reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=resumo["data"], y=resumo["media"], name="Média", marker_color=AGUA))
        fig.add_trace(go.Scatter(x=resumo["data"], y=resumo["minima"], name="Mínima",
                                 mode="lines+markers", line=dict(color=SOLO)))
        fig.update_layout(xaxis_title=None, yaxis_title="Umidade (%)")
        st.plotly_chart(estilo(fig), width="stretch")

# ----------------------------------------------------------------------------
# Padrões
# ----------------------------------------------------------------------------
with aba2:
    st.subheader("Em que horário o solo seca mais?")
    mapa = df.pivot_table(index="hora", columns="data", values="umidade_percentual", aggfunc="mean")
    fig = px.imshow(
        mapa, aspect="auto", origin="lower",
        color_continuous_scale=[[0, BOMBA], [0.5, "#F7F3E3"], [1, AGUA]],
        labels=dict(x="Dia", y="Hora", color="Umidade (%)"),
    )
    st.plotly_chart(estilo(fig, 420), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Umidade média por hora do dia")
        por_hora = df.groupby("hora")["umidade_percentual"].mean().reset_index()
        fig = px.line(por_hora, x="hora", y="umidade_percentual", markers=True,
                      color_discrete_sequence=[AGUA])
        fig.update_layout(xaxis_title="Hora", yaxis_title="Umidade média (%)")
        st.plotly_chart(estilo(fig), width="stretch")
    with c2:
        st.subheader("Distribuição da umidade")
        fig = px.histogram(df, x="umidade_percentual", nbins=25, color_discrete_sequence=[AGUA])
        fig.add_vline(x=limiar, line_dash="dash", line_color=SOLO)
        fig.update_layout(xaxis_title="Umidade (%)", yaxis_title="Leituras")
        st.plotly_chart(estilo(fig), width="stretch")

    st.subheader("Sensor: valor ADC × umidade")
    fig = px.scatter(
        df, x="valor_adc", y="umidade_percentual", color="estado_bomba",
        color_discrete_map={"Ligada": BOMBA, "Desligada": AGUA}, opacity=0.7,
        labels=dict(valor_adc="ADC (bruto)", umidade_percentual="Umidade (%)", estado_bomba="Bomba"),
    )
    st.plotly_chart(estilo(fig), width="stretch")
    st.caption(f"Correlação ADC × umidade: {df['valor_adc'].corr(df['umidade_percentual']):.3f}. "
               "Quanto maior o ADC, mais seco o solo.")

# ----------------------------------------------------------------------------
# Estatísticas
# ----------------------------------------------------------------------------
with aba_est:
    um = df["umidade_percentual"]

    st.subheader("Resumo estatístico")
    def resumo(serie):
        return {
            "Leituras": serie.count(), "Média": serie.mean(), "Mediana": serie.median(),
            "Desvio padrão": serie.std(), "Coef. de variação (%)": serie.std() / serie.mean() * 100,
            "Mínimo": serie.min(), "P5": serie.quantile(.05), "P25": serie.quantile(.25),
            "P75": serie.quantile(.75), "P95": serie.quantile(.95), "Máximo": serie.max(),
            "Assimetria": serie.skew(),
        }
    tabela = pd.DataFrame({"Umidade (%)": resumo(um), "ADC (bruto)": resumo(df["valor_adc"])}).round(2)
    st.dataframe(tabela, width="stretch")
    st.caption("Assimetria negativa indica que a maior parte das leituras está em valores altos de umidade, "
               "com uma cauda de leituras secas.")

    st.subheader("Faixas de umidade")
    faixas = pd.cut(
        um, bins=[-0.01, limiar, 60, 90, 100],
        labels=[f"Crítica (< {limiar}%)", f"Atenção ({limiar}-60%)", "Adequada (60-90%)", "Saturada (> 90%)"],
    )
    fx = faixas.value_counts(normalize=True).sort_index().mul(100).round(1).reset_index()
    fx.columns = ["Faixa", "% das leituras"]
    c1, c2 = st.columns([1, 2])
    with c1:
        st.dataframe(fx, hide_index=True, width="stretch")
    with c2:
        fig = px.bar(fx, x="% das leituras", y="Faixa", orientation="h",
                     color="Faixa", color_discrete_sequence=[BOMBA, VERDE_CLARO, OK, AGUA])
        fig.update_layout(showlegend=False, yaxis_title=None)
        st.plotly_chart(estilo(fig, 260), width="stretch")

    st.subheader("Comparação por período do dia")
    por_periodo = df.groupby("periodo_dia", observed=True).agg(
        leituras=("umidade_percentual", "count"),
        media=("umidade_percentual", "mean"),
        mediana=("umidade_percentual", "median"),
        desvio=("umidade_percentual", "std"),
        pct_critico=("umidade_percentual", lambda x: (x < limiar).mean() * 100),
        acionamentos=("bomba_on", "sum"),
    ).round(2)
    por_periodo.columns = ["Leituras", "Média (%)", "Mediana (%)", "Desvio padrão",
                           f"% abaixo de {limiar}%", "Acionamentos"]
    c1, c2 = st.columns([3, 2])
    with c1:
        st.dataframe(por_periodo, width="stretch")
    with c2:
        fig = px.box(df, x="periodo_dia", y="umidade_percentual", color_discrete_sequence=[AGUA],
                     category_orders={"periodo_dia": list(por_periodo.index)})
        fig.update_layout(xaxis_title=None, yaxis_title="Umidade (%)")
        st.plotly_chart(estilo(fig, 300), width="stretch")

    st.subheader("Velocidade de secagem do solo")
    taxas = df["taxa_pph"].dropna()
    if len(taxas) < 5:
        st.info("Poucas leituras consecutivas sem bomba no filtro atual para calcular a secagem.")
    else:
        secando = taxas[taxas < 0]
        s1, s2, s3 = st.columns(3)
        s1.metric("Secagem média", f"{secando.mean():.1f} p.p./h" if len(secando) else "-")
        s2.metric("Secagem mais rápida (P5)", f"{taxas.quantile(.05):.1f} p.p./h")
        s3.metric("Intervalos analisados", len(taxas))
        fig = px.box(df.dropna(subset=["taxa_pph"]), x="hora", y="taxa_pph", color_discrete_sequence=[SOLO])
        fig.add_hline(y=0, line_color=TINTA, line_width=1)
        fig.update_layout(xaxis_title="Hora do dia", yaxis_title="Variação da umidade (p.p./h)")
        st.plotly_chart(estilo(fig, 340), width="stretch")
        st.caption("Considera só leituras seguidas (até 30 min) com a bomba desligada e sensor fora de 0% e 100%. "
                   "Valores negativos indicam solo secando.")

    st.subheader("Em que umidade a bomba costuma ligar?")
    bins = list(range(0, 101, 10))
    df_b = df.assign(faixa_um=pd.cut(um, bins=bins, include_lowest=True))
    prob = df_b.groupby("faixa_um", observed=True)["bomba_on"].agg(["mean", "count"]).reset_index()
    prob["faixa"] = prob["faixa_um"].astype(str)
    prob["pct"] = (prob["mean"] * 100).round(1)
    fig = px.bar(prob, x="faixa", y="pct", text="count", color_discrete_sequence=[BOMBA])
    fig.update_traces(texttemplate="n=%{text}", textposition="outside")
    fig.update_layout(xaxis_title="Faixa de umidade (%)", yaxis_title="% das leituras com bomba ligada")
    st.plotly_chart(estilo(fig, 340), width="stretch")
    st.caption("Mostra a regra de acionamento na prática: onde a barra sobe, a bomba passa a ligar. "
               "Se houver bomba ligada em faixas altas, vale checar o limiar configurado no equipamento.")

    st.subheader("Correlações")
    cor = pd.DataFrame({
        "Umidade": um, "ADC": df["valor_adc"], "Hora": df["hora"], "Bomba ligada": df["bomba_on"].astype(int),
    }).corr().round(2)
    fig = px.imshow(cor, text_auto=True, zmin=-1, zmax=1,
                    color_continuous_scale=[[0, BOMBA], [0.5, "#FFFFFF"], [1, AGUA]])
    st.plotly_chart(estilo(fig, 380), width="stretch")

    st.subheader("Estatísticas por dia")
    dia = df.groupby("data").agg(
        media=("umidade_percentual", "mean"), desvio=("umidade_percentual", "std"),
        minima=("umidade_percentual", "min"), maxima=("umidade_percentual", "max"),
        pct_critico=("umidade_percentual", lambda x: (x < limiar).mean() * 100),
        acionamentos=("bomba_on", "sum"), segundos=("tempo_bomba_segundos", "sum"),
    ).round(2)
    dia.columns = ["Média (%)", "Desvio padrão", "Mínima (%)", "Máxima (%)",
                   f"% abaixo de {limiar}%", "Acionamentos", "Segundos de bomba"]
    st.dataframe(dia, width="stretch")

# ----------------------------------------------------------------------------
# Eficácia
# ----------------------------------------------------------------------------
with aba3:
    st.markdown(
        "Um **evento** é uma sequência de leituras seguidas com a bomba ligada. "
        "O ganho é a diferença entre a umidade na primeira leitura do evento e na leitura seguinte ao fim dele."
    )
    if ev.empty:
        st.info("Nenhum acionamento no período selecionado.")
    else:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Eventos", len(ev))
        e2.metric("Ganho médio de umidade", f"{ev['ganho'].mean():+.1f} p.p.")
        e3.metric("Duração média", f"{ev['leituras_com_bomba'].mean() * 20:.0f} min")
        e4.metric("Eventos longos (3+ leituras)", int((ev["leituras_com_bomba"] >= 3).sum()))

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Umidade inicial × ganho")
            fig = px.scatter(
                ev, x="umidade_inicial", y="ganho", size="leituras_com_bomba",
                color_discrete_sequence=[AGUA],
                labels=dict(umidade_inicial="Umidade ao ligar (%)", ganho="Ganho (p.p.)",
                            leituras_com_bomba="Leituras com bomba"),
            )
            st.plotly_chart(estilo(fig), width="stretch")
        with c2:
            st.subheader("Duração dos eventos")
            fig = px.histogram(ev, x="leituras_com_bomba", color_discrete_sequence=[BOMBA])
            fig.update_layout(xaxis_title="Leituras seguidas com bomba ligada", yaxis_title="Eventos")
            fig.update_xaxes(dtick=1)
            st.plotly_chart(estilo(fig), width="stretch")

        st.subheader("Eventos de irrigação")
        st.dataframe(
            ev.rename(columns={
                "inicio": "Início", "fim": "Fim", "leituras_com_bomba": "Leituras com bomba",
                "segundos_bomba": "Segundos de bomba", "umidade_inicial": "Umidade inicial (%)",
                "umidade_final": "Umidade depois (%)", "ganho": "Ganho (p.p.)",
            }),
            width="stretch", hide_index=True,
        )
        st.caption("Eventos longos indicam que 2 s por ciclo podem ser pouco, "
                   "ou que o solo estava muito seco quando a bomba ligou.")

# ----------------------------------------------------------------------------
# Qualidade
# ----------------------------------------------------------------------------
with aba4:
    lacunas = df[df["intervalo_min"] > LIMITE_LACUNA_MIN]
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Leituras em 0%", int((df["umidade_percentual"] == 0).sum()))
    q2.metric("Leituras em 100%", int((df["umidade_percentual"] == 100).sum()))
    q3.metric("Lacunas na coleta", len(lacunas))
    q4.metric("Valores ausentes", int(df.isna().sum().sum() - df["intervalo_min"].isna().sum()))

    st.markdown(
        "Leituras em 0% ou 100% costumam indicar sensor saturado ou fora da faixa de calibração."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Lacunas na coleta")
        if lacunas.empty:
            st.success("Nenhuma lacuna acima de 30 minutos no período.")
        else:
            t = lacunas[["data_hora", "intervalo_min"]].copy()
            t["intervalo_min"] = (t["intervalo_min"] / 60).round(2)
            st.dataframe(t.rename(columns={"data_hora": "Retomada em", "intervalo_min": "Horas sem dados"}),
                         width="stretch", hide_index=True)
    with c2:
        st.subheader("Leituras saturadas")
        sat = df[df["umidade_percentual"].isin([0, 100])][["data_hora", "umidade_percentual", "valor_adc"]]
        st.dataframe(sat.rename(columns={"data_hora": "Data/hora", "umidade_percentual": "Umidade (%)",
                                         "valor_adc": "ADC"}),
                     width="stretch", hide_index=True, height=250)

    st.subheader("Intervalo entre leituras (minutos)")
    normal = df[df["intervalo_min"] <= LIMITE_LACUNA_MIN]["intervalo_min"]
    fig = px.histogram(normal, nbins=15, color_discrete_sequence=[SOLO])
    fig.update_layout(xaxis_title="Minutos", yaxis_title="Leituras", showlegend=False)
    st.plotly_chart(estilo(fig, 300), width="stretch")

# ----------------------------------------------------------------------------
# Dados
# ----------------------------------------------------------------------------
with aba5:
    st.dataframe(df.drop(columns=["data", "hora", "bomba_on", "intervalo_min"]),
                 width="stretch", hide_index=True)
    st.download_button(
        "Baixar dados filtrados (CSV)",
        df.drop(columns=["data", "hora", "bomba_on", "intervalo_min"]).to_csv(index=False).encode("utf-8"),
        file_name="irrigacao_filtrado.csv",
        mime="text/csv",
    )
