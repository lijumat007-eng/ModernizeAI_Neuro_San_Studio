// ModernizeAI UI Interactive Controller

const AGENT_META = {
    frontman: { name: "Frontman", icon: "👑", role: "Orchestrator" },
    discovery: { name: "Discovery", icon: "🔍", role: "Asset Ingestion" },
    code_intel: { name: "Code Intel", icon: "☕", role: "Java/SQL AST" },
    database_intel: { name: "DB Intel", icon: "🗄️", role: "DDL & Lineage" },
    doc_intel: { name: "Doc Intel", icon: "📄", role: "Specs & Notes" },
    business_rules: { name: "Business Rules", icon: "⚖️", role: "Logic Extraction" },
    validation: { name: "Validation", icon: "🛡️", role: "Anti-Hallucination" },
    knowledge_graph: { name: "Knowledge Graph", icon: "🌐", role: "MultiDiGraph Engine" },
    memory_manager: { name: "Memory Manager", icon: "💾", role: "5-Tier Memory" },
    impact_analysis: { name: "Impact Analysis", icon: "💥", role: "Blast-Radius BFS" },
    modernization_advisor: { name: "Modernize Advisor", icon: "🧭", role: "6R Roadmap" }
};

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initModals();
    initQueries();
    loadStatus();
    loadReports();
});

// Tab switching
function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPane = document.getElementById(targetTab);
            if (targetPane) {
                targetPane.classList.add("active");
            }
        });
    });
}

// Modal handling
function initModals() {
    const rescanBtn = document.getElementById("rescan-btn");
    const modal = document.getElementById("ingest-modal");
    const closeModal = document.getElementById("close-modal");
    const cancelBtn = document.getElementById("cancel-modal-btn");
    const startIngestBtn = document.getElementById("start-ingest-btn");
    const progressContainer = document.getElementById("ingest-progress-container");

    rescanBtn.addEventListener("click", () => {
        modal.classList.add("active");
    });

    const closeHandler = () => {
        modal.classList.remove("active");
        progressContainer.style.display = "none";
        startIngestBtn.disabled = false;
    };

    closeModal.addEventListener("click", closeHandler);
    cancelBtn.addEventListener("click", closeHandler);

    startIngestBtn.addEventListener("click", async () => {
        const repoPath = document.getElementById("repo-input").value.trim();
        progressContainer.style.display = "block";
        startIngestBtn.disabled = true;

        try {
            const res = await fetch("/api/scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_path: repoPath })
            });
            const data = await res.json();
            if (data.status === "completed") {
                // Refresh status and iframe
                await loadStatus();
                await loadReports();
                const iframe = document.getElementById("graph-iframe");
                if (iframe) {
                    iframe.src = "/artifacts/modernize_graph.html?t=" + Date.now();
                }
                closeHandler();
            }
        } catch (err) {
            console.error("Scan error:", err);
            alert("Error during scan: " + err.message);
            closeHandler();
        }
    });
}

// Fetch status and metrics
async function loadStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        
        if (data.knowledge_graph) {
            document.getElementById("stat-nodes").textContent = data.knowledge_graph.total_nodes || 21;
            document.getElementById("stat-edges").textContent = data.knowledge_graph.total_edges || 29;
        }
        if (data.memory) {
            document.getElementById("stat-rules").textContent = 5;
            document.getElementById("stat-domains").textContent = 5;
        }
    } catch (err) {
        console.warn("Status fetch failed:", err);
    }
}

