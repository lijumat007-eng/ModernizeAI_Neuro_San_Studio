// ModernizeAI Studio UI Controller

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initSourceWizard();
    initCopilot();
    initInspector();
    initRulesFilter();
    loadSystemStatus();
    loadCockpitData();
    loadRulesData();
    loadJsonExport();
});

// 1. Sidebar Navigation & Views Routing
const VIEW_METADATA = {
    "view-ingest": { title: "Ingestion Studio", breadcrumb: "Data Sources & Codebase Ingestion" },
    "view-graph": { title: "Knowledge Fabric Explorer", breadcrumb: "Interactive NetworkX MultiDiGraph Canvas" },
    "view-copilot": { title: "Graph-RAG Copilot", breadcrumb: "Hybrid Agentic Reasoning & Codebase Q&A" },
    "view-cockpit": { title: "6R Modernization Cockpit", breadcrumb: "Cloud Readiness Scoring & Microservices Sizing" },
    "view-rules": { title: "Rules & Provenance Catalog", breadcrumb: "Verified Business Logic & Architectural Risks" },
    "view-exports": { title: "Graph Exports", breadcrumb: "Machine-Readable JSON-LD & GraphML Artifacts" },
};

function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    const views = document.querySelectorAll(".workspace-view");
    const viewTitle = document.getElementById("view-title");
    const viewBreadcrumb = document.getElementById("view-breadcrumb");

    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetViewId = item.getAttribute("data-view");

            navItems.forEach(n => n.classList.remove("active"));
            views.forEach(v => v.classList.remove("active"));

            item.classList.add("active");
            const targetView = document.getElementById(targetViewId);
            if (targetView) {
                targetView.classList.add("active");
            }

            if (VIEW_METADATA[targetViewId]) {
                viewTitle.textContent = VIEW_METADATA[targetViewId].title;
                viewBreadcrumb.textContent = VIEW_METADATA[targetViewId].breadcrumb;
            }

            if (targetViewId === "view-cockpit") {
                loadCockpitData();
            } else if (targetViewId === "view-rules") {
                loadRulesData();
            } else if (targetViewId === "view-exports") {
                loadJsonExport();
            }
        });
    });

    // Quick scan trigger in top-bar switches to Ingest view
    const quickScanTrigger = document.getElementById("quick-scan-trigger");
    if (quickScanTrigger) {
        quickScanTrigger.addEventListener("click", () => {
            const ingestNav = document.querySelector('.nav-item[data-view="view-ingest"]');
            if (ingestNav) ingestNav.click();
        });
    }
}

// 2. Multi-Source Ingestion Wizard (Local, Git, S3)
function initSourceWizard() {
    const sourceTabs = document.querySelectorAll(".source-tab-btn");
    const sourcePanels = document.querySelectorAll(".source-form-panel");
    let activeSource = "local";

    sourceTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const source = tab.getAttribute("data-source");
            activeSource = source;

            sourceTabs.forEach(t => t.classList.remove("active"));
            sourcePanels.forEach(p => p.classList.remove("active"));

            tab.classList.add("active");
            const targetPanel = document.getElementById(`source-form-${source}`);
            if (targetPanel) targetPanel.classList.add("active");
        });
    });

    // Preset Buttons
    const presetBtns = document.querySelectorAll(".preset-btn");
    const localInput = document.getElementById("local-path-input");
    presetBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            presetBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            localInput.value = btn.getAttribute("data-preset");
        });
    });

    // Folder Browse Picker
    const browseBtn = document.getElementById("browse-folder-btn");
    const nativePicker = document.getElementById("native-folder-picker");
    if (browseBtn && nativePicker) {
        browseBtn.addEventListener("click", () => nativePicker.click());
        nativePicker.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                const firstPath = e.target.files[0].webkitRelativePath || e.target.files[0].name;
                const folderName = firstPath.split("/")[0] || firstPath.split("\\")[0];
                localInput.value = `data/${folderName}`;
                appendTerminal(`[FILE-PICKER] Selected local directory: ${localInput.value} (${e.target.files.length} candidate files detected).`);
            }
        });
    }

    // Ingestion Execution
    const runBtn = document.getElementById("run-ingestion-btn");
    if (runBtn) {
        runBtn.addEventListener("click", async () => {
            await executeIngestion(activeSource);
        });
    }
}

