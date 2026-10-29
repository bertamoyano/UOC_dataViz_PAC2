/* Empaquetament interactiu de Gapminder amb D3 v7. */
const svg = d3.select("#circle-chart");
const frame = svg.append("g");
const circles = frame.append("g");
const labels = frame.append("g");
const tooltip = document.getElementById("circle-tooltip");
const breadcrumb = document.getElementById("circle-breadcrumb");
const back = document.getElementById("circle-back");
const table = document.getElementById("circle-table-body");
const formatNumber = new Intl.NumberFormat("ca-ES");
const formatPercent = new Intl.NumberFormat("ca-ES", { style: "percent", maximumFractionDigits: 1 });
const width = 720;
let focus;
let view;
let root;
let nodeSelection;
let labelSelection;

function ancestorColor(node) {
  const continent = node.ancestors().find((d) => d.depth === 1);
  return continent?.data.color ?? "#6d8793";
}

function describe(node) {
  const share = node.value / root.value;
  const kind = node.children ? "Total del grup" : "Població del país";
  return `${node.data.name}: ${kind.toLowerCase()} ${formatNumber.format(node.value)} persones (${formatPercent.format(share)} dels països inclosos).`;
}

function zoomTo(v) {
  const k = width / v[2];
  view = v;
  nodeSelection.attr("transform", (d) => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`)
    .attr("r", (d) => d.r * k);
  labelSelection.attr("transform", (d) => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`)
    .style("display", (d) => d.parent === focus && d.r * k >= 26 ? "block" : "none")
    .style("font-size", (d) => `${Math.min(20, Math.max(10, d.r * k / 5))}px`);
}

function zoom(node) {
  focus = node;
  back.disabled = node === root;
  breadcrumb.textContent = node === root ? "Tots els continents" : `Països de Gapminder › ${node.data.name}`;
  tooltip.textContent = describe(node);
  const target = [node.x, node.y, node.r * 2];
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    zoomTo(target);
  } else {
    svg.transition().duration(650).tween("zoom", () => {
      const interpolate = d3.interpolateZoom(view, target);
      return (t) => zoomTo(interpolate(t));
    });
  }
}

function populateTable(data) {
  for (const continent of data.children) {
    for (const country of continent.children) {
      const row = document.createElement("tr");
      for (const value of [country.name, continent.name, formatNumber.format(country.value)]) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      }
      table.appendChild(row);
    }
  }
}

function render(data) {
    root = d3.pack().size([width, width]).padding(4)(
      d3.hierarchy(data).sum((d) => d.value || 0).sort((a, b) => b.value - a.value)
    );
    focus = root;
    svg.attr("viewBox", `${-width / 2} ${-width / 2} ${width} ${width}`);
    nodeSelection = circles.selectAll("circle").data(root.descendants().slice(1)).join("circle")
      .attr("fill", (d) => d.children ? ancestorColor(d) : d3.color(ancestorColor(d)).brighter(1.65).formatHex())
      .attr("fill-opacity", (d) => d.children ? 0.92 : 1)
      .attr("stroke", "white").attr("stroke-width", 1.6)
      .attr("tabindex", (d) => d.children ? 0 : null)
      .attr("role", (d) => d.children ? "button" : "img")
      .attr("aria-label", (d) => describe(d))
      .style("cursor", (d) => d.children ? "pointer" : "default")
      .on("mouseenter focus", (_, d) => { tooltip.textContent = describe(d); })
      .on("click", (event, d) => {
        if (d.children) zoom(d);
        else if (focus === root) zoom(d.parent);
        event.stopPropagation();
      })
      .on("keydown", (event, d) => { if (d.children && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); zoom(d); } });
    labelSelection = labels.selectAll("text").data(root.descendants().slice(1)).join("text")
      .attr("text-anchor", "middle").attr("dy", ".35em").attr("pointer-events", "none")
      .attr("fill", (d) => d.children ? "white" : "#17384a")
      .attr("stroke", (d) => d.children ? "#17384a" : "white")
      .attr("stroke-width", (d) => d.children ? 3 : 2)
      .attr("paint-order", "stroke")
      .attr("font-weight", (d) => d.children ? 700 : 500)
      .text((d) => d.data.name.length > 16 ? `${d.data.name.slice(0, 15)}…` : d.data.name);
    back.addEventListener("click", () => zoom(focus.parent || root));
    svg.on("click", () => zoom(root));
    populateTable(data);
    zoomTo([root.x, root.y, root.r * 2]);
    tooltip.textContent = "Selecciona un continent per ampliar-lo. Passa el cursor per un cercle per veure'n la població.";
}

if (window.CIRCLE_DATA) render(window.CIRCLE_DATA);
else tooltip.textContent = "No s'han pogut carregar les dades del circle packing.";
