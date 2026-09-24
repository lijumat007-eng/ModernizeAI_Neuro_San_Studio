# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Interactive HTML Knowledge Graph Visualizer.
Generates an executive-grade, color-coded, physics-tuned, interactive HTML network view.
Equipped with neighborhood isolation, search & auto-zoom, hierarchical layout,
edge label decluttering, test-class filtering, and postMessage integration for parent UI.
"""

import json
import os
from typing import Any
from typing import Dict
from typing import List

import networkx as nx


class GraphVisualizer:
    """
    Renders the Knowledge Graph into an interactive, highly responsive HTML visualization.
    """

    COLOR_PALETTE = {
        "Application": "#3b82f6",  # Royal Blue
        "Service": "#10b981",  # Emerald
        "Module": "#06b6d4",  # Cyan
        "APIEndpoint": "#8b5cf6",  # Purple
        "DatabaseTable": "#f59e0b",  # Amber / Gold
        "Column": "#a855f7",  # Violet
        "StoredProcedure": "#14b8a6",  # Teal
        "BusinessRule": "#ec4899",  # Pink / Magenta
        "RequirementDocument": "#f97316",  # Orange
        "SMEInsight": "#f43f5e",  # Rose
        "Risk": "#ef4444",  # Crimson Red
    }

    EDGE_COLORS = {
        "CALLS": "#10b981",
        "DEPENDS_ON": "#64748b",
        "READS_FROM": "#38bdf8",
        "WRITES_TO": "#f43f5e",
        "IMPLEMENTS_RULE": "#ec4899",
        "DEFINED_IN": "#8b5cf6",
        "IMPACTS": "#ef4444",
        "VALIDATES": "#14b8a6",
    }

    @staticmethod
    def is_test_node(node_id: str, data: dict) -> bool:
        nid = node_id.lower()
        sf = str(data.get("source_file", "")).lower()
        return "test" in nid or "test" in sf or nid.endswith("tests") or "test" in str(data.get("label", "")).lower()

    @staticmethod
    def get_node_level(node_id: str, node_type: str) -> int:
        nid = node_id.lower()
        if node_type == "Application":
            return 0
        if "controller" in nid or "endpoint" in nid or "resource" in nid or node_type == "APIEndpoint":
            return 1
        if node_type == "Service" or "service" in nid:
            return 2
        if node_type in ("BusinessRule", "Risk") or "rule" in nid or "validator" in nid:
            return 2
        if "repository" in nid or "dao" in nid or node_type == "Module":
            return 3
        if node_type == "StoredProcedure":
            return 4
        if node_type in ("DatabaseTable", "Column"):
            return 5
        return 3

    @classmethod
    def render_html(
        cls,
        graph: nx.MultiDiGraph,
        output_path: str = "artifacts/modernize_graph.html",
        height: str = "100%",
        width: str = "100%",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        abs_out = os.path.abspath(output_path)

        # Detect application root node to soften hub edges
        app_nodes = {
            n for n, d in graph.nodes(data=True) if d.get("node_type") == "Application" or "application" in n.lower()
        }

        nodes_list: List[Dict[str, Any]] = []
        for node_id, data in graph.nodes(data=True):
            node_type = data.get("node_type", "Module")
            base_color = cls.COLOR_PALETTE.get(node_type, "#94a3b8")
            src = data.get("source_file", "N/A")
            l_start = data.get("line_start", 1)
            l_end = data.get("line_end", 1)
            snippet = str(data.get("evidence_snippet", "")).replace('"', "&quot;").replace("'", "&#39;")
            tooltip = f"[{node_type}] {node_id}\nFile: {src}:{l_start}-{l_end}\n\nSnippet: {snippet[:150]}..."

            is_test = cls.is_test_node(node_id, data)
            level = cls.get_node_level(node_id, node_type)

            size = 30 if node_type == "Application" else (24 if node_type in ("Service", "DatabaseTable") else 18)

            label = data.get("label", node_id)
            # Shorten label for clean canvas presentation
            clean_label = label.replace("Class: ", "").replace("Table: ", "").replace("Procedure: ", "")

            nodes_list.append(
                {
                    "id": node_id,
                    "label": clean_label,
                    "title": tooltip,
                    "color": {
                        "background": base_color,
                        "border": "#ffffff" if node_type == "Application" else base_color,
                        "highlight": {
                            "background": base_color,
                            "border": "#38bdf8",
                        },
                    },
                    "shape": "dot"
                    if node_type not in ("DatabaseTable", "Application")
                    else ("database" if node_type == "DatabaseTable" else "hexagon"),
                    "size": size,
                    "node_type": node_type,
                    "source_file": src,
                    "line_start": l_start,
                    "line_end": l_end,
                    "is_test": is_test,
                    "level": level,
                    "original_color": base_color,
                    "original_size": size,
                    "font": {
                        "color": "#f8fafc",
                        "size": 12,
                        "face": "Inter, system-ui, sans-serif",
                    },
                }
            )

        edges_list: List[Dict[str, Any]] = []
        edge_id_counter = 0
        for u, v, key, data in graph.edges(keys=True, data=True):
            edge_id_counter += 1
            edge_type = data.get("edge_type", key)
            base_color = cls.EDGE_COLORS.get(edge_type, "#64748b")
            src_file = data.get("source_file", "")
            edge_title = f"{u} ➔ [{edge_type}] ➔ {v}"
            if src_file:
                edge_title += f"\nFile: {src_file}:{data.get('line_start', 1)}"

            # Detect star-spoke hub edge from root app node
            is_hub = u in app_nodes

            edges_list.append(
                {
                    "id": f"e_{edge_id_counter}",
                    "from": u,
                    "to": v,
                    "edgeType": edge_type,
                    "title": edge_title,
                    # Edges do not display static labels by default to prevent visual collisions!
                    "label": "",
                    "color": {
                        "color": "rgba(100, 116, 139, 0.22)" if is_hub else base_color,
                        "highlight": "#38bdf8",
                        "hover": "#38bdf8",
                        "opacity": 0.3 if is_hub else 0.85,
                    },
                    "arrows": {
                        "to": {
                            "enabled": not is_hub,
                            "scaleFactor": 0.75,
                        }
                    },
                    "dashes": is_hub,
                    "width": 0.8 if is_hub else (2.2 if edge_type in ("WRITES_TO", "CALLS") else 1.4),
                    # Hub edges have physics=False so they don't drag all nodes into a tight black hole
                    "physics": not is_hub,
                    "is_hub": is_hub,
                    "original_color": base_color,
                    "font": {
                        "color": "#f8fafc",
                        "size": 10,
                        "align": "middle",
                        "background": "#0f172a",
                    },
                }
            )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ModernizeAI Knowledge Fabric Explorer</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link
    href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600;700&display=swap"
    rel="stylesheet">
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      background: #090d16;
      color: #f8fafc;
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
    }}
    #network-canvas {{
      width: 100vw;
      height: 100vh;
      background: radial-gradient(circle at center, #0f172a 0%, #080c14 100%);
    }}

    /* Top Floating Glassmorphic Control Bar */
    .control-dock {{
      position: absolute;
      top: 14px;
      left: 14px;
      right: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      pointer-events: none;
      z-index: 100;
    }}
    .dock-group {{
      display: flex;
      align-items: center;
      gap: 8px;
      pointer-events: auto;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(51, 65, 85, 0.6);
      border-radius: 10px;
      padding: 6px 10px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }}

    /* Search Component Input */
    .search-wrapper {{
      position: relative;
    }}
    .search-input {{
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid #334155;
      color: #f8fafc;
      border-radius: 6px;
      padding: 6px 12px 6px 30px;
      font-size: 12px;
      width: 240px;
      outline: none;
      transition: all 0.2s;
    }}
    .search-input:focus {{
      border-color: #38bdf8;
      width: 280px;
      background: rgba(30, 41, 59, 0.95);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    }}
    .search-icon {{
      position: absolute;
      left: 9px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 12px;
      color: #94a3b8;
      pointer-events: none;
    }}
    .search-dropdown {{
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      margin-top: 4px;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 6px;
      max-height: 220px;
      overflow-y: auto;
      display: none;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      z-index: 200;
    }}
    .search-dropdown.active {{
      display: block;
    }}
    .search-item {{
      padding: 7px 12px;
      font-size: 11px;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      border-bottom: 1px solid rgba(51, 65, 85, 0.4);
    }}
    .search-item:hover {{
      background: #1e293b;
      color: #38bdf8;
    }}
    .search-badge {{
      font-size: 9px;
      padding: 2px 6px;
      border-radius: 4px;
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
    }}

    /* Buttons */
    .ctrl-btn {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid #334155;
      color: #cbd5e1;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease-in-out;
    }}
    .ctrl-btn:hover {{
      background: #334155;
      color: #ffffff;
      border-color: #64748b;
    }}
    .ctrl-btn.active {{
      background: rgba(56, 189, 248, 0.2);
      border-color: #38bdf8;
      color: #38bdf8;
    }}

    /* Stats & Legend */
    .stats-pill {{
      font-size: 11px;
      color: #94a3b8;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .stats-val {{
      color: #f8fafc;
      font-weight: 600;
    }}

    /* Help Overlay bottom right */
    .help-tooltip {{
      position: absolute;
      bottom: 14px;
      right: 14px;
      background: rgba(15, 23, 42, 0.8);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(51, 65, 85, 0.5);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 11px;
      color: #64748b;
      pointer-events: none;
    }}
    .help-tooltip strong {{
      color: #38bdf8;
    }}
  </style>
</head>
<body>

  <!-- Floating Dock Controls -->
  <div class="control-dock">
    <div class="dock-group">
      <!-- Search Input -->
      <div class="search-wrapper">
        <span class="search-icon">🔍</span>
        <input type="text" id="search-input" class="search-input"
               placeholder="Search class or table..." autocomplete="off" />
        <div id="search-dropdown" class="search-dropdown"></div>
      </div>

      <!-- Quick Toggles -->
      <button class="ctrl-btn" id="btn-toggle-tests" title="Toggle Test Classes">
        <span>🧪 Hide Tests</span>
      </button>
      <button class="ctrl-btn" id="btn-layout" title="Switch between Organic and Tiered Architecture">
        <span>📐 Hierarchical</span>
      </button>
      <button class="ctrl-btn" id="btn-freeze" title="Freeze or resume real-time physics">
        <span>❄️ Freeze</span>
      </button>
      <button class="ctrl-btn" id="btn-fit" title="Reset View and Fit All Nodes">
        <span>🎯 Fit View</span>
      </button>
    </div>

    <div class="dock-group">
      <div class="stats-pill">
        <span>Nodes: <span class="stats-val" id="count-nodes">{len(nodes_list)}</span></span>
        <span>•</span>
        <span>Edges: <span class="stats-val" id="count-edges">{len(edges_list)}</span></span>
      </div>
    </div>
  </div>

  <div id="network-canvas"></div>

  <div class="help-tooltip">
    💡 Click any node to <strong>isolate neighborhood</strong> & trigger <strong>Inspector</strong>
  </div>

  <script>
    var rawNodes = {json.dumps(nodes_list)};
    var rawEdges = {json.dumps(edges_list)};

    var nodes = new vis.DataSet(rawNodes);
    var edges = new vis.DataSet(rawEdges);

    var container = document.getElementById('network-canvas');
    var data = {{ nodes: nodes, edges: edges }};

    var isHierarchical = false;
    var isFrozen = false;
    var hideTests = false;
    var activeSelection = null;

    var forceOptions = {{
      nodes: {{
        borderWidth: 2,
        borderWidthSelected: 4,
        shadow: {{ enabled: true, color: 'rgba(0,0,0,0.4)', size: 8 }}
      }},
      edges: {{
        smooth: {{ type: 'continuous', roundness: 0.25 }},
        shadow: false
      }},
      physics: {{
        enabled: true,
        barnesHut: {{
          gravitationalConstant: -14000,
          centralGravity: 0.08,
          springLength: 260,
          springConstant: 0.025,
          damping: 0.18,
          avoidOverlap: 0.75
        }},
        minVelocity: 0.75,
        stabilization: {{
          enabled: true,
          iterations: 140,
          updateInterval: 25,
          fit: true
        }}
      }},
      interaction: {{
        hover: true,
        tooltipDelay: 150,
        navigationButtons: true,
        keyboard: true,
        multiselect: false
      }}
    }};

    var hierarchicalOptions = {{
      layout: {{
        hierarchical: {{
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed',
          nodeSpacing: 190,
          levelSeparation: 140,
          treeSpacing: 200,
          blockShifting: true,
          edgeMinimization: true
        }}
      }},
      physics: {{ enabled: false }}
    }};

    var network = new vis.Network(container, data, forceOptions);

    // Initial fit once stabilized
    network.once("stabilizationIterationsDone", function () {{
      network.fit({{ animation: {{ duration: 500 }} }});
    }});

    // 1. NEIGHBORHOOD ISOLATION (EGO-GRAPH FOCUS) ON NODE SELECT
    network.on("selectNode", function (params) {{
      if (!params.nodes || params.nodes.length === 0) return;
      var selectedId = params.nodes[0];
      activeSelection = selectedId;

      var connectedNodes = network.getConnectedNodes(selectedId);
      var connectedEdges = network.getConnectedEdges(selectedId);
      var connectedSet = new Set(connectedNodes);
      connectedSet.add(selectedId);

      var selectedNodeObj = nodes.get(selectedId);

      // Dim non-connected nodes, highlight connected
      var nodeUpdates = [];
      nodes.forEach(function (n) {{
        if (n.id === selectedId) {{
          nodeUpdates.push({{
            id: n.id,
            opacity: 1.0,
            size: (n.original_size || 20) * 1.35,
            borderWidth: 4,
            shadow: {{ enabled: true, color: '#38bdf8', size: 20 }},
            font: {{ size: 14, color: '#ffffff', strokeWidth: 3, strokeColor: '#0f172a' }}
          }});
        }} else if (connectedSet.has(n.id)) {{
          nodeUpdates.push({{
            id: n.id,
            opacity: 1.0,
            size: (n.original_size || 20) * 1.15,
            borderWidth: 2.5,
            shadow: {{ enabled: true, color: '#00f5d4', size: 10 }},
            font: {{ size: 12, color: '#f8fafc', strokeWidth: 2, strokeColor: '#0f172a' }}
          }});
        }} else {{
          nodeUpdates.push({{
            id: n.id,
            opacity: 0.12,
            size: (n.original_size || 20) * 0.85,
            borderWidth: 1,
            shadow: {{ enabled: false }},
            font: {{ size: 9, color: 'rgba(148, 163, 184, 0.2)' }}
          }});
        }}
      }});
      nodes.update(nodeUpdates);

      // Highlight connected edges and reveal their labels
      var edgeUpdates = [];
      edges.forEach(function (e) {{
        if (connectedEdges.includes(e.id)) {{
          var isOutbound = (e.from === selectedId);
          edgeUpdates.push({{
            id: e.id,
            label: e.edgeType || "",
            width: 3.0,
            color: {{
              color: isOutbound ? '#f97316' : '#00f5d4',
              opacity: 1.0,
              highlight: isOutbound ? '#f97316' : '#00f5d4'
            }},
            font: {{
              size: 11,
              color: '#ffffff',
              background: '#0f172a',
              strokeWidth: 0
            }}
          }});
        }} else {{
          edgeUpdates.push({{
            id: e.id,
            label: "",
            width: 0.4,
            color: {{ color: 'rgba(51, 65, 85, 0.08)', opacity: 0.08 }},
            font: {{ size: 0 }}
          }});
        }}
      }});
      edges.update(edgeUpdates);

      // Send postMessage to ModernizeAI UI parent window to open Inspector Drawer
      if (window.parent && window.parent !== window) {{
        window.parent.postMessage({{
          type: 'NODE_SELECTED',
          nodeId: selectedId,
          nodeType: selectedNodeObj ? selectedNodeObj.node_type : "Component",
          sourceFile: selectedNodeObj ? selectedNodeObj.source_file : ""
        }}, '*');
      }}
    }});

    // 2. RESTORE DEFAULTS ON DESELECT
    function restoreDefaults() {{
      activeSelection = null;
      var nodeUpdates = [];
      nodes.forEach(function (n) {{
        nodeUpdates.push({{
          id: n.id,
          opacity: 1.0,
          size: n.original_size || 20,
          borderWidth: 2,
          shadow: {{ enabled: true, color: 'rgba(0,0,0,0.4)', size: 8 }},
          font: {{ size: 12, color: '#f8fafc', strokeWidth: 0 }}
        }});
      }});
      nodes.update(nodeUpdates);

      var edgeUpdates = [];
      edges.forEach(function (e) {{
        edgeUpdates.push({{
          id: e.id,
          label: "", // Hide edge label in default state
          width: e.is_hub ? 0.8 : (e.edgeType === "WRITES_TO" || e.edgeType === "CALLS" ? 2.2 : 1.4),
          color: {{
            color: e.is_hub ? "rgba(100, 116, 139, 0.22)" : (e.original_color || "#64748b"),
            opacity: e.is_hub ? 0.3 : 0.85
          }},
          font: {{ size: 0 }}
        }});
      }});
      edges.update(edgeUpdates);

      if (window.parent && window.parent !== window) {{
        window.parent.postMessage({{ type: 'NODE_DESELECTED' }}, '*');
      }}
    }}

    network.on("deselectNode", function () {{
      restoreDefaults();
    }});

    network.on("click", function (params) {{
      if (!params.nodes || params.nodes.length === 0) {{
        restoreDefaults();
      }}
    }});

    // 3. SEARCH & AUTO-ZOOM
    var searchInput = document.getElementById("search-input");
    var searchDropdown = document.getElementById("search-dropdown");

    searchInput.addEventListener("input", function (e) {{
      var q = e.target.value.trim().toLowerCase();
      if (!q) {{
        searchDropdown.classList.remove("active");
        searchDropdown.innerHTML = "";
        return;
      }}
      var matches = rawNodes.filter(function (n) {{
        return n.id.toLowerCase().includes(q) || (n.label && n.label.toLowerCase().includes(q));
      }}).slice(0, 8);

      if (matches.length === 0) {{
        searchDropdown.innerHTML = '<div class="search-item" style="color: #64748b;">No matching components</div>';
      }} else {{
        searchDropdown.innerHTML = matches.map(function (m) {{
          return '<div class="search-item" data-id="' + m.id + '">' +
            '<span>' + m.label + '</span><span class="search-badge">' + (m.node_type || '') + '</span></div>';
        }}).join("");
      }}
      searchDropdown.classList.add("active");
    }});

    searchDropdown.addEventListener("click", function (e) {{
      var item = e.target.closest(".search-item");
      if (!item || !item.dataset.id) return;
      var targetId = item.dataset.id;
      searchDropdown.classList.remove("active");
      searchInput.value = "";
      focusNode(targetId);
    }});

    function focusNode(nodeId) {{
      if (!nodes.get(nodeId)) return;
      network.selectNodes([nodeId]);
      network.focus(nodeId, {{
        scale: 1.25,
        animation: {{ duration: 600, easingFunction: 'easeInOutQuad' }}
      }});
      // Trigger selectNode logic
      network.emit("selectNode", {{ nodes: [nodeId] }});
    }}

    // 4. TOGGLE HIDE TESTS
    var toggleTestsBtn = document.getElementById("btn-toggle-tests");
    toggleTestsBtn.addEventListener("click", function () {{
      hideTests = !hideTests;
      toggleTestsBtn.classList.toggle("active", hideTests);
      toggleTestsBtn.innerHTML = hideTests ? "<span>🧪 Show Tests</span>" : "<span>🧪 Hide Tests</span>";

      var filteredNodes = rawNodes.filter(function (n) {{
        return hideTests ? !n.is_test : true;
      }});
      var filteredNodeIds = new Set(filteredNodes.map(function(n) {{ return n.id; }}));
      var filteredEdges = rawEdges.filter(function (e) {{
        return filteredNodeIds.has(e.from) && filteredNodeIds.has(e.to);
      }});

      nodes.clear();
      nodes.add(filteredNodes);
      edges.clear();
      edges.add(filteredEdges);

      document.getElementById("count-nodes").textContent = filteredNodes.length;
      document.getElementById("count-edges").textContent = filteredEdges.length;

      restoreDefaults();
      network.fit({{ animation: {{ duration: 500 }} }});
    }});

    // 5. TOGGLE HIERARCHICAL LAYOUT
    var layoutBtn = document.getElementById("btn-layout");
    layoutBtn.addEventListener("click", function () {{
      isHierarchical = !isHierarchical;
      layoutBtn.classList.toggle("active", isHierarchical);
      layoutBtn.innerHTML = isHierarchical ? "<span>🪐 Organic Force</span>" : "<span>📐 Hierarchical</span>";

      if (isHierarchical) {{
        network.setOptions(hierarchicalOptions);
      }} else {{
        network.setOptions(forceOptions);
      }}
      network.fit({{ animation: {{ duration: 500 }} }});
    }});

    // 6. FREEZE / THAW PHYSICS
    var freezeBtn = document.getElementById("btn-freeze");
    freezeBtn.addEventListener("click", function () {{
      isFrozen = !isFrozen;
      freezeBtn.classList.toggle("active", isFrozen);
      freezeBtn.innerHTML = isFrozen ? "<span>🔥 Resume</span>" : "<span>❄️ Freeze</span>";
      network.setOptions({{ physics: {{ enabled: !isFrozen }} }});
    }});

    // 7. FIT VIEW
    document.getElementById("btn-fit").addEventListener("click", function () {{
      network.fit({{ animation: {{ duration: 500 }} }});
    }});

    // 8. PARENT WINDOW MESSAGE LISTENER
    window.addEventListener("message", function (event) {{
      var msg = event.data;
      if (!msg) return;

      if (msg.action === "freeze") {{
        isFrozen = true;
        freezeBtn.classList.add("active");
        freezeBtn.innerHTML = "<span>🔥 Resume</span>";
        network.setOptions({{ physics: {{ enabled: false }} }});
      }} else if (msg.action === "unfreeze") {{
        isFrozen = false;
        freezeBtn.classList.remove("active");
        freezeBtn.innerHTML = "<span>❄️ Freeze</span>";
        network.setOptions({{ physics: {{ enabled: true }} }});
      }} else if (msg.action === "toggle_tests") {{
        if (msg.hideTests !== undefined && msg.hideTests !== hideTests) {{
          toggleTestsBtn.click();
        }}
      }} else if (msg.action === "search_node" && msg.nodeId) {{
        focusNode(msg.nodeId);
      }}
    }});
  </script>
</body>
</html>"""

        with open(abs_out, "w", encoding="utf-8") as f:
            f.write(html_content)
        return abs_out