async function executeIngestion(sourceType) {
    const runBtn = document.getElementById("run-ingestion-btn");
    const statusBadge = document.getElementById("pipeline-status-badge");
    const terminal = document.getElementById("ingest-terminal-content");
    const steps = [
        document.getElementById("step-discovery"),
        document.getElementById("step-ast"),
        document.getElementById("step-rules"),
        document.getElementById("step-qa"),
        document.getElementById("step-fabric")
    ];

    let payload = { source_type: sourceType };

    if (sourceType === "local") {
        payload.repo_path = document.getElementById("local-path-input").value.trim() || "data/insurance_claims_app";
    } else if (sourceType === "git") {
        payload.git_url = document.getElementById("git-url-input").value.trim();
        payload.git_branch = document.getElementById("git-branch-input").value.trim() || "main";
        if (!payload.git_url) {
            alert("Please enter a valid Git Repository URL.");
            return;
        }
    } else if (sourceType === "s3") {
        payload.s3_uri = document.getElementById("s3-uri-input").value.trim();
        payload.aws_region = document.getElementById("s3-region-input").value;
        if (!payload.s3_uri) {
            alert("Please enter a valid S3 Bucket URI (e.g. s3://bucket-name/path/).");
            return;
        }
    }

    runBtn.disabled = true;
    runBtn.innerHTML = `<span>⏳ Ingesting & Building Fabric...</span>`;
    statusBadge.textContent = "Pipeline Executing...";
    statusBadge.style.color = "var(--accent-cyan)";
    statusBadge.style.borderColor = "var(--accent-cyan)";

    // Stepper Animation
    steps.forEach(s => { s.classList.remove("active", "completed"); });
    steps[0].classList.add("active");

    appendTerminal(`\n[START] Initiating ${sourceType.toUpperCase()} ingestion pipeline...`);

    const stepInterval = setInterval(() => {
        const activeIdx = steps.findIndex(s => s.classList.contains("active"));
        if (activeIdx >= 0 && activeIdx < steps.length - 1) {
            steps[activeIdx].classList.remove("active");
            steps[activeIdx].classList.add("completed");
            steps[activeIdx + 1].classList.add("active");
        }
    }, 1200);

    try {
        const res = await fetch("/api/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        let data;
        try {
            data = await res.json();
        } catch (parseErr) {
            throw new Error(`Server returned HTTP ${res.status}: ${res.statusText || "Internal Error"}`);
        }

        clearInterval(stepInterval);

        if (data.logs) {
            data.logs.forEach(msg => appendTerminal(`[LOG] ${msg}`));
        }

        steps.forEach(s => { s.classList.remove("active"); s.classList.add("completed"); });

        if (data.status === "completed") {
            statusBadge.textContent = "Complete & Verified";
            statusBadge.style.color = "var(--accent-emerald)";
            statusBadge.style.borderColor = "var(--accent-emerald)";

            const nNodes = data.knowledge_graph?.total_nodes || 0;
            const nEdges = data.knowledge_graph?.total_edges || 0;
            appendTerminal(`[SUCCESS] Ingested ${data.repo_path}. Verified ${nNodes} nodes and ${nEdges} relationships.`);
            appendTerminal(`[FABRIC] Knowledge Fabric and 6R scorecards compiled successfully.`);
            if (data.project_artifacts_dir) {
                appendTerminal(`[DELIVERABLES] Project artifacts archived to: ${data.project_artifacts_dir}/`);
            }

            // Reload status & refresh graph iframe and cockpit/rules
            loadSystemStatus();
            loadCockpitData();
            loadRulesData();
            const graphIframe = document.getElementById("graph-iframe");
            if (graphIframe) {
                graphIframe.src = `/artifacts/modernize_graph.html?t=${Date.now()}`;
            }

            // Update sidebar path
            const sidebarPath = document.getElementById("sidebar-active-path");
            if (sidebarPath) sidebarPath.textContent = data.repo_path;
        } else {
            statusBadge.textContent = "Ingestion Notice";
            statusBadge.style.color = "var(--accent-rose)";
            statusBadge.style.borderColor = "var(--accent-rose)";
            appendTerminal(`[ERROR] Ingestion failed: ${data.message || "Unknown error"}`);
        }
    } catch (err) {
        clearInterval(stepInterval);
        statusBadge.textContent = "Error";
        statusBadge.style.color = "var(--accent-rose)";
        appendTerminal(`[ERROR] Connection failed: ${err.message}`);
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = `<span class="btn-icon">🚀</span> Start Ingestion & Rebuild Fabric`;
    }
}

function appendTerminal(msg) {
    const terminal = document.getElementById("ingest-terminal-content");
    if (terminal) {
        terminal.textContent += `\n${msg}`;
        terminal.scrollTop = terminal.scrollHeight;
    }
}

// 3. Node Inspector Drawer & Knowledge Fabric
function initInspector() {
    const drawer = document.getElementById("node-inspector-drawer");
    const closeBtn = document.getElementById("close-inspector-btn");
    const blastBtn = document.getElementById("trigger-blast-btn");
    const askCopilotBtn = document.getElementById("ask-copilot-node-btn");

    if (closeBtn && drawer) {
        closeBtn.addEventListener("click", () => {
            drawer.classList.remove("active");
        });
    }

    // Freeze Physics toggle for iframe
    const freezeBtn = document.getElementById("freeze-physics-btn");
    let isFrozen = false;
    if (freezeBtn) {
        freezeBtn.addEventListener("click", () => {
            const iframe = document.getElementById("graph-iframe");
            if (iframe && iframe.contentWindow) {
                isFrozen = !isFrozen;
                iframe.contentWindow.postMessage({ action: isFrozen ? "freeze" : "unfreeze" }, "*");
                freezeBtn.innerHTML = isFrozen ? "<span>🔥 Thaw Physics</span>" : "<span>❄️ Freeze Physics</span>";
                freezeBtn.classList.toggle("active", isFrozen);
            }
        });
    }

    // Hide Tests toggle for iframe
    const toggleTestsBtn = document.getElementById("toggle-tests-ui-btn");
    let hideTestsState = false;
    if (toggleTestsBtn) {
        toggleTestsBtn.addEventListener("click", () => {
            const iframe = document.getElementById("graph-iframe");
            if (iframe && iframe.contentWindow) {
                hideTestsState = !hideTestsState;
                iframe.contentWindow.postMessage({ action: "toggle_tests", hideTests: hideTestsState }, "*");
                toggleTestsBtn.innerHTML = hideTestsState ? "<span>🧪 Show Tests</span>" : "<span>🧪 Hide Tests</span>";
                toggleTestsBtn.classList.toggle("active", hideTestsState);
            }
        });
    }

    // Hierarchical / Force Layout toggle for iframe
    const toggleLayoutBtn = document.getElementById("toggle-layout-ui-btn");
    let isHierarchicalState = false;
    if (toggleLayoutBtn) {
        toggleLayoutBtn.addEventListener("click", () => {
            const iframe = document.getElementById("graph-iframe");
            if (iframe && iframe.contentWindow) {
                isHierarchicalState = !isHierarchicalState;
                iframe.contentWindow.postMessage({ action: "set_layout", layout: isHierarchicalState ? "hierarchical" : "force" }, "*");
                toggleLayoutBtn.innerHTML = isHierarchicalState ? "<span>🪐 Organic Force</span>" : "<span>📐 Hierarchical</span>";
                toggleLayoutBtn.classList.toggle("active", isHierarchicalState);
            }
        });
    }

    // Blast Radius calculation
    if (blastBtn) {
        blastBtn.addEventListener("click", async () => {
            const nodeName = document.getElementById("inspector-name").textContent;
            blastBtn.disabled = true;
            blastBtn.textContent = "Calculating Blast Radius...";
            try {
                const res = await fetch("/api/blast_radius", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ target_entity: nodeName, max_depth: 2 })
                });
                const data = await res.json();
                alert(`Blast Radius Impact for ${nodeName}:\n- Total Impacted Entities: ${data.total_impacted || 0}\n- Upstream Callers: ${(data.upstream_callers || []).join(", ") || "None"}\n- Downstream Impacts: ${(data.downstream_impacts || []).join(", ") || "None"}\n- Risk Classification: ${data.risk_level || "MEDIUM"}`);
            } catch (e) {
                alert("Error calculating blast radius: " + e.message);
            } finally {
                blastBtn.disabled = false;
                blastBtn.textContent = "💥 Run Blast Radius for this Node";
            }
        });
    }

    // Ask Copilot contextual trigger
    if (askCopilotBtn) {
        askCopilotBtn.addEventListener("click", () => {
            const nodeName = document.getElementById("inspector-name").textContent;
            const nodeType = document.getElementById("inspector-type").textContent;
            const nodeFile = document.getElementById("inspector-file").textContent;

            // Switch to Copilot tab
            const copilotNav = document.querySelector('.nav-item[data-view="view-copilot"]');
            if (copilotNav) copilotNav.click();

            // Populate prompt input
            const promptInput = document.getElementById("copilot-input");
            if (promptInput) {
                promptInput.value = `Analyze the architecture, dependencies, and modernization strategy for [${nodeType}] ${nodeName} (located at ${nodeFile}). How should this component be decoupled and migrated?`;
                promptInput.focus();
            }
        });
    }

    // Listen for events from Graph Visualizer iframe
    window.addEventListener("message", (event) => {
        const msg = event.data;
        if (!msg) return;

        if (msg.type === "NODE_SELECTED" && msg.nodeId) {
            window.inspectNode(msg.nodeId);
        } else if (msg.type === "NODE_DESELECTED") {
            // Keep drawer open or allow user to dismiss
        }
    });
}

