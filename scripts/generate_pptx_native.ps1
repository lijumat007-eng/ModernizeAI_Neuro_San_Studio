# ModernizeAI Native PowerPoint Generator (Uses Windows COM Object)
# Generates a professional 16:9 .pptx directly using Microsoft PowerPoint installed on your PC.

param(
    [string]$OutputPath = "$PSScriptRoot\..\artifacts\ModernizeAI_Native_Presentation.pptx"
)

$resolvedPath = [System.IO.Path]::GetFullPath($OutputPath)
Write-Host "Creating presentation at: $resolvedPath" -ForegroundColor Cyan

try {
    $pptApp = New-Object -ComObject PowerPoint.Application
} catch {
    Write-Warning "PowerPoint COM object could not be initialized. Please ensure Microsoft PowerPoint is installed."
    exit 1
}

$pptApp.Visible = [Microsoft.Office.Core.MsoTriState]::msoTrue
$pres = $pptApp.Presentations.Add()

# 16:9 Widescreen (960 x 540 pt)
$pres.PageSetup.SlideWidth = 960
$pres.PageSetup.SlideHeight = 540

# Add blank slide
$slide = $pres.Slides.Add(1, 12) # 12 = ppLayoutBlank
$slide.Background.Fill.Solid()
$slide.Background.Fill.ForeColor.RGB = 0x1D0F0A # #0a0f1d (BGR format in COM)

# Function to add card
function Add-Card($x, $y, $w, $h, $title, $bodyText) {
    $card = $slide.Shapes.AddShape(5, $x, $y, $w, $h) # 5 = msoShapeRoundedRectangle
    $card.Fill.Solid()
    $card.Fill.ForeColor.RGB = 0x2F1A12 # #121a2f
    $card.Line.ForeColor.RGB = 0xF8BD38 # #38bdf8
    $card.Line.Weight = 1
    
    $tf = $card.TextFrame
    $tf.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
    $tf.MarginLeft = 10
    $tf.MarginRight = 10
    $tf.MarginTop = 8
    
    $pTitle = $tf.TextRange.Paragraphs(1)
    $pTitle.Text = "$title`n"
    $pTitle.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
    $pTitle.Font.Size = 11
    $pTitle.Font.Color.RGB = 0xF8BD38
    
    $pBody = $tf.TextRange.InsertAfter($bodyText)
    $pBody.Font.Size = 8.5
    $pBody.Font.Color.RGB = 0xE2E8F0
}

# Header
$hdr = $slide.Shapes.AddTextbox(1, 20, 15, 920, 50)
$tfH = $hdr.TextFrame
$tfH.TextRange.Text = "ModernizeAI: Enterprise Legacy Modernization Platform"
$tfH.TextRange.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$tfH.TextRange.Font.Size = 17
$tfH.TextRange.Font.Color.RGB = 0xF8BD38

$subH = $tfH.TextRange.InsertAfter("`nAutonomous Hybrid Agentic Graph-RAG Swarm | Powered by Cognizant Neuro® AI Multi-Agent Accelerator")
$subH.Font.Size = 10
$subH.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoFalse
$subH.Font.Color.RGB = 0x94A3B8

# Row 1
Add-Card 20 75 295 190 "🎯 1. Description & Purpose" "• Solves the 70%+ failure rate in enterprise cloud migrations.`n• Reverse-engineers legacy Java/.NET/Oracle monoliths.`n• Built on Cognizant Neuro SAN Studio (11-agent mixture of experts).`n• Scale: 11 Agents | 5 Coded Tools | 5 Memory Tiers | 78/100 Readiness."
Add-Card 325 75 320 190 "💡 2. Innovation & Core Ideas" "• The 80/20 Rule: 80% deterministic AST/DDL extraction without hallucination + 20% LLM reasoning.`n• 5-Tier Memory: Raw, Structural, Semantic, Procedural, Transformation.`n• Schema-enforced MultiDiGraph with Louvain clustering for microservice domain boundaries."
Add-Card 655 75 285 190 "⚡ 3. Key Features Delivered" "• Dual UIs: Dedicated ModernizeAI Web App (PyVis 2D/3D graph) & nsflow Studio Visualizer.`n• Line-Level Business Rules: Formalized BR-01 to BR-05 with code citations.`n• Transitive Blast-Radius: Calculates ripple effects.`n• Sly-Data: Prevents proprietary data leaks to LLMs."

# Row 2
Add-Card 20 275 625 150 "🚀 4. Future Upgrades: Phase 2 Active Code Migration Swarm" "• KG Reader Agent: Ingests candidate microservice subgraphs from Knowledge Graph.`n• Cloud Scaffolder Agent: Generates containerized microservices and Helm/Terraform manifests.`n• Code Migrator Agent: Transpiles legacy .NET Framework (WCF/ADO.NET) to modern .NET 8/9 Minimal APIs.`n• SQL Decoupler & Test Synthesizer: Refactors stored proc row locks; synthesizes regression tests directly from rules."
Add-Card 655 275 285 150 "🏢 5. Benchmark Dataset" "• App: ClaimCore v2.4 (Insurance claims monolith).`n• Stack: Java JDBC, Oracle DDL, PL/SQL stored procs.`n• Verified Nodes: 21 nodes, 29 structural edges.`n• Discrepancy Discovery: Caught 15-day billing cutoff in SME notes conflicting with 30-day spec rule."

# Limitation Banner
$warn = $slide.Shapes.AddShape(5, 20, 435, 920, 75)
$warn.Fill.Solid()
$warn.Fill.ForeColor.RGB = 0x190F28 # Deep dark red
$warn.Line.ForeColor.RGB = 0x4E3FF4 # Red border
$warn.Line.Weight = 1.5

$tfW = $warn.TextFrame
$tfW.WordWrap = [Microsoft.Office.Core.MsoTriState]::msoTrue
$tfW.MarginLeft = 10
$tfW.MarginTop = 6
$pW1 = $tfW.TextRange.Paragraphs(1)
$pW1.Text = "⚠️ PRODUCTION & CORPORATE ENVIRONMENT LIMITATION (COGNIZANT LAPTOP RESTRICTION)`n"
$pW1.Font.Bold = [Microsoft.Office.Core.MsoTriState]::msoTrue
$pW1.Font.Size = 9.5
$pW1.Font.Color.RGB = 0x4E3FF4

$pW2 = $tfW.TextRange.InsertAfter("ModernizeAI requires external LLM API keys (OpenAI/Anthropic/Gemini) for the 20% LLM reasoning swarm. In the current corporate environment on Cognizant laptops, Zscaler (Scalar) blocks all external generative AI calls and API endpoints. Hence, live multi-agent chat and LLM generation cannot be executed or demoed locally without an external cloud sandbox or network proxy exemption.")
$pW2.Font.Size = 8.5
$pW2.Font.Color.RGB = 0xD3CDFE

# Save presentation
$pres.SaveAs($resolvedPath)
Write-Host "Presentation successfully created and saved at: $resolvedPath" -ForegroundColor Green
