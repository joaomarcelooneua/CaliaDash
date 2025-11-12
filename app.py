from __future__ import annotations

import base64
import re
import unicodedata
from pathlib import Path
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# Visual identity constants (aligned with Calia deck)
# -----------------------------------------------------------------------------
PRIMARY = "#FF9100"
SECONDARY = "#FFC65A"
DARK_BG = "#232323"
CARD_BG = "#2B2B2B"
CARD_ALT = "#1E1E1E"
TEXT_LIGHT = "#F8F8F8"
TEXT_MUTED = "#CBCBCB"

DATA_PATH = Path("data") / "valores.xlsx"
LOGO_PATH = Path("assets") / "calia-logo.svg"
MAC_REFERENCE_DEPRECIATION = 2145
LICENSE_REFERENCE_DEPRECIATION = 1200
LOW_COST_THRESHOLD = 800


# -----------------------------------------------------------------------------
# Data helpers
# -----------------------------------------------------------------------------
def _normalize_column(column: str) -> str:
    """Normalize Excel column names to snake_case ascii."""
    base = (
        unicodedata.normalize("NFKD", column)
        .encode("ascii", "ignore")
        .decode("ascii")
        .replace("\n", " ")
        .strip()
        .lower()
    )
    base = re.sub(r"[^0-9a-z ]+", " ", base)
    return "_".join(base.split())


@st.cache_data(show_spinner=False)
def load_inventory(path: Path) -> pd.DataFrame:
    ...

