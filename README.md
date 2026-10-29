# PAC 2 · Visualització de dades

Web amb tres visualitzacions interactives i la memòria breu de cada tècnica:

1. [Circle packing](circle_packing.html) de la població dels 142 països inclosos a Gapminder el 2007.
2. [Dendrograma lineal](dendrogram.html) dels valors de l'IDH dels 19 estats del G20 en sis anys entre 2000 i 2023.
3. [Gràfic de violí](violin_plot.html) del guany de capital positiu segons la categoria racial registrada a la mostra Adult.

La pàgina inicial és [index.html](index.html). Els fitxers HTML, JavaScript i les dades necessàries per consultar les visualitzacions són locals al repositori; un visitant de GitHub Pages no necessita Python ni iniciar sessió.

## Entorn i deploy

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\build.py
.venv\Scripts\python.exe -m http.server 8000
```

Obriu `http://localhost:8000/`. Per tornar a descarregar les fonts originals, executeu `build.py --refresh`. Sense aquesta opció, el generador reutilitza els CSV preparats i manté els resultats publicats.

El generador crea els tres CSV preparats sota `data/`, `assets/circle-data.js` i els gràfics de Plotly sota `figures/`. Mostra el resum numèric al terminal, sense desar-ne una còpia redundant. D3 v7.9.0 està desat a `assets/`; la seva [llicència](assets/D3_LICENSE.txt) l'acompanya. Plotly s'inclou també com a recurs local a `figures/`.

## Fonts i decisions metodològiques

| Visualització | Font | Preparació | Lectura limitada a |
| --- | --- | --- | --- |
| Circle packing | [Gapminder / Plotly Express](https://www.gapminder.org/data/) | Any 2007; continent, país i població; noms en català; correcció del codi duplicat de Corea del Nord | Els 142 països presents a la còpia de Gapminder |
| Dendrograma | [Our World in Data / PNUD](https://ourworldindata.org/grapher/human-development-index) | 19 estats del G20 i anys 2000, 2005, 2010, 2015, 2020 i 2023; distància euclidiana i enllaç mitjà | Semblança segons aquests sis valors d'IDH i aquest mètode |
| Gràfic de violí | [UCI Adult](https://archive.ics.uci.edu/dataset/2/adult) | `capital-gain` i `race`; violins per als guanys positius de quatre categories, caixa i punts per a «Altres» (n=22); taula amb la freqüència de zeros de les cinc categories | Mostra històrica del cens de 1994, sense inferència causal |

## Publicació a GitHub Pages

Al repositori de GitHub, seleccioneu **Settings → Pages → Deploy from a branch → main → /(root)**. Les URL previstes són:

- `https://bertamoyano.github.io/UOC_dataViz_PAC2/`
- `https://bertamoyano.github.io/UOC_dataViz_PAC2/circle_packing.html`
- `https://bertamoyano.github.io/UOC_dataViz_PAC2/dendrogram.html`
- `https://bertamoyano.github.io/UOC_dataViz_PAC2/violin_plot.html`

