# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Interactive HTML Knowledge Graph Visualizer.
Generates an interactive, color-coded, physics-enabled HTML network view.
Uses PyVis if installed, or produces self-contained standalone Vis.js HTML if offline.
"""

import json
import os
from typing import Dict, Optional
import networkx as nx

try:
    from pyvis.network import Network
    HAS_PYVIS = True
except ImportError:
    HAS_PYVIS = False


class GraphVisualizer:
    """
    Renders the Knowledge Graph into a standalone, interactive HTML visualization.
    """

    COLOR_PALETTE = {
        "Application": "#2b5c8f",        # Navy
        "Service": "#00a896",            # Cyan / Teal
        "Module": "#028090",             # Dark Cyan
        "APIEndpoint": "#05668d",        # Deep Blue
        "DatabaseTable": "#3a86ff",      # Vibrant Blue
        "Column": "#8338ec",             # Purple
        "StoredProcedure": "#06d6a0",     # Emerald
        "BusinessRule": "#ffb703",       # Amber / Gold
        "RequirementDocument": "#fb5607",# Orange
        "SMEInsight": "#f72585",         # Magenta
        "Risk": "#e63946",               # Crimson Red
    }

    EDGE_COLORS = {
        "CALLS": "#00a896",
        "DEPENDS_ON": "#6c757d",
        "READS_FROM": "#3a86ff",
        "WRITES_TO": "#e63946",
        "IMPLEMENTS_RULE": "#ffb703",
        "DEFINED_IN": "#8338ec",
        "IMPACTS": "#d90429",
        "VALIDATES": "#06d6a0",
    }

    @classmethod
    def render_html(
        cls,
        graph: nx.MultiDiGraph,
        output_path: str = "artifacts/modernize_graph.html",
        height: str = "800px",
        width: str = "100%",
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        abs_out = os.path.abspath(output_path)

        if HAS_PYVIS:
            net = Network(
                height=height,
                width=width,
                directed=True,
                notebook=False,
                bgcolor="#0f172a",
                font_color="#f8fafc",
            )
            net.set_options("""
            {
              "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 4,
                "shadow": true,
                "font": { "size": 14, "face": "Inter, sans-serif", "color": "#f8fafc" }
              },
              "edges": {
                "arrows": { "to": { "enabled": true, "scaleFactor": 0.8 } },
                "smooth": { "type": "continuous" },
                "shadow": true
              },
              "physics": {
                "barnesHut": {
                  "gravitationalConstant": -6000,
                  "centralGravity": 0.3,
                  "springLength": 120,
                  "springConstant": 0.04,
                  "damping": 0.09
                },
                "minVelocity": 0.75
              },
              "interaction": {
                "hover": true,
                "tooltipDelay": 200,
                "navigationButtons": true,
                "keyboard": true
              }
            }
            """)

            for node_id, data in graph.nodes(data=True):
                node_type = data.get("node_type", "Module")
                color = cls.COLOR_PALETTE.get(node_type, "#94a3b8")
                src = data.get("source_file", "N/A")
                l_start = data.get("line_start", 1)
                l_end = data.get("line_end", 1)
                snippet = str(data.get("evidence_snippet", "")).replace('"', '&quot;').replace("'", "&#39;")
                tooltip = f"[{node_type}] {node_id}\nFile: {src}:{l_start}-{l_end}\n\nSnippet: {snippet[:140]}..."

                size = 28 if node_type in ("Application", "Service") else 20
                if node_type == "DatabaseTable":
                    size = 24
                elif node_type == "BusinessRule":
                    size = 22

                net.add_node(
                    node_id,
                    label=data.get("label", node_id),
                    title=tooltip,
                    color=color,
                    size=size,
                )

            for u, v, key, data in graph.edges(keys=True, data=True):
                edge_type = data.get("edge_type", key)
                edge_color = cls.EDGE_COLORS.get(edge_type, "#64748b")
                src_file = data.get("source_file", "")
                edge_title = f"{u} --[{edge_type}]--> {v}"
                if src_file:
                    edge_title += f" ({src_file}:{data.get('line_start', 1)})"

                net.add_edge(
                    u,
                    v,
                    label=edge_type,
                    title=edge_title,
                    color=edge_color,
                    font={"size": 10, "color": "#94a3b8", "align": "middle"},
                    width=2 if edge_type in ("WRITES_TO", "CALLS") else 1,
                )

            net.write_html(abs_out)
            return abs_out

        # Standalone HTML fallback if pyvis is not installed
        nodes_list = []
        for node_id, data in graph.nodes(data=True):
            node_type = data.get("node_type", "Module")
            nodes_list.append({
                "id": node_id,
                "label": data.get("label", node_id),
                "color": cls.COLOR_PALETTE.get(node_type, "#94a3b8"),
                "size": 26 if node_type in ("Application", "Service") else 18,
                "title": f"[{node_type}] {node_id}",
            })

        edges_list = []
        for u, v, key, data in graph.edges(keys=True, data=True):
            edge_type = data.get("edge_type", key)
            edges_list.append({
                "from": u,
                "to": v,
                "label": edge_type,
                "color": {"color": cls.EDGE_COLORS.get(edge_type, "#64748b")},
                "arrows": "to",
            })

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>ModernizeAI Knowledge Fabric</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{ margin: 0; background: #0f172a; color: #f8fafc; font-family: sans-serif; }}
    #network {{ width: 100vw; height: 100vh; }}
    #legend {{ position: absolute; top: 10px; left: 10px; background: rgba(15,23,42,0.9); padding: 12px; border-radius: 8px; border: 1px solid #334155; font-size: 12px; }}
  </style>
</head>
<body>
  <div id="legend"><strong>ModernizeAI Graph Nodes: {len(nodes_list)} | Edges: {len(edges_list)}</strong></div>
  <div id="network"></div>
  <script>
    var nodes = new vis.DataSet({json.dumps(nodes_list)});
    var edges = new vis.DataSet({json.dumps(edges_list)});
    var container = document.getElementById('network');
    var data = {{ nodes: nodes, edges: edges }};
    var options = {{
      physics: {{ barnesHut: {{ gravitationalConstant: -4000, springLength: 120 }} }},
      nodes: {{ font: {{ color: '#f8fafc' }} }},
      edges: {{ font: {{ color: '#94a3b8', size: 10, align: 'middle' }} }}
    }};
    var network = new vis.Network(container, data, options);
  </script>
</body>
</html>"""
        with open(abs_out, "w", encoding="utf-8") as f:
            f.write(html_content)
        return abs_out
