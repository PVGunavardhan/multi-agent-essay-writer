"""
Main agent components for the Essay Writer Dash application
Replicates and enhances the Gradio functionality from helper.py
"""
from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
from datetime import datetime
import json

def create_step_indicator(step_id, label, color, active=False, completed=False):
    """Create a step indicator for the workflow progress"""
    icon_class = "fas fa-check-circle" if completed else "fas fa-circle"
    if active:
        icon_class = "fas fa-spinner fa-spin"
        color = "primary"
    elif completed:
        color = "success"
    
    # Use direct color values instead of CSS variables
    color_map = {
        "primary": "#0d6efd",
        "success": "#198754", 
        "secondary": "#6c757d",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "info": "#0dcaf0"
    }
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"{icon_class} fa-lg", style={"color": color_map.get(color, "#6c757d")}),
                html.Div(label, className="small mt-1 text-center")
            ], className="text-center")
        ], className="p-2")
    ], id=f"step-{step_id}", className=f"border-{color}", style={"minHeight": "70px"})

def create_toast_notification(message, type="info", duration=4000):
    """Create a toast notification for user feedback"""
    color_map = {
        "success": "success",
        "error": "danger", 
        "warning": "warning",
        "info": "info"
    }
    
    icon_map = {
        "success": "fas fa-check-circle",
        "error": "fas fa-exclamation-circle",
        "warning": "fas fa-exclamation-triangle", 
        "info": "fas fa-info-circle"
    }
    
    return dbc.Toast([
        html.I(className=f"{icon_map.get(type, 'fas fa-info-circle')} me-2"),
        message
    ],
    header="System Notification",
    icon=icon_map.get(type, "info"),
    duration=duration,
    is_open=True,
    style={"position": "fixed", "top": 20, "right": 20, "width": 350, "zIndex": 9999}
    )

def update_step_progress(current_step, completed_steps):
    """Update the step progress indicators"""
    steps = ["planner", "research_plan", "generate", "reflect", "research_critique", "final"]
    step_components = []
    
    for step in steps:
        is_completed = step in completed_steps
        is_active = step == current_step
        
        step_components.append(
            create_step_indicator(step, step.replace("_", " ").title(), 
                                "secondary", is_active, is_completed)
        )
    
    return step_components