// Global inspect function for external triggers
window.inspectNode = async function(nodeId) {
    const drawer = document.getElementById("node-inspector-drawer");
    if (!drawer) return;

    try {
        const res = await fetch(`/api/node_details/${encodeURIComponent(nodeId)}`);
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById("inspector-type").textContent = data.properties.node_type || "Component";
        document.getElementById("inspector-name").textContent = data.node_id;
        document.getElementById("inspector-file").textContent = data.properties.source_file || "N/A";
        document.getElementById("inspector-lines").textContent = `Lines ${data.properties.line_start || 1} - ${data.properties.line_end || 1}`;
        document.getElementById("inspector-sha").textContent = data.properties.sha256 ? data.properties.sha256.substring(0, 16) + "..." : "verified";
        document.getElementById("inspector-snippet").textContent = data.snippet || data.properties.evidence_snippet || "// No snippet available in Raw Memory";

        const inList = document.getElementById("inspector-inbound");
        inList.innerHTML = (data.inbound_connections || []).map(c => `<li>${c.from} (${c.relationship})</li>`).join("") || "<li>None</li>";

        const outList = document.getElementById("inspector-outbound");
        outList.innerHTML = (data.outbound_connections || []).map(c => `<li>${c.to} (${c.relationship})</li>`).join("") || "<li>None</li>";

        drawer.classList.add("active");
    } catch (e) {
        console.warn("Could not inspect node:", e);
    }
};

