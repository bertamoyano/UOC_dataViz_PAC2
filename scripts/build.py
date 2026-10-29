"""Prepara les dades de la PAC 2 i genera els dos gràfics Plotly.

Ús: python scripts/build.py [--refresh]
Sense --refresh reutilitza les dades preparades que acompanyen el lloc web.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from babel import Locale
from plotly.subplots import make_subplots
from scipy.cluster.hierarchy import dendrogram, linkage
from ucimlrepo import fetch_ucirepo
import pycountry


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"
YEARS = [2000, 2005, 2010, 2015, 2020, 2023]
HDI_URL = (
    "https://ourworldindata.org/grapher/human-development-index.csv"
    "?v=1&csvType=full&useColumnShortNames=true"
)
G20 = {
    "ARG": "Argentina", "AUS": "Austràlia", "BRA": "Brasil",
    "CAN": "Canadà", "CHN": "Xina", "FRA": "França",
    "DEU": "Alemanya", "IND": "Índia", "IDN": "Indonèsia",
    "ITA": "Itàlia", "JPN": "Japó", "KOR": "Corea del Sud",
    "MEX": "Mèxic", "RUS": "Rússia", "SAU": "Aràbia Saudita",
    "ZAF": "Sud-àfrica", "TUR": "Turquia", "GBR": "Regne Unit",
    "USA": "Estats Units",
}
CONTINENTS = {
    "Africa": "Àfrica", "Americas": "Amèrica", "Asia": "Àsia",
    "Europe": "Europa", "Oceania": "Oceania",
}
COLORS = {
    "Àfrica": "#b85b4a", "Amèrica": "#3c7fa4", "Àsia": "#937249",
    "Europa": "#6d65a6", "Oceania": "#3d917b",
}
INCOME_LABELS = {
    "<=50K": "Fins a 50.000 USD/any",
    ">50K": "Més de 50.000 USD/any",
}


def save_csv(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(DATA / name, index=False, encoding="utf-8")


def prepare_hdi(refresh: bool) -> pd.DataFrame:
    path = DATA / "dendrogram.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path).rename(columns={str(year): year for year in YEARS})
    response = requests.get(HDI_URL, timeout=60, headers={"User-Agent": "UOC PAC2 data visualization/1.0"})
    response.raise_for_status()
    source = pd.read_csv(io.BytesIO(response.content))
    source.columns = [str(col).lower() for col in source.columns]
    required = {"entity", "code", "year"}
    if not required.issubset(source.columns):
        raise ValueError(f"Columnes inesperades d'OWID: {list(source.columns)}")
    measures = [col for col in source.columns if col.startswith("hdi")]
    if len(measures) != 1:
        raise ValueError(f"S'esperava una mesura d'IDH: {measures}")
    metric = measures[0]
    source = source[source["code"].isin(G20) & source["year"].isin(YEARS)].copy()
    source[metric] = pd.to_numeric(source[metric], errors="coerce")
    wide = source.pivot(index="code", columns="year", values=metric).reindex(index=list(G20), columns=YEARS)
    valid = wide.notna().all(axis=1)
    excluded = wide.index[~valid].tolist()
    if excluded:
        print(f"IDH: països sense els sis anys, exclosos: {', '.join(excluded)}")
    wide = wide[valid]
    if len(wide) < 3:
        raise ValueError("L'IDH disponible no permet construir un dendrograma.")
    if not np.isfinite(wide.to_numpy(dtype=float)).all():
        raise ValueError("L'IDH conté valors no finits.")
    frame = wide.reset_index()
    frame.insert(0, "pais", frame["code"].map(G20))
    save_csv(frame, path.name)
    return frame


def country_ca(code: str, original: str) -> str:
    country = pycountry.countries.get(alpha_3=code)
    if country is None:
        return original
    return str(Locale.parse("ca").territories.get(country.alpha_2, original))


def prepare_circle(refresh: bool) -> pd.DataFrame:
    path = DATA / "circle.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    source = px.data.gapminder().query("year == 2007").copy()
    frame = source[["continent", "country", "iso_alpha", "pop"]].copy()
    # La còpia Gapminder de Plotly etiqueta les dues Corees com a KOR.
    frame.loc[frame["country"] == "Korea, Dem. Rep.", "iso_alpha"] = "PRK"
    frame.columns = ["continent", "pais", "code", "poblacio"]
    frame["continent"] = frame["continent"].map(CONTINENTS)
    frame["pais"] = [country_ca(code, name) for code, name in zip(frame["code"], frame["pais"])]
    if frame["continent"].isna().any() or frame["poblacio"].isna().any():
        raise ValueError("Gapminder conté un continent o una població buits.")
    if (frame["poblacio"] <= 0).any() or frame["code"].duplicated().any():
        raise ValueError("Gapminder conté poblacions no positives o països duplicats.")
    frame["poblacio"] = frame["poblacio"].astype(int)
    save_csv(frame, path.name)
    return frame


def prepare_violin(refresh: bool) -> pd.DataFrame:
    path = DATA / "violin.csv"
    if path.exists() and not refresh:
        cached = pd.read_csv(path)
        if {"edat", "ingressos"}.issubset(cached.columns):
            return cached
    adult = fetch_ucirepo(id=2)
    ages = pd.to_numeric(adult.data.features["age"], errors="coerce")
    income = adult.data.targets["income"].astype(str).str.strip().str.rstrip(".")
    frame = pd.DataFrame({"edat": ages, "ingressos": income})
    if frame.isna().any().any() or (frame["edat"] < 0).any():
        raise ValueError("Adult conté edats absents o invàlides.")
    if set(frame["ingressos"]) != set(INCOME_LABELS):
        raise ValueError(f"Categories d'ingressos inesperades: {sorted(frame['ingressos'].unique())}")
    frame["edat"] = frame["edat"].astype(int)
    save_csv(frame, path.name)
    return frame


def build_circle(frame: pd.DataFrame) -> dict:
    total = int(frame["poblacio"].sum())
    children = []
    group_totals = frame.groupby("continent")["poblacio"].sum().sort_values(ascending=False)
    for continent, group_total in group_totals.items():
        rows = frame[frame["continent"] == continent].sort_values("poblacio", ascending=False)
        leaves = [
            {"name": row.pais, "code": row.code, "value": int(row.poblacio)}
            for row in rows.itertuples(index=False)
        ]
        children.append({"name": continent, "total": int(group_total), "color": COLORS[continent], "children": leaves})
    hierarchy = {"name": "Països de Gapminder", "total": total, "children": children}
    (ROOT / "assets" / "circle-data.js").write_text(
        "window.CIRCLE_DATA = " + json.dumps(hierarchy, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    top = frame.sort_values("poblacio", ascending=False).iloc[0]
    return {
        "paisos": len(frame), "continents": len(children), "total": total,
        "continent_major": str(group_totals.index[0]),
        "continent_major_poblacio": int(group_totals.iloc[0]),
        "pais_major": str(top["pais"]), "pais_major_poblacio": int(top["poblacio"]),
    }


def build_dendrogram(frame: pd.DataFrame) -> dict:
    matrix = frame[YEARS].to_numpy(dtype=float)
    names = frame["pais"].tolist()
    tree = linkage(matrix, method="average", metric="euclidean", optimal_ordering=True)
    dend = dendrogram(tree, no_plot=True)
    leaves = dend["leaves"]
    positions = [5 + 10 * i for i in range(len(leaves))]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.59, 0.41], horizontal_spacing=0.045)
    for xs, ys in zip(dend["dcoord"], dend["icoord"]):
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line={"color": "#376980", "width": 2}, hoverinfo="skip", showlegend=False), row=1, col=1)
    arranged = matrix[leaves, :]
    ordered_names = [names[i] for i in leaves]
    fig.add_trace(
        go.Heatmap(
            x=YEARS, y=positions, z=arranged, zmin=0, zmax=1,
            customdata=[[name] * len(YEARS) for name in ordered_names],
            colorscale=[[0, "#edf4f1"], [0.5, "#86b8ad"], [1, "#174e69"]],
            colorbar={"title": "IDH", "len": 0.75, "thickness": 13},
            hovertemplate="<b>%{customdata}</b><br>Any %{x}: IDH %{z:.3f}<extra></extra>",
        ), row=1, col=2,
    )
    fig.update_yaxes(tickmode="array", tickvals=positions, ticktext=ordered_names, showgrid=False, range=[0, len(leaves) * 10], row=1, col=1)
    fig.update_yaxes(showticklabels=False, showgrid=False, row=1, col=2)
    fig.update_xaxes(title_text="Dissimilitud (distància euclidiana mitjana)", rangemode="tozero", showgrid=True, gridcolor="#e1e9eb", row=1, col=1)
    fig.update_xaxes(title_text="Any", tickmode="array", tickvals=YEARS, tickangle=-45, row=1, col=2)
    fig.update_layout(
        title={"text": "Trajectòries de l’IDH dels estats del G20", "x": 0.5},
        paper_bgcolor="white", plot_bgcolor="white", font={"family": "Arial, sans-serif", "size": 13, "color": "#193a4a"},
        margin={"l": 145, "r": 55, "t": 85, "b": 90}, height=650,
        hoverlabel={"bgcolor": "white", "font_size": 13},
    )
    fig.write_html(FIGURES / "dendrogram.html", include_plotlyjs="directory", full_html=True, config={"displayModeBar": False, "responsive": True})
    first_a, first_b, first_distance = tree[0, 0], tree[0, 1], tree[0, 2]
    top_2023 = frame.sort_values(2023, ascending=False).iloc[0]
    low_2023 = frame.sort_values(2023).iloc[0]
    return {
        "paisos": len(frame), "exclosos": [G20[code] for code in G20 if code not in frame["code"].tolist()],
        "parella_propera": [names[int(first_a)], names[int(first_b)]],
        "distancia_parella": round(float(first_distance), 4),
        "idh_alt_2023": {"pais": str(top_2023["pais"]), "valor": float(top_2023[2023])},
        "idh_baix_2023": {"pais": str(low_2023["pais"]), "valor": float(low_2023[2023])},
    }


def build_violin(frame: pd.DataFrame) -> dict:
    groups = {}
    for category in INCOME_LABELS:
        values = frame.loc[frame["ingressos"] == category, "edat"]
        groups[category] = {
            "n": len(values),
            "percentatge": round(100 * len(values) / len(frame), 2),
            "mediana": float(values.median()),
            "q1": float(values.quantile(0.25)),
            "q3": float(values.quantile(0.75)),
        }
    order = sorted(INCOME_LABELS, key=lambda category: -groups[category]["mediana"])
    fig = go.Figure()
    display_names = {}
    for category in order:
        values = frame.loc[frame["ingressos"] == category, "edat"].to_numpy()
        display_name = f"{INCOME_LABELS[category]}<br>n={len(values):,}".replace(",", ".")
        display_names[category] = display_name
        fig.add_trace(go.Violin(
            y=values, x0=display_name, name=INCOME_LABELS[category],
            box_visible=True, meanline_visible=False, points=False,
            fillcolor="#4b83a2", line_color="#27647f", opacity=0.78,
            scalemode="width", hoveron="violins",
            hovertemplate="Edat: %{y:.0f} anys<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(
        title={"text": "Distribució de l’edat segons els ingressos anuals", "x": 0.5},
        yaxis={"title": {"text": "Edat (anys)", "standoff": 12}, "range": [15, 92], "dtick": 10,
               "gridcolor": "#e1e9eb", "zeroline": False},
        xaxis={"title": {"text": "Ingressos anuals", "standoff": 18}, "showgrid": False,
               "categoryorder": "array", "categoryarray": [display_names[category] for category in order]},
        paper_bgcolor="white", plot_bgcolor="white",
        font={"family": "Arial, sans-serif", "size": 14, "color": "#193a4a"},
        margin={"l": 75, "r": 25, "t": 85, "b": 115}, height=620,
        showlegend=False, violinmode="group", hoverlabel={"bgcolor": "white"},
    )
    fig.write_html(FIGURES / "violin_plot.html", include_plotlyjs="directory", full_html=True,
                   config={"displayModeBar": False, "responsive": True})
    return {"total": len(frame), "grups": {category: groups[category] for category in order}, "ordre": order}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Torna a descarregar les dades originals.")
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    hdi = prepare_hdi(args.refresh)
    circle = prepare_circle(args.refresh)
    violin = prepare_violin(args.refresh)
    summary = {
        "dendrograma": build_dendrogram(hdi),
        "circle_packing": build_circle(circle),
        "violi": build_violin(violin),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