def create_agent_tab():
    """Create the main agent control tab with enhanced UX and loading states"""
    return dbc.Container([
        # Essay topic and controls
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-robot me-2"),
                            "AI Essay Writer Agent"
                        ], className="mb-0 text-primary"),
                        dbc.Badge("Ready", id="agent-status-badge", color="secondary", className="ms-auto")
                    ], className="d-flex align-items-center"),
                    dbc.CardBody([
                        # Progress indicator at top
                        html.Div(id="progress-container", children=[
                            dbc.Progress(id="overall-progress", value=0, striped=True, animated=True, 
                                       className="mb-3", style={"height": "8px", "display": "none"})
                        ]),
                        
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Essay Topic:", className="fw-bold"),
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="topic-input",
                                        type="text",
                                        placeholder="Enter your essay topic (e.g., 'The Impact of AI on Education')",
                                        value="The Impact of Artificial Intelligence on Modern Education",
                                        className="mb-0"
                                    ),
                                    dbc.Button([
                                        html.I(className="fas fa-magic"),
                                    ], id="suggest-topic-btn", color="outline-secondary", 
                                       title="Get topic suggestions")
                                ], className="mb-3"),
                            ], width=8),
                            dbc.Col([
                                dbc.Label("Max Revisions:", className="fw-bold"),
                                dbc.Input(
                                    id="max-revisions-input",
                                    type="number",
                                    value=2,
                                    min=1,
                                    max=5,
                                    className="mb-3"
                                ),
                            ], width=4),
                        ]),
                        
                        # Enhanced control buttons with loading states
                        dbc.Row([
                            dbc.Col([
                                dbc.Button([
                                    html.Div([
                                        dbc.Spinner([
                                            html.I(className="fas fa-play me-2", id="generate-icon")
                                        ], size="sm", id="generate-spinner"),
                                        html.Span("Generate Essay")
                                    ], className="d-flex align-items-center justify-content-center")
                                ], id="generate-btn", color="primary", size="lg", className="px-3 w-100"),
                            ], width=3),
                            dbc.Col([
                                dbc.Button([
                                    html.Div([
                                        dbc.Spinner([
                                            html.I(className="fas fa-forward me-2", id="continue-icon")
                                        ], size="sm", id="continue-spinner"),
                                        html.Span("Continue")
                                    ], className="d-flex align-items-center justify-content-center")
                                ], id="continue-btn", color="success", size="lg", className="px-3 w-100"),
                            ], width=3),
                            dbc.Col([
                                dbc.Button([
                                    html.Div([
                                        dbc.Spinner([
                                            html.I(className="fas fa-stop me-2", id="stop-icon")
                                        ], size="sm", id="stop-spinner"),
                                        html.Span("Stop")
                                    ], className="d-flex align-items-center justify-content-center")
                                ], id="stop-btn", color="warning", size="lg", className="px-3 w-100"),
                            ], width=3),
                            dbc.Col([
                                dbc.Button([
                                    html.Div([
                                        dbc.Spinner([
                                            html.I(className="fas fa-redo me-2", id="reset-icon")
                                        ], size="sm", id="reset-spinner"),
                                        html.Span("Reset")
                                    ], className="d-flex align-items-center justify-content-center")
                                ], id="reset-btn", color="outline-secondary", size="lg", className="px-3 w-100"),
                            ], width=3),
                        ]),
                        
                        # Quick actions
                        html.Hr(),
                        dbc.Row([
                            dbc.Col([
                                html.Small("Quick Actions:", className="text-muted fw-bold me-2"),
                                dbc.ButtonGroup([
                                    dbc.Button("Save Draft", id="save-draft-btn", color="outline-info", size="sm"),
                                    dbc.Button("Export PDF", id="export-pdf-btn", color="outline-primary", size="sm"),
                                    dbc.Button("Share", id="share-btn", color="outline-success", size="sm"),
                                ], size="sm")
                            ])
                        ])
                    ])
                ], className="mb-4 shadow-sm")
            ], width=12)
        ]),
        
        # Enhanced agent status with step-by-step progress
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="fas fa-cogs me-2"),
                            "Agent Workflow Status"
                        ], className="mb-0"),
                        dbc.Badge("Ready", id="workflow-status-badge", color="secondary", className="ms-2")
                    ]),
                    dbc.CardBody([
                        # Step progress indicators (like Gradio app)
                        html.Div(id="step-progress-container", children=[
                            dbc.Row([
                                # Step indicators
                                dbc.Col([
                                    create_step_indicator("planner", "📋 Planning", "secondary", False),
                                ], width=2),
                                dbc.Col([
                                    create_step_indicator("research_plan", "🔍 Research", "secondary", False),
                                ], width=2),
                                dbc.Col([
                                    create_step_indicator("generate", "✍️ Writing", "secondary", False),
                                ], width=2),
                                dbc.Col([
                                    create_step_indicator("reflect", "🤔 Review", "secondary", False),
                                ], width=2),
                                dbc.Col([
                                    create_step_indicator("research_critique", "📚 Research+", "secondary", False),
                                ], width=2),
                                dbc.Col([
                                    create_step_indicator("final", "✅ Complete", "secondary", False),
                                ], width=2),
                            ], className="mb-3"),
                        ]),
                        
                        # Current status details
                        dbc.Row([
                            dbc.Col([
                                html.Small("Current Node:", className="text-muted d-block"),
                                html.Div("None", id="current-node-display", className="fw-bold text-primary")
                            ], width=2),
                            dbc.Col([
                                html.Small("Next Node:", className="text-muted d-block"),
                                html.Div("None", id="next-node-display", className="fw-bold text-info")
                            ], width=2),
                            dbc.Col([
                                html.Small("Revision:", className="text-muted d-block"),
                                html.Div("0", id="revision-display", className="fw-bold text-warning")
                            ], width=2),
                            dbc.Col([
                                html.Small("Step Count:", className="text-muted d-block"),
                                html.Div("0", id="step-count-display", className="fw-bold text-success")
                            ], width=2),
                            dbc.Col([
                                html.Small("Thread ID:", className="text-muted d-block"),
                                html.Div("None", id="thread-id-display", className="fw-bold small text-secondary")
                            ], width=2),
                            dbc.Col([
                                html.Small("Elapsed Time:", className="text-muted d-block"),
                                html.Div("00:00", id="elapsed-time-display", className="fw-bold text-dark")
                            ], width=2),
                        ]),
                        
                        html.Hr(),
                        
                        # Advanced controls (collapsible like Gradio)
                        dbc.Accordion([
                            dbc.AccordionItem([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Interrupt After Step:", className="fw-bold"),
                                        dbc.Checklist(
                                            id="interrupt-after-checklist",
                                            options=[
                                                {"label": " 📋 Planner", "value": "planner"},
                                                {"label": " 🔍 Research Plan", "value": "research_plan"},
                                                {"label": " ✍️ Generate", "value": "generate"},
                                                {"label": " 🤔 Reflect", "value": "reflect"},
                                                {"label": " 📚 Research Critique", "value": "research_critique"},
                                            ],
                                            value=["planner", "research_plan", "generate", "reflect", "research_critique"],
                                            inline=True,
                                            # style={"columnCount": "2"}
                                        )
                                    ], width=6),
                                    dbc.Col([
                                        dbc.Label("Agent Settings:", className="fw-bold"),
                                        dbc.Row([
                                            dbc.Col([
                                                dbc.Label("Temperature:", className="small"),
                                                dbc.Input(id="temperature-input", type="number", 
                                                        value=0, min=0, max=1, step=0.1, size="sm")
                                            ]),
                                            dbc.Col([
                                                dbc.Label("Max Tokens:", className="small"),
                                                dbc.Input(id="max-tokens-input", type="number", 
                                                        value=2000, min=100, max=4000, size="sm")
                                            ])
                                        ])
                                    ], width=6)
                                ])
                            ], title="⚙️ Advanced Settings", item_id="advanced-settings")
                        ], start_collapsed=True, className="mt-2")
                    ])
                ])
            ], width=12)
        ]),
        
        # Enhanced live agent output with tabs (like Gradio)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H5([
                            html.I(className="fas fa-terminal me-2"),
                            "Live Agent Output"
                        ], className="mb-0"),
                        dbc.ButtonGroup([
                            dbc.Button([
                                html.I(className="fas fa-broom me-1"),
                                "Clear"
                            ], id="clear-output-btn", color="outline-secondary", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-download me-1"),
                                "Export"
                            ], id="export-output-btn", color="outline-primary", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-pause me-1"),
                                "Pause"
                            ], id="pause-output-btn", color="outline-warning", size="sm"),
                        ], size="sm")
                    ], className="d-flex justify-content-between align-items-center"),
                    dbc.CardBody([
                        # Live output with syntax highlighting and auto-scroll
                        html.Div([
                            dcc.Textarea(
                                id="agent-output",
                                placeholder="🤖 Agent execution output will appear here...\n\nWaiting for commands...",
                                style={
                                    'width': '100%', 
                                    'height': '450px', 
                                    'fontFamily': 'Monaco, Consolas, "Courier New", monospace',
                                    'fontSize': '13px',
                                    'backgroundColor': '#f8f9fa',
                                    'border': '1px solid #dee2e6',
                                    'borderRadius': '8px',
                                    'padding': '12px',
                                    'resize': 'vertical'
                                },
                                className="border-0",
                                readOnly=True
                            ),
                            # Real-time status overlay
                            html.Div(id="output-overlay", style={"display": "none"}, children=[
                                dbc.Alert([
                                    dbc.Spinner([
                                        html.I(className="fas fa-cog", id="overlay-spinner-icon")
                                    ], size="sm", id="overlay-spinner"),
                                    html.Span(id="current-action-text", children="Processing...")
                                ], color="info", className="mb-0 position-absolute", 
                                style={"top": "10px", "right": "10px", "zIndex": "1000"})
                            ])
                        ], style={"position": "relative"})
                    ])
                ])
            ], width=12)
        ], className="mt-3"),
        
        # Hidden components for state management and real-time updates
        dcc.Store(id="session-store"),
        dcc.Store(id="agent-state-store"),
        dcc.Store(id="workflow-timing", data={"start_time": None, "elapsed": 0}),
        dcc.Interval(id="status-interval", interval=1000, n_intervals=0, disabled=True),
        dcc.Interval(id="progress-interval", interval=500, n_intervals=0, disabled=True),
        
    ], fluid=True)