// Load markdown reports into tabs
async function loadReports() {
    try {
        // 1. Readiness Report
        const r1 = await fetch("/api/artifacts/readiness_report");
        if (r1.ok) {
            const d1 = await r1.json();
            document.getElementById("readiness-report-body").innerHTML = marked.parse(d1.content);
        }

        // 2. Blast Radius Matrix
        const r2 = await fetch("/api/artifacts/blast_radius");
        if (r2.ok) {
            const d2 = await r2.json();
            document.getElementById("blast-matrix-body").innerHTML = marked.parse(d2.content);
        }

        // 3. Business Rules Catalog
        const r3 = await fetch("/api/artifacts/business_rules");
        if (r3.ok) {
            const d3 = await r3.json();
            document.getElementById("rules-catalog-body").innerHTML = marked.parse(d3.content);
        }

        // 4. JSON Graph
        const r4 = await fetch("/api/artifacts/knowledge_graph_json");
        if (r4.ok) {
            const d4 = await r4.json();
            document.getElementById("json-viewer-content").textContent = d4.content;
        }
    } catch (err) {
        console.warn("Failed to load artifacts preview:", err);
    }
}

// Helper to update agent grid highlight
function updateAgentVisualizer(agentPath = []) {
    // Clear all previous badges and active states
    document.querySelectorAll(".agent-chip").forEach(chip => {
        chip.classList.remove("active-traversed");
        const existingBadge = chip.querySelector(".agent-step-badge");
        if (existingBadge) existingBadge.remove();
    });

    agentPath.forEach((fullAgentId, idx) => {
        const cleanId = fullAgentId.replace(/_agent$/, "");
        const chip = document.querySelector(`.agent-chip[data-agent="${cleanId}"]`);
        if (chip) {
            chip.classList.add("active-traversed");
            const badge = document.createElement("span");
            badge.className = "agent-step-badge";
            badge.textContent = `${idx + 1}`;
            chip.appendChild(badge);
        }
    });
}