// 4. Graph-RAG Conversational Copilot
function initCopilot() {
    const input = document.getElementById("copilot-input");
    const sendBtn = document.getElementById("copilot-send-btn");
    const thread = document.getElementById("chat-thread");
    const promptChips = document.querySelectorAll(".prompt-chip");

    const handleSend = async (queryText) => {
        const query = queryText || input.value.trim();
        if (!query) return;

        input.value = "";
        appendUserMessage(query);

        // Loading bubble
        const loadingId = "loading-" + Date.now();
        appendAssistantMessage(`<span class="pulse-dot"></span> <em>Consulting 11-Agent Swarm (Hybrid Graph-RAG + Personalized PageRank)...</em>`, loadingId);

        try {
            const res = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query })
            });
            const data = await res.json();

            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();

            const answerText = data.final_answer || data.answer || data.response || "Query processed across Knowledge Fabric.";
            const parsedAnswer = (window.marked && window.marked.parse) ? window.marked.parse(answerText) : `<p>${answerText}</p>`;

            // Render Agent Swarm Collaboration Chain
            let traceHtml = "";
            if (data.agent_path && data.agent_path.length > 0) {
                const agentIcons = {
                    frontman: "👑",
                    frontman_agent: "👑",
                    discovery_agent: "🔍",
                    code_intel_agent: "☕",
                    database_intel_agent: "🗄️",
                    doc_intel_agent: "📄",
                    business_rules_agent: "⚖️",
                    validation_agent: "🛡️",
                    knowledge_graph_agent: "🌐",
                    memory_manager_agent: "💾",
                    impact_analysis_agent: "💥",
                    modernization_advisor_agent: "🧭"
                };

                const hopsHtml = data.agent_path.map(ag => {
                    const icon = agentIcons[ag] || "🤖";
                    const cleanName = ag.replace("_agent", "").replace("_", " ").toUpperCase();
                    return `<span class="agent-hop-badge">${icon} ${cleanName}</span>`;
                }).join('<span class="hop-arrow">➔</span>');

                let stepsHtml = "";
                if (data.trace && data.trace.length > 0) {
                    stepsHtml = data.trace.map(t => {
                        const icon = agentIcons[t.agent] || "🤖";
                        return `
                            <div class="trace-step-item">
                                <div class="step-agent-header">
                                    <span class="step-agent-tag">${icon} ${t.agent} (${t.role || "Specialist"})</span>
                                    <span class="step-action-tag">${escapeHtml(t.action || "")}</span>
                                </div>
                                <div class="step-thought-text">${escapeHtml(t.thought || t.reasoning || "")}</div>
                                ${t.result_summary ? `<div class="step-summary-text">↳ <em>${escapeHtml(t.result_summary)}</em></div>` : ""}
                            </div>
                        `;
                    }).join("");
                }

                traceHtml = `
                    <div class="swarm-trace-card">
                        <div class="swarm-trace-header" onclick="this.parentElement.classList.toggle('expanded')">
                            <div class="trace-title-group">
                                <span class="trace-pulse-icon">⚡</span>
                                <span class="trace-title-text">Swarm Collaboration (${data.agent_path.length} Agents):</span>
                                <div class="trace-hops-row">${hopsHtml}</div>
                            </div>
                            <span class="trace-expand-hint">View Trace ▾</span>
                        </div>
                        <div class="swarm-trace-body">
                            ${stepsHtml}
                        </div>
                    </div>
                `;
            }

            appendAssistantMessage(`${traceHtml}<div class="answer-content">${parsedAnswer}</div>`);
        } catch (err) {
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();
            appendAssistantMessage(`<p style="color:var(--accent-rose);">Error querying Knowledge Fabric: ${err.message}</p>`);
        }
    };

    if (sendBtn) {
        sendBtn.addEventListener("click", () => handleSend());
    }

    if (input) {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") handleSend();
        });
    }

    promptChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const q = chip.getAttribute("data-q");
            handleSend(q);
        });
    });
}