def create_plan_tab():
    """Create the enhanced plan editing tab with Gradio-like functionality"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-clipboard-list me-2"),
                            "Essay Plan Editor"
                        ], className="mb-0 text-primary"),
                        dbc.ButtonGroup([
                            dbc.Button([
                                dbc.Spinner([
                                    html.I(className="fas fa-sync me-2", id="refresh-plan-icon")
                                ], size="sm", id="refresh-plan-spinner"),
                                "Refresh"
                            ], id="refresh-plan-btn", color="outline-primary", size="sm"),
                            dbc.Button([
                                dbc.Spinner([
                                    html.I(className="fas fa-save me-2", id="save-plan-icon")
                                ], size="sm", id="save-plan-spinner"),
                                "Save Changes"
                            ], id="save-plan-btn", color="success", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-magic me-2"),
                                "Regenerate"
                            ], id="regenerate-plan-btn", color="warning", size="sm"),
                        ])
                    ], className="d-flex justify-content-between align-items-center"),
                    dbc.CardBody([
                        # Plan status indicator
                        dbc.Alert([
                            html.I(className="fas fa-info-circle me-2"),
                            html.Span(id="plan-status-text", children="No plan generated yet. Run the planning agent to create one.")
                        ], id="plan-status-alert", color="info", className="mb-3"),
                        
                        # Interactive plan editor
                        html.Div([
                            dbc.Label("Plan Content:", className="fw-bold mb-2"),
                            dbc.Textarea(
                                id="plan-textarea",
                                placeholder="📝 Essay plan will appear here after running the planner agent...\n\nYou can edit the plan manually and save changes to influence the essay generation.",
                                style={
                                    'height': '400px',
                                    'fontFamily': 'Monaco, Consolas, "Courier New", monospace',
                                    'fontSize': '14px'
                                },
                                className="border-2"
                            ),
                            
                            # Plan metadata
                            dbc.Row([
                                dbc.Col([
                                    html.Small("Last Updated:", className="text-muted"),
                                    html.Div(id="plan-last-updated", className="small fw-bold")
                                ], width=4),
                                dbc.Col([
                                    html.Small("Word Count:", className="text-muted"),
                                    html.Div(id="plan-word-count", className="small fw-bold")
                                ], width=4),
                                dbc.Col([
                                    html.Small("Character Count:", className="text-muted"),
                                    html.Div(id="plan-char-count", className="small fw-bold")
                                ], width=4),
                            ], className="mt-2"),
                        ]),
                        
                        html.Hr(),
                        
                        # Plan actions and tools
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Plan Tools:", className="fw-bold small"),
                                dbc.ButtonGroup([
                                    dbc.Button("📋 Copy", id="copy-plan-btn", color="outline-secondary", size="sm"),
                                    dbc.Button("📤 Export", id="export-plan-btn", color="outline-info", size="sm"),
                                    dbc.Button("🔄 Revert", id="revert-plan-btn", color="outline-warning", size="sm"),
                                ], size="sm")
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Plan Quality:", className="fw-bold small"),
                                html.Div(id="plan-quality-indicator", children=[
                                    dbc.Progress(value=0, id="plan-quality-progress", className="small")
                                ])
                            ], width=6)
                        ]),
                        
                        # Success/Error alerts
                        dbc.Alert(
                            id="plan-save-alert",
                            is_open=False,
                            dismissable=True,
                            duration=3000
                        )
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)

def create_research_tab():
    """Create the enhanced research content tab with detailed insights"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-search me-2"),
                            "Research Intelligence Hub"
                        ], className="mb-0 text-info"),
                        dbc.ButtonGroup([
                            dbc.Button([
                                dbc.Spinner([
                                    html.I(className="fas fa-sync me-2", id="refresh-research-icon")
                                ], size="sm", id="refresh-research-spinner"),
                                "Refresh"
                            ], id="refresh-research-btn", color="outline-primary", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-download me-2"),
                                "Export Research"
                            ], id="export-research-btn", color="outline-success", size="sm"),
                        ])
                    ], className="d-flex justify-content-between align-items-center"),
                    dbc.CardBody([
                        # Research status and statistics
                        dbc.Row([
                            dbc.Col([
                                dbc.Alert([
                                    html.I(className="fas fa-lightbulb me-2"),
                                    html.Span(id="research-status-text", 
                                             children="Research content is automatically gathered by AI agents based on your essay topic and current writing phase.")
                                ], id="research-status-alert", color="info", className="mb-3"),
                            ], width=12)
                        ]),
                        
                        # Research queries section (like Gradio)
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-question-circle me-2"),
                                    "Research Queries"
                                ], className="mb-0")
                            ]),
                            dbc.CardBody([
                                html.Div(id="research-queries-display", children=[
                                    dbc.Alert("No research queries generated yet.", color="light", className="text-center")
                                ])
                            ])
                        ], className="mb-3"),
                        
                        # Research content with enhanced display
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-book me-2"),
                                    "Research Content"
                                ], className="mb-0"),
                                html.Div(id="research-stats", className="small text-muted")
                            ], className="d-flex justify-content-between align-items-center"),
                            dbc.CardBody([
                                dbc.Textarea(
                                    id="research-content-textarea",
                                    placeholder="🔍 Research content will appear here after the research agents run...\n\nThe AI will automatically search for relevant information to support your essay.",
                                    style={
                                        'height': '400px',
                                        'fontFamily': 'Monaco, Consolas, "Courier New", monospace',
                                        'fontSize': '13px'
                                    },
                                    readOnly=True
                                ),
                                
                                # Research quality indicators
                                html.Hr(),
                                dbc.Row([
                                    dbc.Col([
                                        html.Small("Sources Found:", className="text-muted"),
                                        html.Div(id="sources-count", className="fw-bold text-primary")
                                    ], width=3),
                                    dbc.Col([
                                        html.Small("Content Quality:", className="text-muted"),
                                        dbc.Progress(id="content-quality-progress", value=0, className="small")
                                    ], width=4),
                                    dbc.Col([
                                        html.Small("Relevance Score:", className="text-muted"),
                                        html.Div(id="relevance-score", className="fw-bold text-success")
                                    ], width=3),
                                    dbc.Col([
                                        html.Small("Word Count:", className="text-muted"),
                                        html.Div(id="research-word-count", className="fw-bold text-info")
                                    ], width=2),
                                ])
                            ])
                        ])
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)

