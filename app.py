from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Horta Automatizada", page_icon="🌱", layout="wide")

# ---------- Configuração ----------
AUTOR = "Igor"
REPO = "igorgilmore/dashboard-irrigacao"
CSV_URL = f"https://raw.githubusercontent.com/{REPO}/main/base_irriga%C3%A7%C3%A3o.csv"
CSV_LOCAL = Path("base_irrigação.csv")
IMG = Path("imagens")
FONTE_DADOS = "Base de teste gerada pelo script `gerar_base_teste.py`, no formato enviado pelo Arduino UNO."
ADC_SECO, ADC_MOLHADO = 620, 260
LIMIAR, TEMPO_BOMBA, INTERVALO_MIN = 40, 2, 20
SALTO_P_P, LACUNA_MIN = 25, 40
VERDE, CIANO, AMBAR, ROSA, ROXO = "#3DDC84", "#4DD0E1", "#FFB300", "#FF5C8A", "#B388FF"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Poppins', sans-serif !important; letter-spacing: -0.5px; }
h1 { background: linear-gradient(90deg, #3DDC84, #4DD0E1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
[data-testid="stMetric"] { background: #14281E; border: 1px solid #21402F; border-left: 4px solid #3DDC84; border-radius: 12px; padding: 14px 16px; }
[data-testid="stMetricValue"] { font-family: 'Poppins', sans-serif; }
[data-testid="stMetricLabel"] { color: #9CCFB0; }
.stTabs [data-baseweb="tab"] { font-weight: 600; font-size: 1.02rem; }
.card { background: #14281E; border: 1px solid #21402F; border-radius: 14px; padding: 18px 20px; height: 100%; }
.card h4 { margin: 0 0 8px 0; color: #3DDC84; font-family: 'Poppins', sans-serif; }
.tag { display: inline-block; background: #1D3A2B; color: #9CF0C0; border-radius: 20px; padding: 3px 12px; margin: 3px 2px; font-size: .85rem; }
</style>""", unsafe_allow_html=True)


# ---------- Dados ----------
@st.cache_data(ttl=300)  # se o CSV mudar no GitHub, o painel atualiza em até 5 min
def carregar_dados():
    try:
        df, origem = pd.read_csv(CSV_URL), "GitHub"
    except Exception:
        if not CSV_LOCAL.exists():
            raise
        df, origem = pd.read_csv(CSV_LOCAL), "arquivo local"
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df = df.sort_values("data_hora").reset_index(drop=True)
    df["ligada"] = df["estado_bomba"].eq("Ligada")
    df["dia"] = df["data_hora"].dt.normalize()
    df["dia_txt"] = df["dia"].dt.strftime("%d/%m")
    df["hora"] = df["data_hora"].dt.hour
    df["gap_min"] = df["data_hora"].diff().dt.total_seconds() / 60
    df["dif"] = df["umidade_percentual"].diff()
    df["salto"] = df["dif"].abs()
    df["media_movel"] = df["umidade_percentual"].rolling(18, min_periods=1).mean()  # 6 h
    return df, origem


try:
    df, origem = carregar_dados()
except Exception as e:
    st.error(f"Não foi possível carregar o CSV: {e}")
    st.stop()

U = df["umidade_percentual"]
periodo = f"{df['data_hora'].min():%d/%m/%Y} a {df['data_hora'].max():%d/%m/%Y}"
lig = df[df["ligada"]]
por_dia = df.groupby("dia")["ligada"].sum()
h = df.groupby("hora").agg(umid=("umidade_percentual", "mean"), ac=("ligada", "sum")).reindex(range(24), fill_value=0)


def estilo(fig, titulo, altura=380):
    fig.update_layout(template="plotly_dark", title=titulo, height=altura,
                      colorway=[VERDE, CIANO, AMBAR, ROSA, ROXO],
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter", color="#E8F5E9"),
                      margin=dict(l=10, r=10, t=55, b=10), legend=dict(orientation="h", y=-0.2))
    return fig


def card(titulo, corpo):
    st.markdown(f'<div class="card"><h4>{titulo}</h4>{corpo}</div>', unsafe_allow_html=True)


def resumo(s):
    q1, q3 = s.quantile(.25), s.quantile(.75)
    return {"Observações": s.count(), "Média": s.mean(), "Mediana": s.median(),
            "Desvio padrão": s.std(), "Variância": s.var(), "Mínimo": s.min(), "1º quartil": q1,
            "3º quartil": q3, "Máximo": s.max(), "Amplitude interquartil": q3 - q1,
            "Coef. de variação (%)": s.std() / s.mean() * 100,
            "Assimetria": s.skew(), "Curtose": s.kurt()}


# ---------- Navegação ----------
secao = st.sidebar.radio("Navegação", ["Projeto", "Coleta dos dados", "Armazenamento", "Análise dos resultados"])
st.sidebar.markdown("---")
st.sidebar.caption(f"Autor: {AUTOR}")
st.sidebar.caption(f"Dados lidos de: {origem}")
st.sidebar.caption(f"github.com/{REPO}")

# ============ 1. PROJETO ============
if secao == "Projeto":
    st.title("🌱 Horta Automatizada")
    st.markdown("##### Irrigação automática com Arduino, banco PostgreSQL e análise estatística em Python")
    k = st.columns(4)
    k[0].metric("Leituras analisadas", len(df))
    k[1].metric("Período", f"{df['data_hora'].min():%d/%m} a {df['data_hora'].max():%d/%m}")
    k[2].metric("Limiar de irrigação", f"{LIMIAR}%")
    k[3].metric("Acionamentos da bomba", len(lig))
    st.write("")
    a, b, c = st.columns(3)
    with a:
        card("Problema", "Regar a horta na hora certa, sem depender de alguém lembrar e sem desperdiçar água.")
    with b:
        card("Solução", f"Um sensor mede a umidade do solo. Abaixo de <b>{LIMIAR}%</b>, o Arduino liga a válvula "
                        f"solenoide por <b>{TEMPO_BOMBA} s</b>. Cada leitura é enviada ao computador, gravada no "
                        "PostgreSQL e analisada.")
    with c:
        tags = ["Arduino (C++)", "Python", "PostgreSQL", "Pandas", "Plotly", "Streamlit", "psycopg2", "pySerial"]
        card("Tecnologias", "".join(f'<span class="tag">{t}</span>' for t in tags))

    st.markdown("### Arquitetura do sistema")
    st.graphviz_chart('''
    digraph G { rankdir=LR; bgcolor="transparent";
      node [shape=box, style="rounded,filled", fillcolor="#14281E", color="#3DDC84", fontcolor="#E8F5E9", fontname="Helvetica"];
      edge [color="#9CCFB0", fontcolor="#9CCFB0", fontname="Helvetica", fontsize=10];
      Sensor [label="Sensor de umidade\\ndo solo"]; Arduino [label="Arduino UNO"]; Rele [label="Relé 5 V"];
      Valvula [label="Válvula solenoide\\n12 V"]; Coletor [label="coletor.py"];
      Banco [label="PostgreSQL\\n(tabela leituras)"]; Painel [label="Análise e painel\\nStreamlit"];
      Sensor -> Arduino [label="ADC"]; Arduino -> Rele [label="umidade < 40%"]; Rele -> Valvula [label="2 s"];
      Arduino -> Coletor [label="serial / USB"]; Coletor -> Banco [label="INSERT"]; Banco -> Painel [label="dados"];
    }''', width="stretch")

    st.markdown("### Componentes e montagem")
    e, f = st.columns([1, 2])
    with e:
        card("Hardware", "• Arduino UNO<br>• Sensor de umidade do solo capacitivo<br>• Módulo relé de 5 V<br>"
                         "• Válvula solenoide de 12 V<br>• Display LCD 16x2 com potenciômetro<br>• Protoboard e jumpers")
    with f:
        fotos = [IMG / "montagem_1.jpg", IMG / "montagem_2.jpg"]
        if all(p.exists() for p in fotos):
            f1, f2 = st.columns(2)
            f1.image(str(fotos[0]), caption="Circuito: Arduino, relé, válvula e display")
            f2.image(str(fotos[1]), caption="Sensor no copo e leitura no LCD")

# ============ 2. COLETA ============
elif secao == "Coleta dos dados":
    st.title("🔎 Coleta dos dados")
    esperado = int((df["data_hora"].max() - df["data_hora"].min()).total_seconds() / 60 / INTERVALO_MIN) + 1
    k = st.columns(4)
    k[0].metric("Leituras", len(df))
    k[1].metric("Período", f"{df['data_hora'].min():%d/%m} a {df['data_hora'].max():%d/%m}")
    k[2].metric("Intervalo entre leituras", f"{INTERVALO_MIN} min")
    k[3].metric("Completude da coleta", f"{len(df) / esperado:.1%}")
    st.caption(f"Fonte dos dados: {FONTE_DADOS}")

    a, b = st.columns(2)
    with a:
        st.markdown("#### Do sensor ao percentual de umidade")
        fig = go.Figure(go.Scatter(x=[ADC_MOLHADO, ADC_SECO], y=[100, 0], mode="lines+markers+text",
                                   text=["molhado", "seco"], textposition="top center",
                                   line=dict(color=VERDE, width=3), marker=dict(size=11)))
        fig.update_layout(xaxis_title="Valor ADC (0 a 1023)", yaxis_title="Umidade (%)")
        st.plotly_chart(estilo(fig, "Calibração linear do sensor", 300), width="stretch")
        st.code(f"umidade = (adc - {ADC_SECO}) * 100 / ({ADC_MOLHADO} - {ADC_SECO})   # limitada de 0 a 100",
                language="python")
    with b:
        st.markdown("#### Comunicação serial (9600 baud)")
        st.write("O Arduino envia uma linha por leitura: umidade, ADC, tempo da bomba e estado.")
        p = df.iloc[0]
        st.code(f"{p.umidade_percentual},{p.valor_adc},{p.tempo_bomba_segundos},{p.estado_bomba}", language="text")
        st.markdown("#### Script coletor (`coletor.py`)")
        st.code("arduino = serial.Serial(PORTA, 9600)\n"
                "while True:\n"
                "    linha = arduino.readline().decode().strip()\n"
                "    umidade, adc, tempo, estado = linha.split(',')\n"
                "    cur.execute(INSERT_SQL, (datetime.now(), umidade, adc, tempo, estado))\n"
                "    conn.commit()", language="python")

    st.markdown("#### Dicionário de dados")
    st.table(pd.DataFrame({
        "coluna": ["data_hora", "umidade_percentual", "valor_adc", "tempo_bomba_segundos", "estado_bomba"],
        "tipo": ["data e hora", "numérico", "inteiro", "numérico", "categórico"],
        "descrição": ["Momento da leitura", "Umidade do solo em %", "Valor bruto do conversor analógico-digital",
                      "Segundos com a bomba acionada", "Ligada ou Desligada"]}))

# ============ 3. ARMAZENAMENTO ============
elif secao == "Armazenamento":
    st.title("🗄️ Armazenamento no banco de dados")
    t1, t2, t3 = st.tabs(["Estrutura", "Terminal", "Explorar a base"])

    with t1:
        k = st.columns(4)
        k[0].metric("Banco", "PostgreSQL")
        k[1].metric("Tabela", "leituras")
        k[2].metric("Registros", len(df))
        k[3].metric("Colunas", 5)
        a, b = st.columns(2)
        with a:
            st.markdown("#### Estrutura da tabela (tipos ilustrativos)")
            st.code("CREATE TABLE leituras (\n    data_hora            TIMESTAMP,\n    umidade_percentual   REAL,\n"
                    "    valor_adc            INTEGER,\n    tempo_bomba_segundos REAL,\n    estado_bomba         TEXT\n);",
                    language="sql")
            st.markdown("#### Gravação feita pelo `coletor.py`")
            st.code("INSERT INTO leituras\n  (data_hora, umidade_percentual, valor_adc, tempo_bomba_segundos, estado_bomba)\n"
                    "VALUES (%s, %s, %s, %s, %s);", language="sql")
        with b:
            st.markdown("#### Consulta: acionamentos por dia")
            st.code("SELECT DATE(data_hora) AS dia, COUNT(*) AS acionamentos\nFROM leituras\n"
                    "WHERE estado_bomba = 'Ligada'\nGROUP BY dia ORDER BY dia;", language="sql")
            res = por_dia.rename("acionamentos").reset_index()
            res["dia"] = res["dia"].dt.strftime("%d/%m/%Y")
            st.dataframe(res, width="stretch", hide_index=True)
        st.info("O painel lê um arquivo CSV no mesmo formato da tabela, hospedado no GitHub.")

    with t2:
        st.markdown("#### Preparação do ambiente e gravação no banco, direto do terminal")
        passos = [("terminal_1.png", "1. Instalação do pandas e do matplotlib (análise e gráficos)"),
                  ("terminal_2.png", "2. Instalação do driver do PostgreSQL (psycopg2-binary)"),
                  ("terminal_3.png", "3. Teste de conexão com o banco e gravação das leituras na tabela")]
        for arq, legenda in passos:
            if (IMG / arq).exists():
                st.image(str(IMG / arq), caption=legenda)

    with t3:
        f1, f2, f3 = st.columns(3)
        est = f1.multiselect("Estado da bomba", ["Ligada", "Desligada"], default=["Ligada", "Desligada"])
        ur = f2.slider("Umidade (%)", float(U.min()), float(U.max()), (float(U.min()), float(U.max())))
        dias = sorted(df["dia"].dt.date.unique())
        dr = f3.select_slider("Período", options=dias, value=(dias[0], dias[-1]))
        sub = df[df["estado_bomba"].isin(est) & U.between(*ur) & (df["dia"].dt.date >= dr[0])
                 & (df["dia"].dt.date <= dr[1])]
        cols = ["data_hora", "umidade_percentual", "valor_adc", "tempo_bomba_segundos", "estado_bomba"]
        st.caption(f"{len(sub)} de {len(df)} registros")
        st.dataframe(sub[cols], width="stretch", hide_index=True, height=420)
        st.download_button("Baixar seleção (CSV)", sub[cols].to_csv(index=False).encode("utf-8"),
                           "leituras.csv", "text/csv")

# ============ 4. ANÁLISE ============
elif secao == "Análise dos resultados":
    st.title("📈 Análise dos resultados")
    tabs = st.tabs(["Visão geral", "Estatística descritiva", "Eficácia da irrigação", "Qualidade dos dados",
                    "Conclusões"])

    # ----- Visão geral -----
    with tabs[0]:
        k = st.columns(4)
        k[0].metric("Umidade média", f"{U.mean():.1f}%")
        k[1].metric("Umidade mediana", f"{U.median():.1f}%")
        k[2].metric("Desvio padrão", f"{U.std():.1f} p.p.")
        k[3].metric("Umidade mínima", f"{U.min():.1f}%")
        k = st.columns(4)
        k[0].metric("Acionamentos", len(lig))
        k[1].metric("% das leituras com bomba", f"{df['ligada'].mean():.1%}")
        k[2].metric("Tempo total de bomba", f"{df['tempo_bomba_segundos'].sum():.0f} s")
        k[3].metric("Acionamentos por dia (média)", f"{por_dia.mean():.1f}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["data_hora"], y=U, mode="lines", name="Umidade (%)",
                                 line=dict(color=CIANO, width=1.3)))
        fig.add_trace(go.Scatter(x=df["data_hora"], y=df["media_movel"], mode="lines", name="Média móvel (6 h)",
                                 line=dict(color=VERDE, width=3)))
        fig.add_trace(go.Scatter(x=lig["data_hora"], y=lig["umidade_percentual"], mode="markers",
                                 name="Bomba ligada", marker=dict(color=AMBAR, size=9, line=dict(width=1, color="white"))))
        fig.add_hline(y=LIMIAR, line_dash="dash", line_color=ROSA, annotation_text=f"Limiar {LIMIAR}%")
        fig.update_layout(yaxis_title="Umidade (%)")
        st.plotly_chart(estilo(fig, "Umidade do solo ao longo do tempo", 430), width="stretch")

        a, b = st.columns([3, 2])
        with a:
            fig = px.bar(x=por_dia.index.strftime("%d/%m"), y=por_dia.values, text=por_dia.values,
                         labels={"x": "Dia", "y": "Acionamentos"}, color=por_dia.values,
                         color_continuous_scale=["#1D3A2B", AMBAR])
            fig.update_coloraxes(showscale=False)
            fig.update_traces(textposition="outside")
            st.plotly_chart(estilo(fig, "Acionamentos da bomba por dia"), width="stretch")
        with b:
            fig = px.pie(df, names="estado_bomba", hole=0.6, color="estado_bomba",
                         color_discrete_map={"Ligada": AMBAR, "Desligada": "#2A5C42"})
            st.plotly_chart(estilo(fig, "Estado da bomba nas leituras"), width="stretch")

    # ----- Estatística descritiva -----
    with tabs[1]:
        a, b = st.columns([2, 3])
        with a:
            tab = pd.DataFrame({"Umidade (%)": resumo(U), "Valor ADC": resumo(df["valor_adc"])}).round(2)
            st.markdown("#### Medidas-resumo")
            st.dataframe(tab, width="stretch", height=500)
        with b:
            fig = px.histogram(df, x="umidade_percentual", nbins=25, color_discrete_sequence=[CIANO],
                               labels={"umidade_percentual": "Umidade (%)"})
            fig.add_vline(x=U.mean(), line_color=AMBAR, line_dash="dash", annotation_text=f"Média {U.mean():.1f}",
                          annotation_position="top right")
            fig.add_vline(x=U.median(), line_color=VERDE, line_dash="dash", annotation_text=f"Mediana {U.median():.1f}",
                          annotation_position="top left")
            st.plotly_chart(estilo(fig, "Distribuição da umidade: média × mediana", 500), width="stretch")
        a, b = st.columns(2)
        with a:
            fig = px.box(df, x="dia_txt", y="umidade_percentual", points="outliers", color_discrete_sequence=[VERDE],
                         labels={"dia_txt": "Dia", "umidade_percentual": "Umidade (%)"})
            st.plotly_chart(estilo(fig, "Boxplot da umidade por dia"), width="stretch")
        with b:
            fig = px.ecdf(df, x="umidade_percentual", color_discrete_sequence=[ROXO],
                          labels={"umidade_percentual": "Umidade (%)"})
            fig.add_vline(x=LIMIAR, line_dash="dash", line_color=ROSA)
            st.plotly_chart(estilo(fig, "Distribuição acumulada (ECDF)"), width="stretch")
        piv = df.pivot_table(index="hora", columns="dia_txt", values="umidade_percentual", aggfunc="mean")
        fig = px.imshow(piv, aspect="auto", color_continuous_scale="YlGnBu", origin="lower",
                        labels=dict(x="Dia", y="Hora", color="Umidade (%)"))
        st.plotly_chart(estilo(fig, "Mapa de calor: umidade média por hora e dia", 450), width="stretch")
        corr = U.corr(df["valor_adc"])
        st.caption(f"Correlação entre umidade e valor ADC: {corr:.3f}. A umidade é calculada a partir do ADC "
                   "por uma conta linear, por isso a relação é quase perfeita.")

    # ----- Eficácia da irrigação -----
    with tabs[2]:
        apos = df.loc[df["ligada"].shift(fill_value=False), "dif"].dropna()
        seco = df[(~df["ligada"].shift(fill_value=False)) & (df["salto"] <= SALTO_P_P)]
        taxa_h = -seco["dif"].mean() * 60 / INTERVALO_MIN
        interv = lig["data_hora"].diff().dropna().dt.total_seconds() / 3600
        k = st.columns(4)
        k[0].metric("Intervalo médio entre acionamentos", f"{interv.mean():.1f} h")
        k[1].metric("Intervalo mediano", f"{interv.median():.1f} h")
        k[2].metric("Ganho de umidade após acionar", f"{apos.mean():+.1f} p.p.", help="Média da diferença para a leitura seguinte")
        k[3].metric("Queda média sem irrigação", f"{taxa_h:.2f} p.p./h")

        a, b = st.columns(2)
        with a:
            fig = px.histogram(interv, nbins=20, color_discrete_sequence=[AMBAR], labels={"value": "Horas"})
            fig.add_vline(x=interv.mean(), line_dash="dash", line_color=VERDE, annotation_text="Média")
            fig.add_vline(x=interv.median(), line_dash="dot", line_color=CIANO, annotation_text="Mediana",
                          annotation_position="top left")
            fig.update_layout(showlegend=False)
            st.plotly_chart(estilo(fig, "Tempo entre acionamentos consecutivos"), width="stretch")
        with b:
            fig = px.histogram(apos, nbins=20, color_discrete_sequence=[VERDE], labels={"value": "Variação (p.p.)"})
            fig.add_vline(x=apos.mean(), line_dash="dash", line_color=AMBAR, annotation_text="Média")
            fig.update_layout(showlegend=False)
            st.plotly_chart(estilo(fig, "Variação da umidade na leitura seguinte ao acionamento"), width="stretch")

        a, b = st.columns(2)
        with a:
            fig = px.bar_polar(h.reset_index(), r="ac", theta=h.index.astype(str), color="ac",
                               color_continuous_scale=["#1D3A2B", AMBAR])
            fig.update_layout(polar=dict(angularaxis=dict(direction="clockwise", rotation=90)))
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(estilo(fig, "Acionamentos por hora do dia (relógio)", 420), width="stretch")
        with b:
            fig = px.line(h.reset_index(), x="hora", y="umid", markers=True, color_discrete_sequence=[CIANO],
                          labels={"hora": "Hora do dia", "umid": "Umidade média (%)"})
            fig.add_hline(y=LIMIAR, line_dash="dash", line_color=ROSA)
            st.plotly_chart(estilo(fig, "Umidade média por hora do dia", 420), width="stretch")

    # ----- Qualidade -----
    with tabs[3]:
        fora = df[(df["valor_adc"] > ADC_SECO) | (df["valor_adc"] < ADC_MOLHADO)]
        saltos = df[df["salto"] > SALTO_P_P]
        lacunas = df[df["gap_min"] > LACUNA_MIN]
        seq = (df["ligada"] != df["ligada"].shift()).cumsum()
        tam = df[df["ligada"]].groupby(seq).size()
        seq_longas = tam[tam >= 3]
        q1, q3 = U.quantile(.25), U.quantile(.75)
        outl = df[(U < q1 - 1.5 * (q3 - q1)) | (U > q3 + 1.5 * (q3 - q1))]
        k = st.columns(4)
        k[0].metric("Fora da faixa do sensor", len(fora))
        k[1].metric(f"Saltos bruscos (> {SALTO_P_P} p.p.)", len(saltos))
        k[2].metric(f"Lacunas (> {LACUNA_MIN} min)", len(lacunas))
        k[3].metric("Irrigações seguidas (3+)", len(seq_longas))
        k = st.columns(3)
        k[0].metric("Valores nulos", int(df[["umidade_percentual", "valor_adc"]].isna().sum().sum()))
        k[1].metric("Registros duplicados", int(df.duplicated("data_hora").sum()))
        k[2].metric("Outliers (critério 1,5 × IQR)", len(outl))

        a, b = st.columns(2)
        with a:
            dia_top = por_dia.idxmax()
            d = df[df["dia"] == dia_top]
            dl = d[d["ligada"]]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=d["data_hora"], y=d["umidade_percentual"], mode="lines+markers", name="Umidade (%)",
                                     line=dict(color=CIANO)))
            fig.add_trace(go.Scatter(x=dl["data_hora"], y=dl["umidade_percentual"], mode="markers", name="Bomba ligada",
                                     marker=dict(color=AMBAR, size=11)))
            fig.add_hline(y=LIMIAR, line_dash="dash", line_color=ROSA)
            st.plotly_chart(estilo(fig, f"Dia com mais acionamentos: {dia_top:%d/%m}"), width="stretch")
        with b:
            st.markdown("#### Alertas")
            maior = ""
            if df["salto"].notna().any():
                i = df["salto"].idxmax()
                maior = f" Maior: {df.loc[i, 'salto']:.0f} p.p. em {df.loc[i, 'data_hora']:%d/%m %H:%M}."
            st.write(f"1. **Faixa do sensor:** {len(fora)} leituras com ADC fora de {ADC_MOLHADO} a {ADC_SECO}.\n"
                     f"2. **Saltos bruscos:** {len(saltos)} ocorrências.{maior}\n"
                     f"3. **Lacunas de coleta:** {len(lacunas)} intervalos acima de {LACUNA_MIN} min.\n"
                     f"4. **Irrigação sem efeito:** {len(seq_longas)} sequências de 3 ou mais acionamentos"
                     + (f" (maior: {tam.max()})." if len(tam) else ".") + "\n"
                     f"5. **Dia crítico:** {dia_top:%d/%m}, com {int(por_dia.max())} acionamentos.")

    # ----- Conclusões -----
    with tabs[4]:
        forma = "maior que" if U.mean() > U.median() else "menor ou igual à"
        assim = "assimétrica à direita" if U.skew() > 0.5 else ("assimétrica à esquerda" if U.skew() < -0.5 else "aproximadamente simétrica")
        st.markdown("### Principais conclusões")
        st.write(
            f"1. **Funcionamento:** a bomba foi acionada **{len(lig)} vezes** ({df['ligada'].mean():.1%} das leituras), "
            f"sempre com umidade entre **{lig['umidade_percentual'].min():.1f}%** e **{lig['umidade_percentual'].max():.1f}%**, "
            f"somando **{df['tempo_bomba_segundos'].sum():.0f} s**.\n"
            f"2. **Distribuição:** média de **{U.mean():.1f}%**, {forma} a mediana (**{U.median():.1f}%**), com distribuição "
            f"{assim} (assimetria {U.skew():.2f}).\n"
            f"3. **Resposta à irrigação:** a umidade variou em média **{apos.mean():+.1f} p.p.** na leitura seguinte ao "
            f"acionamento, e o intervalo mediano entre acionamentos foi de **{interv.median():.1f} h**.\n"
            f"4. **Padrão horário:** o horário com mais acionamentos foi **{int(h['ac'].idxmax())}h** "
            f"({int(h['ac'].max())}) e o dia com mais irrigações foi **{por_dia.idxmax():%d/%m}** ({int(por_dia.max())}).\n"
            f"5. **Qualidade:** {len(fora)} leituras fora da faixa do sensor, {len(lacunas)} lacunas de coleta e "
            f"{len(saltos)} saltos bruscos."
        )
      st.markdown("### Próximos passos")
st.write(
    "- Manter o `coletor.py` rodando de forma contínua e ampliar o período de análise.\n"
    "- Ler os dados direto do banco no painel.\n"
    "- Ajustar o limiar e o tempo de acionamento com base nos resultados.\n"
    "- Conectividade WiFi para monitoramento remoto.\n"
    "- Múltiplas zonas de segurança."
)
st.caption(f"Período analisado: {periodo}. Fonte dos dados: {FONTE_DADOS}")