function appendUserMessage(text) {
    const thread = document.getElementById("chat-thread");
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble user";
    bubble.innerHTML = `
        <div class="bubble-avatar">👤</div>
        <div class="bubble-body"><p>${escapeHtml(text)}</p></div>
    `;
    thread.appendChild(bubble);
    thread.scrollTop = thread.scrollHeight;
}

function appendAssistantMessage(htmlContent, id = null) {
    const thread = document.getElementById("chat-thread");
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble assistant";
    if (id) bubble.id = id;
    bubble.innerHTML = `
        <div class="bubble-avatar">⚡</div>
        <div class="bubble-body">${htmlContent}</div>
    `;
    thread.appendChild(bubble);
    thread.scrollTop = thread.scrollHeight;
}

function escapeHtml(str) {
    return str.replace(/[&<>'"]/g, tag => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        '"': "&quot;"
    }[tag] || tag));
}

// 5. Rules & Risks Filter
function initRulesFilter() {
    const pills = document.querySelectorAll(".filter-pill");
    const rows = document.querySelectorAll("#rules-table-body tr");

    pills.forEach(pill => {
        pill.addEventListener("click", () => {
            pills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");

            const filter = pill.getAttribute("data-filter");
            rows.forEach(r => {
                if (filter === "all" || r.getAttribute("data-type") === filter) {
                    r.style.display = "";
                } else {
                    r.style.display = "none";
                }
            });
        });
    });
}