def create_draft_tab():
    """Create the enhanced draft editing tab with comprehensive writing tools"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-edit me-2"),
                            "Essay Draft Editor"
                        ], className="mb-0 text-success"),
                        dbc.ButtonGroup([
                            dbc.Button([
                                dbc.Spinner([
                                    html.I(className="fas fa-sync me-2", id="refresh-draft-icon")
                                ], size="sm", id="refresh-draft-spinner"),
                                "Refresh"
                            ], id="refresh-draft-btn", color="outline-primary", size="sm"),
                            dbc.Button([
                                dbc.Spinner([
                                    html.I(className="fas fa-save me-2", id="save-draft-icon")
                                ], size="sm", id="save-draft-spinner"),
                                "Save Changes"
                            ], id="save-draft-btn", color="success", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-download me-2"),
                                "Export"
                            ], id="export-draft-btn", color="info", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-magic me-2"),
                                "Regenerate"
                            ], id="regenerate-draft-btn", color="warning", size="sm"),
                        ])
                    ], className="d-flex justify-content-between align-items-center"),
                    dbc.CardBody([
                        # Draft status and metadata
                        dbc.Row([
                            dbc.Col([
                                dbc.Alert([
                                    html.I(className="fas fa-pencil-alt me-2"),
                                    html.Span(id="draft-info-text", 
                                             children="Essay draft will be generated by the AI writing agent. You can edit and refine it here.")
                                ], id="draft-info-alert", color="success", className="mb-3"),
                            ], width=8),
                            dbc.Col([
                                # Draft statistics
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("Draft Stats", className="card-title small"),
                                        html.Div([
                                            html.Small("Words: ", className="text-muted"),
                                            html.Span(id="draft-word-count", className="fw-bold text-primary")
                                        ], className="small"),
                                        html.Div([
                                            html.Small("Characters: ", className="text-muted"),
                                            html.Span(id="draft-char-count", className="fw-bold text-info")
                                        ], className="small"),
                                        html.Div([
                                            html.Small("Paragraphs: ", className="text-muted"),
                                            html.Span(id="draft-para-count", className="fw-bold text-success")
                                        ], className="small"),
                                    ], className="p-2")
                                ], className="border-0 bg-light")
                            ], width=4)
                        ]),
                        
                        # Enhanced text editor
                        html.Div([
                            dbc.Label("Draft Content:", className="fw-bold mb-2"),
                            dbc.Textarea(
                                id="draft-textarea",
                                placeholder="✍️ Essay draft will appear here after the generation agent runs...\n\nYou can edit the draft manually and save changes. The AI will use your edits for future revisions.",
                                style={
                                    'height': '450px',
                                    'fontFamily': 'Georgia, "Times New Roman", serif',
                                    'fontSize': '16px',
                                    'lineHeight': '1.6'
                                },
                                className="border-2"
                            ),
                        ]),
                        
                        html.Hr(),
                        
                        # Writing tools and analysis
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Writing Tools:", className="fw-bold small"),
                                dbc.ButtonGroup([
                                    dbc.Button("📊 Analyze", id="analyze-draft-btn", color="outline-info", size="sm"),
                                    dbc.Button("🔍 Check Grammar", id="grammar-check-btn", color="outline-warning", size="sm"),
                                    dbc.Button("📝 Format", id="format-draft-btn", color="outline-secondary", size="sm"),
                                ], size="sm")
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Draft Quality:", className="fw-bold small"),
                                html.Div([
                                    dbc.Progress(
                                        id="draft-quality-progress", 
                                        value=0, 
                                        label="",
                                        className="small",
                                        style={"height": "20px"}
                                    )
                                ])
                            ], width=6)
                        ]),
                        
                        # Last updated info
                        html.Div([
                            html.Small("Last Updated: ", className="text-muted"),
                            html.Span(id="draft-last-updated", className="small fw-bold")
                        ], className="mt-2"),
                        
                        # Save status alert
                        dbc.Alert(
                            id="draft-save-alert",
                            is_open=False,
                            dismissable=True,
                            duration=3000
                        )
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)

def create_critique_tab():
    """Create the enhanced critique tab with detailed feedback analysis"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4([
                            html.I(className="fas fa-eye me-2"),
                            "AI Essay Critique & Feedback"
                        ], className="mb-0 text-warning"),
                        dbc.ButtonGroup([
                            dbc.Button([
                                dbc.Spinner([
                                    html.I(className="fas fa-sync me-2", id="refresh-critique-icon")
                                ], size="sm", id="refresh-critique-spinner"),
                                "Refresh"
                            ], id="refresh-critique-btn", color="outline-primary", size="sm"),
                            dbc.Button([
                                dbc.Spinner([
                                    html.I(className="fas fa-save me-2", id="save-critique-icon")
                                ], size="sm", id="save-critique-spinner"),
                                "Save Changes"
                            ], id="save-critique-btn", color="success", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-magic me-2"),
                                "Re-analyze"
                            ], id="reanalyze-critique-btn", color="warning", size="sm"),
                        ])
                    ], className="d-flex justify-content-between align-items-center"),
                    dbc.CardBody([
                        # Critique status and summary
                        dbc.Row([
                            dbc.Col([
                                dbc.Alert([
                                    html.I(className="fas fa-graduation-cap me-2"),
                                    html.Span(id="critique-status-text", 
                                             children="AI critique will analyze your essay and provide detailed feedback for improvement.")
                                ], id="critique-status-alert", color="warning", className="mb-3"),
                            ], width=8),
                            dbc.Col([
                                # Critique summary
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H6("Overall Score", className="card-title small"),
                                        html.Div([
                                            dbc.Progress(
                                                id="overall-score-progress", 
                                                value=0, 
                                                label="0%",
                                                className="mb-2",
                                                style={"height": "25px"}
                                            )
                                        ]),
                                        html.Div([
                                            html.Small("Grade: ", className="text-muted"),
                                            html.Span(id="essay-grade", className="fw-bold text-primary")
                                        ], className="small"),
                                    ], className="p-2")
                                ], className="border-0 bg-light")
                            ], width=4)
                        ]),
                        
                        # Critique categories
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("📝 Content & Structure", className="py-2"),
                                    dbc.CardBody([
                                        dbc.Progress(id="content-score", value=0, label="0%", className="small")
                                    ], className="py-2")
                                ])
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("🎨 Style & Flow", className="py-2"),
                                    dbc.CardBody([
                                        dbc.Progress(id="style-score", value=0, label="0%", className="small")
                                    ], className="py-2")
                                ])
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("📚 Evidence & Research", className="py-2"),
                                    dbc.CardBody([
                                        dbc.Progress(id="evidence-score", value=0, label="0%", className="small")
                                    ], className="py-2")
                                ])
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader("✅ Grammar & Mechanics", className="py-2"),
                                    dbc.CardBody([
                                        dbc.Progress(id="grammar-score", value=0, label="0%", className="small")
                                    ], className="py-2")
                                ])
                            ], width=3),
                        ], className="mb-3"),
                        
                        # Detailed critique content
                        html.Div([
                            dbc.Label("Detailed Critique & Recommendations:", className="fw-bold mb-2"),
                            dbc.Textarea(
                                id="critique-textarea",
                                placeholder="🎯 Essay critique will appear here after the reflection agent runs...\n\nThe AI teacher will provide detailed feedback on:\n• Content quality and organization\n• Writing style and clarity\n• Use of evidence and examples\n• Grammar and mechanics\n• Specific recommendations for improvement",
                                style={
                                    'height': '400px',
                                    'fontFamily': 'Monaco, Consolas, "Courier New", monospace',
                                    'fontSize': '14px'
                                },
                                className="border-2"
                            ),
                        ]),
                        
                        html.Hr(),
                        
                        # Action items from critique
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Key Action Items:", className="fw-bold small"),
                                html.Div(id="action-items-list", children=[
                                    dbc.Alert("No action items yet - critique will generate specific recommendations.", 
                                             color="light", className="small")
                                ])
                            ], width=8),
                            dbc.Col([
                                dbc.Label("Improvement Priority:", className="fw-bold small"),
                                html.Div(id="improvement-priority", children=[
                                    dbc.Badge("Content", color="primary", className="me-1"),
                                    dbc.Badge("Structure", color="secondary", className="me-1"),
                                    dbc.Badge("Style", color="info"),
                                ])
                            ], width=4)
                        ]),
                        
                        # Save status
                        dbc.Alert(
                            id="critique-save-alert",
                            is_open=False,
                            dismissable=True,
                            duration=3000
                        )
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)