// Queries handling
function initQueries() {
    const queryInput = document.getElementById("query-input");
    const runBtn = document.getElementById("run-query-btn");
    const resultsPanel = document.getElementById("query-results");
    const chips = document.querySelectorAll(".query-chip");

    chips.forEach(chip => {
        chip.addEventListener("click", () => {
            const q = chip.getAttribute("data-q");
            queryInput.value = q;
            executeQuery(q);
        });
    });

    runBtn.addEventListener("click", () => {
        const q = queryInput.value.trim();
        if (q) executeQuery(q);
    });

    queryInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            const q = queryInput.value.trim();
            if (q) executeQuery(q);
        }
    });

    async function executeQuery(query) {
        // Optimistic UI update: pulse Frontman agent
        updateAgentVisualizer(["frontman_agent"]);

        resultsPanel.innerHTML = `
            <div class="results-placeholder">
                <span class="placeholder-icon">⚡</span>
                <p><strong>Frontman Orchestrator Active:</strong> Invoking Neuro SAN LLM Swarm Reasoning & Traversing Knowledge Fabric...</p>
            </div>
        `;

        try {
            // Check if query targets a specific entity
            let targetEntity = null;
            if (query.toUpperCase().includes("POLICY_MASTER")) targetEntity = "POLICY_MASTER";
            else if (query.toUpperCase().includes("CLAIMSERVICE")) targetEntity = "ClaimService";
            else if (query.toUpperCase().includes("SP_PROCESS_CLAIM")) targetEntity = "SP_PROCESS_CLAIM";

            const res = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query, target_entity: targetEntity })
            });
            const data = await res.json();
            renderQueryResults(data);
        } catch (err) {
            resultsPanel.innerHTML = `<div class="error-msg">Failed to execute query: ${err.message}</div>`;
        }
    }

    function renderQueryResults(data) {
        const hybrid = data.hybrid_rag || {};
        const evidence = hybrid.fused_evidence || [];
        const blast = data.blast_radius;
        const agentPath = data.agent_path || [];
        const trace = data.trace || [];
        const finalAnswer = data.final_answer || "";

        // Update the top agent grid visualizer with the traversed nodes
        updateAgentVisualizer(agentPath);

        let html = "";

        // 1. Swarm Execution Breadcrumb
        if (agentPath.length > 0) {
            html += `
                <div class="swarm-breadcrumb-container">
                    <div class="swarm-breadcrumb-header">
                        <span>⚡ Active Agent Traversal Pipeline (${agentPath.length} Nodes Visited)</span>
                    </div>
                    <div class="swarm-breadcrumb-path">
            `;
            agentPath.forEach((agentId, idx) => {
                const cleanId = agentId.replace(/_agent$/, "");
                const meta = AGENT_META[cleanId] || { name: cleanId, icon: "🤖" };
                html += `
                    <span class="breadcrumb-node">
                        <span>${meta.icon}</span>
                        <span>${meta.name}</span>
                    </span>
                `;
                if (idx < agentPath.length - 1) {
                    html += `<span class="breadcrumb-arrow">➔</span>`;
                }
            });
            html += `
                    </div>
                </div>
            `;
        }

        // 2. Synthesized LLM Answer Card
        if (finalAnswer) {
            const llmModelLabel = data.llm_reasoning ? "Gemini 2.5 Flash Reasoning" : "Local Heuristic Synthesis";
            html += `
                <div class="llm-answer-card">
                    <div class="llm-answer-header">
                        <span class="llm-badge">🧠 ${llmModelLabel}</span>
                        <span style="font-size: 11px; color: #94a3b8;">Deterministic 80% / LLM 20%</span>
                    </div>
                    <div class="llm-answer-content">
                        ${marked.parse(finalAnswer)}
                    </div>
                </div>
            `;
        }

        // 3. Multi-Agent Reasoning Trace Timeline
        if (trace.length > 0) {
            html += `
                <div class="reasoning-timeline">
                    <div class="timeline-header">
                        <span>🔍 Agent-by-Agent LLM Reasoning & Decision Trace</span>
                        <span style="font-size: 11px; color: #94a3b8;">Step-by-Step Traversal</span>
                    </div>
            `;
            trace.forEach(step => {
                const cleanId = (step.agent || "").replace(/_agent$/, "");
                const meta = AGENT_META[cleanId] || { name: cleanId, icon: "🤖" };
                html += `
                    <div class="timeline-step">
                        <div class="timeline-step-dot"></div>
                        <div class="timeline-step-title">${meta.icon} Step ${step.step}: ${meta.name} - ${step.action}</div>
                        <div class="timeline-step-desc">
                            <strong>Thought:</strong> ${step.thought}<br/>
                            <span style="color: #38bdf8;"><strong>Outcome:</strong> ${step.result_summary}</span>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        // 4. Blast radius alert if entity queried
        if (blast && blast.target_entity) {
            html += `
                <div class="evidence-card" style="border-left-color: #e63946; background: rgba(230, 57, 70, 0.08);">
                    <div class="evidence-header">
                        <span class="evidence-label" style="color: #f87171;">💥 Blast-Radius Impact: ${blast.target_entity}</span>
                        <span class="evidence-score" style="background: rgba(230, 57, 70, 0.2); color: #fca5a5;">${blast.risk_level}</span>
                    </div>
                    <div class="evidence-body">
                        Modifications to <b>${blast.target_entity}</b> affect <b>${blast.total_affected_count} components</b> (${blast.upstream_count} upstream callers, ${blast.downstream_count} downstream dependencies).
                    </div>
                </div>
            `;
        }

        // 5. Render fused evidence cards
        if (evidence.length > 0) {
            html += `<h4 style="font-size: 14px; color: #94a3b8; margin: 12px 0 6px;">Fused Knowledge Fabric Evidence (Semantic RRF + Graph PPR)</h4>`;
            evidence.forEach((ev) => {
                const sourceBadge = ev.source === "knowledge_graph" ? "🌐 Graph Node" : "📄 Doc Semantic";
                html += `
                    <div class="evidence-card">
                        <div class="evidence-header">
                            <span class="evidence-label">${ev.label}</span>
                            <span class="evidence-score">RRF: ${ev.rrf_score}</span>
                        </div>
                        <div class="evidence-body">${ev.content}</div>
                        <div class="evidence-citation">Provenance Citation: ${ev.citation} | Source: ${sourceBadge}</div>
                    </div>
                `;
            });
        } else if (!finalAnswer) {
            html += `<div class="results-placeholder"><p>No relevant evidence matched in Knowledge Fabric.</p></div>`;
        }

        resultsPanel.innerHTML = html;
    }
}