// 6. System Status & Metrics Loader
async function loadSystemStatus() {
    try {
        const res = await fetch("/api/status");
        if (!res.ok) return;
        const data = await res.json();

        if (data.knowledge_graph) {
            const kg = data.knowledge_graph;
            const nodesEl = document.getElementById("kpi-nodes");
            const edgesEl = document.getElementById("kpi-edges");
            if (nodesEl) nodesEl.textContent = kg.total_nodes || 0;
            if (edgesEl) edgesEl.textContent = kg.total_edges || 0;
        }

        if (data.active_workspace) {
            const wp = document.getElementById("sidebar-active-path");
            if (wp) wp.textContent = data.active_workspace;
        }
    } catch (e) {
        console.warn("Status poller notice:", e);
    }
}

// 7. Dynamic 6R Cockpit Data Loader
async function loadCockpitData() {
    try {
        const res = await fetch("/api/readiness");
        if (!res.ok) return;
        const data = await res.json();
        const readiness = data.readiness;
        if (!readiness) return;

        // 1. Overall Score Dial & KPI Chip
        const score = readiness.overall_readiness_score ?? 78;
        const cockpitScoreEl = document.getElementById("cockpit-score");
        const kpiScoreEl = document.getElementById("kpi-score");
        if (cockpitScoreEl) cockpitScoreEl.textContent = score;
        if (kpiScoreEl) kpiScoreEl.textContent = `${score}/100`;

        const subTitleEl = document.getElementById("cockpit-score-subtitle");
        if (subTitleEl) {
            subTitleEl.textContent = `Mathematically weighted composite: Modularity (${readiness.modularity_score || 0}%) + Provenance (${readiness.provenance_score || 100}%) + Risk Health (${readiness.risk_health_score || 0}%) • Grade: ${readiness.grade || 'Ready'}`;
        }

        // 2. Subscore Meters
        const modMeter = document.getElementById("meter-modularity");
        const modVal = document.getElementById("val-modularity");
        if (modMeter) modMeter.style.width = `${readiness.modularity_score || 0}%`;
        if (modVal) modVal.textContent = `${readiness.modularity_score || 0}%`;

        const provMeter = document.getElementById("meter-provenance");
        const provVal = document.getElementById("val-provenance");
        if (provMeter) provMeter.style.width = `${readiness.provenance_score || 100}%`;
        if (provVal) provVal.textContent = `${readiness.provenance_score || 100}%`;

        const riskMeter = document.getElementById("meter-risk");
        const riskVal = document.getElementById("val-risk");
        if (riskMeter) riskMeter.style.width = `${readiness.risk_health_score || 60}%`;
        if (riskVal) riskVal.textContent = `${readiness.risk_health_score || 60}%`;

        // 3. 6R Strategy Cards (Grouped by 6R classification)
        const stratRow = document.getElementById("cockpit-strategies-row");
        if (stratRow && data.strategies && data.strategies.length > 0) {
            const stratAccent = {
                "Refactor": "#06b6d4",
                "Replatform": "#3b82f6",
                "Retire / Replace": "#f43f5e",
                "Retain / ACL": "#10b981",
                "Repurchase": "#a855f7"
            };

            const grouped = {};
            data.strategies.forEach(s => {
                const strat = s.strategy_6r || "Refactor";
                if (!grouped[strat]) {
                    grouped[strat] = {
                        strategy: strat,
                        target_pattern: s.target_pattern || strat,
                        components: [],
                        rationale: s.rationale || ""
                    };
                }
                if (s.component) grouped[strat].components.push(s.component);
            });

            stratRow.innerHTML = Object.values(grouped).map(g => {
                const color = stratAccent[g.strategy] || "#06b6d4";
                const comps = g.components;
                const compStr = comps.slice(0, 4).map(c => `<code>${escapeHtml(c)}</code>`).join(", ") + (comps.length > 4 ? ` +${comps.length - 4} more` : "");
                return `
                    <div class="strategy-card glass-panel" style="--card-accent: ${color};">
                        <div class="strat-header">
                            <span class="strat-badge">${escapeHtml(g.strategy)} (${comps.length})</span>
                        </div>
                        <h4>${escapeHtml(g.target_pattern)}</h4>
                        <p>${compStr || escapeHtml(g.rationale)}</p>
                    </div>
                `;
            }).join("");
        }

        // 4. Candidate Microservice Domains (Louvain Community Detection)
        const domainsGrid = document.getElementById("cockpit-domains-grid");
        if (domainsGrid && data.candidate_domains && data.candidate_domains.length > 0) {
            const domainIcons = ["🏥", "⚙️", "🗄️", "💳", "👤", "📦", "📊", "🔐", "🧩", "⚡"];
            domainsGrid.innerHTML = data.candidate_domains.map((dom, i) => {
                const icon = domainIcons[i % domainIcons.length];
                const members = dom.members || [];
                const memberStr = members.slice(0, 4).map(m => `<code>${escapeHtml(m)}</code>`).join(", ") + (members.length > 4 ? ` +${members.length - 4} more` : "");
                return `
                    <div class="domain-card">
                        <h5>${icon} ${escapeHtml(dom.domain_name || `Domain Cluster ${dom.community_id + 1}`)}</h5>
                        <p>Components (${members.length}): ${memberStr}</p>
                    </div>
                `;
            }).join("");
        }
    } catch (e) {
        console.warn("Cockpit loader notice:", e);
    }
}