def create_history_tab():
    """Create the essay history tab"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("📚 My Essays", className="mb-0"),
                        dbc.Button([
                            html.I(className="fas fa-plus me-2"),
                            "New Essay"
                        ], id="new-essay-btn", color="primary", size="sm")
                    ]),
                    dbc.CardBody([
                        html.Div(id="essays-list-container"),
                        
                        # Essay details modal
                        dbc.Modal([
                            dbc.ModalHeader(dbc.ModalTitle(id="essay-modal-title")),
                            dbc.ModalBody(id="essay-modal-body"),
                            dbc.ModalFooter([
                                dbc.Button("Close", id="close-essay-modal", color="secondary"),
                                dbc.Button("Load Essay", id="load-essay-btn", color="primary"),
                            ])
                        ], id="essay-modal", size="lg")
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)

def create_state_management_tab():
    """Create the state management and time travel tab"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("⏰ Time Travel & State Management", className="mb-0"),
                        dbc.Button([
                            html.I(className="fas fa-sync me-2"),
                            "Refresh History"
                        ], id="refresh-history-btn", color="outline-primary", size="sm")
                    ]),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Select Thread:", className="fw-bold"),
                                dcc.Dropdown(
                                    id="thread-selector",
                                    placeholder="Select a thread...",
                                    className="mb-3"
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Select State Snapshot:", className="fw-bold"),
                                dcc.Dropdown(
                                    id="state-snapshot-selector",
                                    placeholder="Select a state to restore...",
                                    className="mb-3"
                                )
                            ], width=6),
                        ]),
                        
                        dbc.Row([
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="fas fa-undo me-2"),
                                    "Restore State"
                                ], id="restore-state-btn", color="warning", className="me-2"),
                                dbc.Button([
                                    html.I(className="fas fa-history me-2"),
                                    "View Full History"
                                ], id="view-history-btn", color="info"),
                            ])
                        ]),
                        
                        html.Hr(),
                        
                        # State snapshots display
                        html.Div([
                            html.H6("📸 State Snapshots:", className="fw-bold"),
                            dcc.Textarea(
                                id="state-snapshots-display",
                                placeholder="State history will appear here...",
                                style={'height': '400px'},
                                className="font-monospace",
                                readOnly=True
                            )
                        ])
                    ])
                ])
            ], width=12)
        ])
    ], fluid=True)

