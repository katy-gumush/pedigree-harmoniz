/**
 * Renders an SVG pedigree tree and refocuses on edge click (±2 generations).
 */
(function () {
  var bootstrap = document.getElementById("pedigree-bootstrap");
  var mount = document.getElementById("pedigree-tree-mount");
  var statusEl = document.getElementById("pedigree-tree-status");
  var resetBtn = document.getElementById("pedigree-tree-reset");
  if (!bootstrap || !mount) return;

  var initialGraph = JSON.parse(bootstrap.textContent);
  var currentGraph = initialGraph;
  var EDGE_ANCESTORS = 2;
  var EDGE_DESCENDANTS = 2;

  var NODE_W = 168;
  var NODE_H = 48;
  var GAP_X = 20;
  var ROW_H = 88;
  var MARGIN = 24;

  function groupByGeneration(nodes) {
    var buckets = {};
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var g = n.generation;
      if (!buckets[g]) buckets[g] = [];
      buckets[g].push(n);
    }
    Object.keys(buckets).forEach(function (g) {
      buckets[g].sort(function (a, b) {
        return a.id - b.id;
      });
    });
    return buckets;
  }

  function layout(graph) {
    var buckets = groupByGeneration(graph.nodes);
    var gens = Object.keys(buckets)
      .map(function (x) {
        return parseInt(x, 10);
      })
      .sort(function (a, b) {
        return a - b;
      });
    if (!gens.length) {
      return {
        positions: {},
        width: MARGIN * 2 + NODE_W,
        height: MARGIN * 2 + NODE_H,
        minGen: 0,
      };
    }
    var minGen = gens[0];
    var maxGen = gens[gens.length - 1];
    var maxRow = 0;
    for (var gi = 0; gi < gens.length; gi++) {
      var row = buckets[gens[gi]];
      var rowLen = row.length * NODE_W + (row.length - 1) * GAP_X;
      if (rowLen > maxRow) maxRow = rowLen;
    }
    var width = Math.max(maxRow + MARGIN * 2, 320);
    var rowCount = maxGen - minGen + 1;
    var height = MARGIN * 2 + rowCount * ROW_H;

    var positions = {};
    for (var g = 0; g < gens.length; g++) {
      var gen = gens[g];
      var rowNodes = buckets[gen];
      var rowW = rowNodes.length * NODE_W + (rowNodes.length - 1) * GAP_X;
      var startX = (width - rowW) / 2;
      var y = MARGIN + (gen - minGen) * ROW_H;
      for (var j = 0; j < rowNodes.length; j++) {
        var x = startX + j * (NODE_W + GAP_X);
        positions[rowNodes[j].id] = { x: x, y: y, gen: gen };
      }
    }
    return { positions: positions, width: width, height: height, minGen: minGen };
  }

  function applyNodeTestIds(g, n, graph) {
    if (n.id === graph.focus_id) return;
    if (n.ancestor_list_depth != null) {
      g.setAttribute("data-testid", "pedigree-ancestor");
      g.setAttribute("data-dog-id", String(n.id));
      g.setAttribute("data-depth", String(n.ancestor_list_depth));
    } else if (n.descendant_list_depth != null) {
      g.setAttribute("data-testid", "pedigree-descendant");
      g.setAttribute("data-dog-id", String(n.id));
      g.setAttribute("data-depth", String(n.descendant_list_depth));
    } else {
      g.setAttribute("data-testid", "pedigree-tree-node");
      g.setAttribute("data-dog-id", String(n.id));
    }
  }

  function render(graph) {
    var lay = layout(graph);
    var pos = lay.positions;
    var svgNS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + lay.width + " " + lay.height);
    svg.setAttribute("class", "pedigree-tree-svg");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Pedigree tree");

    var edges = graph.edges || [];
    for (var e = 0; e < edges.length; e++) {
      var edge = edges[e];
      var pa = pos[edge.parent_id];
      var ca = pos[edge.child_id];
      if (!pa || !ca) continue;
      var x1 = pa.x + NODE_W / 2;
      var y1 = pa.y + NODE_H;
      var x2 = ca.x + NODE_W / 2;
      var y2 = ca.y;
      var hit = document.createElementNS(svgNS, "line");
      hit.setAttribute("x1", x1);
      hit.setAttribute("y1", y1);
      hit.setAttribute("x2", x2);
      hit.setAttribute("y2", y2);
      hit.setAttribute("class", "pedigree-edge-hit");
      hit.setAttribute("data-parent-id", String(edge.parent_id));
      hit.setAttribute("data-child-id", String(edge.child_id));
      hit.setAttribute("stroke-width", "18");
      hit.setAttribute("stroke", "transparent");
      svg.appendChild(hit);

      var vis = document.createElementNS(svgNS, "line");
      vis.setAttribute("x1", x1);
      vis.setAttribute("y1", y1);
      vis.setAttribute("x2", x2);
      vis.setAttribute("y2", y2);
      vis.setAttribute("class", "pedigree-edge");
      vis.setAttribute("pointer-events", "none");
      svg.appendChild(vis);
    }

    for (var i = 0; i < graph.nodes.length; i++) {
      var n = graph.nodes[i];
      var p = pos[n.id];
      if (!p) continue;
      var g = document.createElementNS(svgNS, "g");
      g.setAttribute("transform", "translate(" + p.x + "," + p.y + ")");
      applyNodeTestIds(g, n, graph);

      var link = document.createElementNS(svgNS, "a");
      link.setAttribute("href", "/dogs/" + n.id);

      var rect = document.createElementNS(svgNS, "rect");
      rect.setAttribute("width", NODE_W);
      rect.setAttribute("height", NODE_H);
      rect.setAttribute("rx", "6");
      var isFocus = n.id === graph.focus_id;
      rect.setAttribute(
        "class",
        isFocus ? "pedigree-node pedigree-node-focus" : "pedigree-node"
      );
      link.appendChild(rect);

      var title = document.createElementNS(svgNS, "title");
      title.textContent = n.name + " — " + n.breed + " (" + n.sex + ")";
      link.appendChild(title);

      var text = document.createElementNS(svgNS, "text");
      text.setAttribute("x", NODE_W / 2);
      text.setAttribute("y", NODE_H / 2 + 4);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("class", "pedigree-node-label");
      var label = n.name.length > 22 ? n.name.slice(0, 20) + "…" : n.name;
      text.textContent = label;
      link.appendChild(text);

      g.appendChild(link);
      svg.appendChild(g);
    }

    mount.innerHTML = "";
    mount.appendChild(svg);
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  function refocus(childId) {
    setStatus("Loading…");
    var url =
      "/api/dogs/" +
      childId +
      "/pedigree-network?ancestors=" +
      EDGE_ANCESTORS +
      "&descendants=" +
      EDGE_DESCENDANTS;
    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        currentGraph = data;
        render(currentGraph);
        var ia = initialGraph.initial_max_ancestors;
        var id = initialGraph.initial_max_descendants;
        var resetHint =
          ia != null && id != null
            ? " Use Reset to restore the page view (" +
              ia +
              " up, " +
              id +
              " down)."
            : " Use Reset to restore the page view.";
        setStatus(
          "Showing ±" +
            EDGE_ANCESTORS +
            " generations up and ±" +
            EDGE_DESCENDANTS +
            " down from dog #" +
            childId +
            " (child end of the edge)." +
            resetHint
        );
        if (resetBtn) resetBtn.hidden = false;
      })
      .catch(function () {
        setStatus("Could not load neighborhood view.");
      });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      currentGraph = initialGraph;
      render(currentGraph);
      resetBtn.hidden = true;
      setStatus("");
    });
    resetBtn.hidden = true;
  }

  mount.addEventListener("click", function (ev) {
    var hit = ev.target.closest && ev.target.closest(".pedigree-edge-hit");
    if (hit) {
      ev.preventDefault();
      refocus(parseInt(hit.getAttribute("data-child-id"), 10));
    }
  });

  render(initialGraph);
})();