// 8. Dynamic Rules & Provenance Table Loader
async function loadRulesData() {
    try {
        const res = await fetch("/api/rules");
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById("rules-table-body");
        if (!tbody) return;

        let rowsHtml = "";

        // Formalized Rules (BR-xx)
        if (data.rules && data.rules.length > 0) {
            rowsHtml += data.rules.map(r => `
                <tr data-type="rule">
                    <td><span class="id-badge rule">${escapeHtml(r.rule_id)}</span></td>
                    <td><strong>${escapeHtml(r.rule_name)}</strong><br><small>${escapeHtml(r.specification || r.condition_summary || "Enforces enterprise business constraint.")}</small></td>
                    <td class="mono">${escapeHtml(r.source_file || "")}</td>
                    <td class="mono">Lines ${r.line_start || 1}-${r.line_end || 1}</td>
                    <td class="mono hash">${escapeHtml((r.sha256 || "e3b0c442").slice(0, 10))}...</td>
                    <td><span class="status-tag verified">✓ Verified</span></td>
                </tr>
            `).join("");
        }

        // Discrepancies & Risks
        if (data.discrepancies && data.discrepancies.length > 0) {
            rowsHtml += data.discrepancies.map(d => `
                <tr data-type="risk">
                    <td><span class="id-badge risk">${escapeHtml(d.discrepancy_id)}</span></td>
                    <td><strong>${escapeHtml(d.title)}</strong><br><small>${escapeHtml(d.description)}</small></td>
                    <td class="mono">${escapeHtml(d.component || "System")}</td>
                    <td class="mono">Line-checked</td>
                    <td class="mono hash">Audit</td>
                    <td><span class="status-tag risk">⚠️ ${escapeHtml(d.severity || "Risk")}</span></td>
                </tr>
            `).join("");
        }

        if (rowsHtml) {
            tbody.innerHTML = rowsHtml;
            initRulesFilter();
        }
    } catch (e) {
        console.warn("Rules loader notice:", e);
    }
}

// 9. Load Raw JSON Export
async function loadJsonExport() {
    const jsonBox = document.getElementById("json-export-preview");
    if (!jsonBox) return;

    try {
        const res = await fetch("/artifacts/modernize_kg.json");
        if (res.ok) {
            const data = await res.json();
            jsonBox.textContent = JSON.stringify(data, null, 2);
        } else {
            jsonBox.textContent = "// Run ingestion to generate modernize_kg.json";
        }
    } catch (e) {
        jsonBox.textContent = "// Error loading graph JSON artifact.";
    }
}