def create_settings_tab(user_info):
    """Create the settings and preferences tab"""
    return dbc.Container([
        dbc.Row([
            # User Profile
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("👤 User Profile")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Img(
                                    src=user_info.get('avatar_url', ''),
                                    className="rounded-circle",
                                    style={'width': '80px', 'height': '80px'}
                                )
                            ], width="auto"),
                            dbc.Col([
                                html.H6(user_info.get('name', 'User'), className="mb-1"),
                                html.P(user_info.get('email', ''), className="text-muted mb-1"),
                                dbc.Badge(f"via {user_info.get('provider', '').title()}", color="secondary"),
                            ])
                        ]),
                        html.Hr(),
                        dbc.Row([
                            dbc.Col([
                                html.Small("Member since:", className="text-muted"),
                                html.Div(user_info.get('created_at', ''), className="small")
                            ], width=6),
                            dbc.Col([
                                html.Small("Essays written:", className="text-muted"),
                                html.Div(id="user-essay-count", className="small fw-bold")
                            ], width=6),
                        ])
                    ])
                ])
            ], width=6),
            
            # Writing Preferences
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("⚙️ Writing Preferences")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Default Max Revisions:"),
                                dbc.Input(
                                    id="pref-max-revisions",
                                    type="number",
                                    value=2,
                                    min=1,
                                    max=5,
                                    className="mb-3"
                                )
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Writing Style:"),
                                dcc.Dropdown(
                                    id="pref-writing-style",
                                    options=[
                                        {"label": "Academic", "value": "academic"},
                                        {"label": "Casual", "value": "casual"},
                                        {"label": "Professional", "value": "professional"},
                                        {"label": "Creative", "value": "creative"}
                                    ],
                                    value="academic",
                                    className="mb-3"
                                )
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("AI Model:"),
                                dcc.Dropdown(
                                    id="pref-ai-model",
                                    options=[
                                        {"label": "Llama 3.3 70B (Recommended)", "value": "llama-3.3-70b-versatile"},
                                        {"label": "Llama 3.1 8B", "value": "llama-3.1-8b-instant"},
                                        {"label": "Mixtral 8x7B", "value": "mixtral-8x7b-32768"},
                                    ],
                                    value="llama-3.3-70b-versatile",
                                    className="mb-3"
                                )
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Checklist(
                                    id="pref-auto-research",
                                    options=[{"label": "Auto-research topics", "value": "enabled"}],
                                    value=["enabled"],
                                    className="mb-3"
                                )
                            ])
                        ]),
                        dbc.Button("Save Preferences", id="save-preferences-btn", color="primary")
                    ])
                ])
            ], width=6)
        ]),
        
        # API Configuration
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("🔑 API Configuration")),
                    dbc.CardBody([
                        dbc.Alert([
                            html.I(className="fas fa-shield-alt me-2"),
                            "API keys are stored securely and never shared."
                        ], color="info", className="mb-3"),
                        
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Groq API Key:"),
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="groq-api-key",
                                        type="password",
                                        placeholder="Enter your Groq API key...",
                                    ),
                                    dbc.Button("Test", id="test-groq-btn", color="outline-secondary")
                                ], className="mb-3")
                            ])
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Tavily API Key:"),
                                dbc.InputGroup([
                                    dbc.Input(
                                        id="tavily-api-key",
                                        type="password",
                                        placeholder="Enter your Tavily API key...",
                                    ),
                                    dbc.Button("Test", id="test-tavily-btn", color="outline-secondary")
                                ], className="mb-3")
                            ])
                        ]),
                        
                        dbc.Button("Save API Keys", id="save-api-keys-btn", color="success")
                    ])
                ])
            ], width=12)
        ], className="mt-3")
    ], fluid=True)