def load_inventory(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df.rename(columns={col: _normalize_column(col) for col in df.columns})

    rename_map = {
        "nome": "nome",
        "status": "status",
        "grupo": "grupo",
        "usuario": "usuario",
        "numero_de_inventario": "numero_inventario",
        "tipo_do_item": "tipo_item",
        "categoria": "categoria",
        "valor_medio_unitario": "valor_unitario",
        "depreciacao_anual_mercado": "perc_depreciacao",
        "vida_util_anos_mercado": "vida_util_anos",
        "depreciacao_anual_unitaria_r": "depreciacao_unitaria",
    }
    df = df.rename(columns=rename_map)

    df["valor_unitario"] = df["valor_unitario"].astype(float)
    df["depreciacao_unitaria"] = df["depreciacao_unitaria"].astype(float)
    df["categoria"] = df["categoria"].str.strip()
    df["numero_inventario"] = (
        df["numero_inventario"].fillna("Sem inventário").astype(str).str.strip()
    )
    df["usuario"] = df["usuario"].fillna("").astype(str).str.strip()

    df["is_mac"] = df["nome"].str.contains("mac", case=False, na=False)
    df["is_license"] = df["tipo_item"].str.contains("licenca", case=False, na=False)
    df["is_low_cost"] = df["valor_unitario"] <= LOW_COST_THRESHOLD
    df["tem_usuario"] = df["usuario"].str.len() > 0
    df["tem_inventario"] = ~df["numero_inventario"].str.contains("sem", case=False, na=False)
    df["rastreados"] = df["tem_usuario"] & df["tem_inventario"]

    df["dep_referencia"] = df["depreciacao_unitaria"]
    df.loc[df["is_mac"], "dep_referencia"] = MAC_REFERENCE_DEPRECIATION
    df.loc[df["is_license"], "dep_referencia"] = LICENSE_REFERENCE_DEPRECIATION

    def classify_priority(row: pd.Series) -> str:
        if row["is_mac"] or row["is_license"]:
            return "Premium controlado"
        if row["tipo_item"].lower() in {"computador", "telefone", "monitor", "impressora"}:
            return "Essencial"
        return "Não essencial"

    df["prioridade"] = df.apply(classify_priority, axis=1)
    return df


DATA_PATH = Path(__file__).parent / "data" / "valores.xlsx"

@st.cache_data(show_spinner=False)
def load_inventory(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Arquivo {path} não encontrado. Suba valores.xlsx na pasta data/ do repositório.")
        st.stop()
    return pd.read_excel(path)



def compute_insights(df: pd.DataFrame) -> Dict[str, float]:
    total_items = len(df) or 1
    total_dep = (
        df.get("Depreciação anual unitária (R$)")
        or df.get("Depreciacao anual_% (mercado)")
        or pd.Series([0]*len(df))
        ).sum(
    )

    patr_total = df["valor_unitario"].sum()
    avg_dep = total_dep / total_items

    mac_mask = df["is_mac"]
    lic_mask = df["is_license"]
    low_mask = df["is_low_cost"]
    tracked_mask = df["rastreados"]

    status_counts = df["status"].value_counts()
    sem_uso = int(status_counts.get("Sem Uso", 0))

    centros = df.groupby("grupo")["valor_unitario"].sum().sort_values(ascending=False)
    centros_total = centros.sum() or 1
    top_centros = centros.head(2)

    return {
        "total_dep": total_dep,
        "patrimonio_total": patr_total,
        "avg_dep": avg_dep,
        "mac_dep": df.loc[mac_mask, "dep_referencia"].sum(),
        "license_dep": df.loc[lic_mask, "dep_referencia"].sum(),
        "mac_count": int(mac_mask.sum()),
        "license_count": int(lic_mask.sum()),
        "tracked_pct": tracked_mask.mean() * 100,
        "tracked_count": int(tracked_mask.sum()),
        "low_cost_dep": df.loc[low_mask, "dep_referencia"].sum(),
        "low_cost_count": int(low_mask.sum()),
        "low_cost_pct": low_mask.mean() * 100,
        "sem_uso_pct": sem_uso / total_items * 100,
        "sem_uso_count": sem_uso,
        "centros": centros.reset_index(name="valor_unitario"),
        "top_centros_share": (top_centros.sum() / centros_total * 100) if not top_centros.empty else 0,
        "top_centros_names": ", ".join(top_centros.index.tolist()),
        "total_items": len(df),
    }


# -----------------------------------------------------------------------------
# Styling helpers
# -----------------------------------------------------------------------------
def style_streamlit():
    st.set_page_config(
        page_title="Calia | Inventário inteligente",
        page_icon="??",
        layout="wide",
    )
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Sans:wght@500;600&display=swap');
        :root {{
            --primary: {PRIMARY};
            --secondary: {SECONDARY};
            --bg: {DARK_BG};
            --card: {CARD_BG};
            --text: {TEXT_LIGHT};
            --muted: {TEXT_MUTED};
        }}
        body {{ background-color: var(--bg); color: var(--text); }}
        [data-testid="stAppViewContainer"] > div {{ background-color: var(--bg); color: var(--text); }}
        h1, h2, h3, h4, h5, h6 {{ font-family: 'IBM Plex Sans', sans-serif; color: var(--text); }}
        p, li, span {{ font-family: 'Inter', sans-serif; }}
        .hero {{
            background: linear-gradient(90deg, #1c1c1c 0%, #2d2d2d 100%);
            border-radius: 24px;
            padding: 2rem 2.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid #3a3a3a;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .calia-logo-img {{
            width: 140px;
            height: auto;
            display: block;
            margin-bottom: 0.6rem;
        }}
        .section-card {{
            background: var(--card);
            padding: 1.6rem;
            border-radius: 22px;
            border: 1px solid #3d3d3d;
            margin-bottom: 1.2rem;
        }}
        .metric-grid {{ display: flex; gap: 1rem; flex-wrap: wrap; }}
        .metric-grid .metric {{
            flex: 1;
            min-width: 200px;
            background: #2f2f2f;
            padding: 1.1rem 1.4rem;
            border-radius: 18px;
            border: 1px solid #3a3a3a;
        }}
        .metric-label {{ text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.7rem; color: var(--muted); }}
        .metric-value {{ font-size: 1.8rem; font-weight: 600; color: var(--primary); }}
        .metric-subtext {{ color: var(--muted); font-size: 0.85rem; }}
        .fade-card {{
            animation: fadeIn 1.4s ease;
            background: {CARD_ALT};
            border-radius: 16px;
            padding: 1.2rem 1.5rem;
            border: 1px solid #3d3d3d;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(12px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .footer {{
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #3d3d3d;
            color: var(--muted);
            font-size: 0.9rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_block(label: str, value: str, subtext: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtext">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_priority_filter(df: pd.DataFrame, selection: str) -> pd.DataFrame:
    if selection == "Inventário completo" or selection not in df["prioridade"].unique():
        return df
    return df[df["prioridade"] == selection]


# -----------------------------------------------------------------------------
# Charts
# -----------------------------------------------------------------------------
def premium_vs_rest_chart(df: pd.DataFrame) -> px.bar:
    mac_dep = df.loc[df["is_mac"], "dep_referencia"].sum()
    lic_dep = df.loc[df["is_license"], "dep_referencia"].sum()
    total = df["dep_referencia"].sum()
    other = max(total - (mac_dep + lic_dep), 0)
    data = pd.DataFrame(
        {
            "Segmento": ["Macs premium", "Licenças críticas", "Demais ativos"],
            "Depreciação anual": [mac_dep, lic_dep, other],
        }
    )
    fig = px.bar(
        data,
        x="Depreciação anual",
        y="Segmento",
        orientation="h",
        text_auto=".0f",
        color="Segmento",
        color_discrete_sequence=[PRIMARY, SECONDARY, "#7c7c7c"],
    )
    fig.update_layout(
        bargap=0.25,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_LIGHT,
        showlegend=False,
    )
    return fig


def category_depreciation_chart(df: pd.DataFrame) -> px.bar:
    cat = (
        df.groupby("categoria")
        .agg(dep_total=("dep_referencia", "sum"), itens=("nome", "count"))
        .assign(dep_media=lambda d: d["dep_total"] / d["itens"])
        .sort_values("dep_media", ascending=False)
        .head(8)
        .reset_index()
    )
    fig = px.bar(
        cat,
        x="dep_media",
        y="categoria",
        orientation="h",
        text_auto=".0f",
        color="dep_total",
        color_continuous_scale=["#5f5f5f", PRIMARY],
        labels={"dep_media": "Depreciação média anual (R$)", "categoria": "Categoria"},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_LIGHT,
        coloraxis_showscale=False,
    )
    return fig


def tracking_ratio_chart(df: pd.DataFrame) -> px.pie:
    tracked = int(df["rastreados"].sum())
    pending = max(len(df) - tracked, 0)
    if len(df) == 0:
        data = pd.DataFrame({"Status": ["Sem dados"], "Itens": [1]})
        color_map = {"Sem dados": "#5c5c5c"}
    else:
        data = pd.DataFrame(
            {"Status": ["Rastreabilidade completa", "Pendências"], "Itens": [tracked, pending]}
        )
        color_map = {
            "Rastreabilidade completa": PRIMARY,
            "Pendências": "#555555",
        }
    fig = px.pie(
        data,
        names="Status",
        values="Itens",
        hole=0.55,
        color="Status",
        color_discrete_map=color_map,
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_LIGHT,
        showlegend=True,
    )
    return fig


def centro_custo_chart(df: pd.DataFrame) -> px.bar:
    centros = (
        df.groupby("grupo")["valor_unitario"].sum().sort_values(ascending=False).head(6).reset_index()
        if not df.empty
        else pd.DataFrame({"grupo": [], "valor_unitario": []})
    )
    fig = px.bar(
        centros,
        x="valor_unitario",
        y="grupo",
        orientation="h",
        text_auto=".0f",
        color="valor_unitario",
        color_continuous_scale=["#5c5c5c", PRIMARY],
        labels={"valor_unitario": "Valor imobilizado (R$)", "grupo": "Centro de custo"},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_LIGHT,
        coloraxis_showscale=False,
    )
    return fig


def status_distribution_chart(df: pd.DataFrame) -> px.bar:
    pivot = (
        df.groupby(["tipo_item", "status"])
        .size()
        .reset_index(name="itens")
        .sort_values("itens", ascending=False)
    )
    fig = px.bar(
        pivot,
        x="itens",
        y="tipo_item",
        color="status",
        orientation="h",
        color_discrete_map={
            "Em uso": PRIMARY,
            "Sem Uso": "#6b6b6b",
            "Novo": SECONDARY,
        },
        text_auto=True,
        labels={"tipo_item": "Tipo de item", "itens": "Quantidade"},
    )
    fig.update_layout(
        barmode="stack",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_LIGHT,
        legend_title="Status",
    )
    return fig


def pequenos_itens_chart(df: pd.DataFrame) -> px.scatter:
    top_small = (
        df[df["is_low_cost"]]
        .groupby("nome")
        .agg(itens=("nome", "count"), dep=("dep_referencia", "sum"))
        .sort_values("itens", ascending=False)
        .head(10)
        .reset_index()
    )
    if top_small.empty:
        top_small = pd.DataFrame({"dep": [], "nome": [], "itens": []})
    fig = px.scatter(
        top_small,
        x="dep",
        y="nome",
        size="itens" if not top_small.empty else None,
        color="itens" if not top_small.empty else None,
        color_continuous_scale=[SECONDARY, PRIMARY],
        labels={"dep": "Depreciação anual (R$)", "nome": "Item", "itens": "Qtd."},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=TEXT_LIGHT,
        coloraxis_showscale=False,
    )
    return fig


# -----------------------------------------------------------------------------
# Layout sections
# -----------------------------------------------------------------------------
import base64
import streamlit as st
from pathlib import Path

# Caminho do arquivo SVG
LOGO_PATH = Path("assets/calia-logo.svg")

def load_logo_asset(path: Path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    except FileNotFoundError:
        return None

def render_header():
    logo_data = load_logo_asset(LOGO_PATH)
    if logo_data:
        logo_html = (
            f'<img src="data:image/svg+xml;base64,{logo_data}" '
            'alt="Calia logo" style="height:42px; margin-bottom:0.4rem;" />'
        )
    else:
        logo_html = '<div class="calia-logo">calia<span>°</span></div>'

    st.markdown(
        f"""
        <div class="hero" style="display:flex; justify-content:space-between; align-items:flex-start; gap:2rem;">
            <div>
                {logo_html}
                <p style="color:#d0d0d0; margin-bottom:0.2rem;">Projeto de programação estruturada · Calia Y2</p>
                <h2 style="margin:0;">Inventário inteligente para racionalizar ativos sem perder performance.</h2>
            </div>
            <div style="text-align:right; max-width:360px; color:#d0d0d0;">
                <p>Este dashboard traduz o diagnóstico da AP2</p> </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_inventory_numbers(kpis: Dict[str, float]):
    st.markdown("#### Inventário em números")
    cols = st.columns(3)
    with cols[0]:
        metric_block("Patrimônio total", f"R$ {kpis['patrimonio_total']:,.0f}")
    with cols[1]:
        metric_block("Depreciação média anual", f"R$ {kpis['avg_dep']:,.0f}")
    with cols[2]:
        metric_block(
            "Itens rastreáveis",
            f"{kpis['tracked_pct']:.1f}%",
            f"{kpis['tracked_count']} ativos com dono + código",
        )


def section_high_value(df: pd.DataFrame, view_kpis: Dict[str, float]):
    st.markdown("### 1 · Equipamentos de alto valor concentram o orçamento")
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.plotly_chart(premium_vs_rest_chart(df), use_container_width=True)
    with col2:
        st.plotly_chart(category_depreciation_chart(df), use_container_width=True)

    mac_share = (view_kpis["mac_dep"] / view_kpis["total_dep"] * 100) if view_kpis["total_dep"] else 0
    lic_share = (view_kpis["license_dep"] / view_kpis["total_dep"] * 100) if view_kpis["total_dep"] else 0

    st.markdown(
        f"""
        <div class="fade-card" style="margin-top:0.5rem;">
            <h4 style="color:{PRIMARY}; margin-top:0;">Leitura estratégica</h4>
            <p>Mesmo com políticas pontuais, Macs e licenças críticas seguem ditando o ritmo da depreciação:
            <strong>{mac_share:.1f}%</strong> do total anual vem dos Macs e <strong>{lic_share:.1f}%</strong> das licenças premium.
            Padronizar quando cada exceção é autorizada garante previsibilidade orçamentária.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_rastreabilidade(df: pd.DataFrame, view_kpis: Dict[str, float]):
    st.markdown("### 2 · Rastreabilidade cria disciplina e evita reposições desnecessárias")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(tracking_ratio_chart(df), use_container_width=True)
    with col2:
        st.plotly_chart(centro_custo_chart(df), use_container_width=True)

    st.markdown(
        f"""
        <div class="fade-card">
            <p><strong>{view_kpis['tracked_pct']:.1f}%</strong> dos itens exibidos possuem dono e número de inventário.
            Ao conectar isso a centro de custo, conseguimos responsabilizar quem decide e quem usa.</p>
            <p>Os centros <strong>{view_kpis['top_centros_names'] or 'principais'}</strong> concentram
            <strong>{view_kpis['top_centros_share']:.1f}%</strong> do valor imobilizado — justificativa direta para
a implantação de QR Codes e checagens periódicas.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_operacao(df: pd.DataFrame, view_kpis: Dict[str, float]):
    st.markdown("### 3 · Eficiência operacional e o impacto dos pequenos itens")
    col1, col2 = st.columns([1.2, 0.8])
    with col1:
        st.plotly_chart(status_distribution_chart(df), use_container_width=True)
    with col2:
        st.plotly_chart(pequenos_itens_chart(df), use_container_width=True)

    st.markdown(
        f"""
        <div class="section-card">
            <p><strong>{view_kpis['sem_uso_pct']:.1f}%</strong> dos ativos estão ociosos. Antes de qualquer compra, o plano é
            realocar e liberar estoques; só depois abrir exceção.</p>
            <p>Itens abaixo de R$ {LOW_COST_THRESHOLD:,.0f} representam <strong>{view_kpis['low_cost_pct']:.1f}%</strong> do park
            e consomem R$ {view_kpis['low_cost_dep']:,.0f}/ano em depreciação. São pequenos, mas formam uma linha de gasto
difícil de enxergar sem consolidar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        """
        <div class="footer">
            Projeto de análise de dados da matéria de Programação Estruturada · Calia Y2
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Main app
# -----------------------------------------------------------------------------
def render():
    style_streamlit()
    df = load_inventory(DATA_PATH)
    global_kpis = compute_insights(df)

    render_header()
    st.caption("Selecione o recorte que deseja analisar. As visualizações e interpretações abaixo se ajustam automaticamente.")

    selection = st.radio(
        "Filtro por prioridade",
        ["Inventário completo", "Premium controlado", "Essencial", "Não essencial"],
        horizontal=True,
    )
    filtered_df = apply_priority_filter(df, selection)
    view_kpis = compute_insights(filtered_df)

    st.caption(
        f"Mostrando {len(filtered_df)} itens considerando a categoria '{selection}'."
    )

    render_inventory_numbers(global_kpis)
    section_high_value(filtered_df, view_kpis)
    section_rastreabilidade(filtered_df, view_kpis)
    section_operacao(filtered_df, view_kpis)

    with st.expander("Prévia dos dados (50 primeiros registros)"):
        st.dataframe(filtered_df.head(50), use_container_width=True)

    render_footer()


if __name__ == "__main__":
    render()





