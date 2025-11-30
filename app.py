"""
Main Essay Writer Dash Application
Full-featured multi-agent essay writer with authentication, persistence, and user management
"""
import dash
from dash import dcc, html, Input, Output, State, callback, clientside_callback, ClientsideFunction, ctx, no_update
import dash_bootstrap_components as dbc
from flask import Flask, session, request, has_request_context, redirect
from flask_login import LoginManager, current_user, login_required
import os
from datetime import datetime
import json
import uuid
import threading

# Local imports
from database.models import db, User, Essay, AgentSession, UserPreferences
from auth.oauth import init_auth, require_auth
from components.auth_components import login_layout, user_header, loading_spinner, error_alert, success_alert
from components.agent_components import (
    create_agent_tab, create_plan_tab, create_research_tab, 
    create_draft_tab, create_history_tab, create_state_management_tab, 
    create_settings_tab, create_critique_tab
)
from core.essay_writer import EnhancedEssayWriter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask server
server = Flask(__name__)
server.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "super-secret-key-for-development-only")

# Database configuration - Use Supabase PostgreSQL in production, SQLite locally
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
if DATABASE_URL:
    # Supabase/PostgreSQL connection
    # Fix postgres:// to postgresql:// if needed (some platforms use old format)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    server.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Local development with SQLite
    server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///essay_writer.db'

server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration - Initially allow insecure for testing
server.config['SESSION_COOKIE_SECURE'] = False  # Will be updated based on HTTPS
server.config['SESSION_COOKIE_HTTPONLY'] = True
server.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
server.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
server.config['SESSION_TYPE'] = 'filesystem'

# Initialize database
db.init_app(server)

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__, 
    server=server,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True,
    title="Essay Writer AI"
)

# Initialize authentication
init_auth(server)

# Add a server-side route for the main page to handle authentication properly
@server.route('/')
def index():
    """Main route that handles authentication state"""
    from flask import session as flask_session
    
    print(f"=== Server Route Check ===")
    print(f"Session authenticated: {flask_session.get('user_authenticated', False)}")
    print(f"Session user_id: {flask_session.get('user_id', 'None')}")
    print(f"Session data: {dict(flask_session)}")
    
    try:
        flask_login_auth = current_user.is_authenticated
        print(f"Flask-Login authenticated: {flask_login_auth}")
        if flask_login_auth:
            print(f"Current user: {current_user.name}")
    except Exception as e:
        print(f"Flask-Login error: {e}")
    
    print(f"========================")
    
    # If authenticated, redirect to the Dash app with user data in URL
    if flask_session.get('user_authenticated', False):
        user_id = flask_session.get('user_id')
        return redirect(f"/app?user_id={user_id}")
    
    return app.index()

@server.route('/app')
def dash_app():
    """Serve the Dash app for authenticated users"""
    from flask import session as flask_session, request
    
    # Verify authentication
    if not flask_session.get('user_authenticated', False):
        return redirect('/')
    
    # Get user ID from URL parameter or session
    user_id = request.args.get('user_id') or flask_session.get('user_id')
    if not user_id:
        return redirect('/')
    
    print(f"Serving Dash app for user_id: {user_id}")
    return app.index()

@server.route('/debug-auth')
def debug_auth():
    """Debug route to check authentication state"""
    try:
        from flask import session as flask_session
        flask_login_auth = current_user.is_authenticated if hasattr(current_user, 'is_authenticated') else False
        flask_login_id = getattr(current_user, 'id', 'No ID')
        flask_login_name = getattr(current_user, 'name', 'No Name')
        
        session_auth = flask_session.get('user_authenticated', False)
        session_id = flask_session.get('user_id', 'No ID')
        session_name = flask_session.get('user_name', 'No Name')
        
        return f"""
        <h3>Authentication Debug</h3>
        <p><strong>Flask-Login:</strong> {flask_login_auth}, User ID: {flask_login_id}, Name: {flask_login_name}</p>
        <p><strong>Session:</strong> {session_auth}, User ID: {session_id}, Name: {session_name}</p>
        <p><strong>Session Data:</strong> {dict(flask_session)}</p>
        <p><a href="/">Back to App</a></p>
        """
    except Exception as e:
        return f"Auth Error: {str(e)}"

# Global agent instance (thread-safe)
essay_agent = EnhancedEssayWriter()
active_sessions = {}  # Store active agent sessions
session_lock = threading.Lock()

# Create tables
with server.app_context():
    db.create_all()

def is_authenticated():
    """Check if user is authenticated using multiple methods"""
    try:
        from flask import session as flask_session
        
        # Method 1: Check Flask session
        session_auth = flask_session.get('user_authenticated', False)
        print(f"Session auth check: {session_auth}")
        
        # Method 2: Check Flask-Login (if possible)
        flask_login_auth = False
        try:
            flask_login_auth = current_user.is_authenticated
            print(f"Flask-Login auth check: {flask_login_auth}")
        except Exception as e:
            print(f"Flask-Login check failed: {e}")
        
        # CRITICAL FIX: Require BOTH session data AND Flask-Login to be authenticated
        # This prevents the stale Flask-Login state after logout
        both_authenticated = session_auth and flask_login_auth
        
        # Additional validation: if Flask-Login says authenticated but no session data,
        # it means we have stale Flask-Login state - treat as not authenticated
        if flask_login_auth and not session_auth:
            print("WARNING: Flask-Login authenticated but no session data - treating as not authenticated")
            both_authenticated = False
        
        print(f"Final auth result: {both_authenticated}")
        return both_authenticated
        
    except Exception as e:
        print(f"Auth check error: {e}")
        return False

def get_current_user_info():
    """Get current user information from session or database"""
    try:
        from flask import session as flask_session
        
        # Try to get from session first
        if flask_session.get('user_authenticated', False):
            user_info = {
                'id': flask_session.get('user_id'),
                'name': flask_session.get('user_name'),
                'email': flask_session.get('user_email'),
                'avatar_url': flask_session.get('user_avatar_url'),
                'provider': flask_session.get('user_provider'),
                'created_at': flask_session.get('user_created_at', '')
            }
            print(f"Got user info from session: {user_info['name']}")
            return user_info
        
        # Fallback: try to get from database using session user_id
        # user_id = flask_session.get('user_id')
        # if user_id:
        #     with server.app_context():
        #         user = db.session.get(User, user_id)
        #         if user:
        #             user_info = {
        #                 'id': user.id,
        #                 'name': user.name,
        #                 'email': user.email,
        #                 'avatar_url': user.avatar_url,
        #                 'provider': user.provider,
        #                 'created_at': user.created_at.strftime("%B %d, %Y") if user.created_at else ""
        #             }
        #             print(f"Got user info from database: {user_info['name']}")
                    
        #             # Restore session data
        #             flask_session['user_authenticated'] = True
        #             flask_session['user_name'] = user.name
        #             flask_session['user_email'] = user.email
        #             flask_session['user_avatar_url'] = user.avatar_url
        #             flask_session['user_provider'] = user.provider
        #             flask_session['user_created_at'] = user_info['created_at']
                    
        #             return user_info
        
        print("No user info available from any source")
        return None
        
    except Exception as e:
        print(f"User info error: {e}")
        return None

# Main app layout - Static layout that handles both states
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
    dcc.Store(id="user-store"),
    dcc.Store(id="session-data-store")
])

@app.callback(
    [Output("page-content", "children"), Output("user-store", "data")],
    [Input("url", "pathname")]
)
def display_page(pathname):
    """Handle page routing and authentication"""
    
    print(f"=== Dash Callback ===")
    print(f"Display page called for path: {pathname}")
    
    # Get authentication status and user info
    authenticated = is_authenticated()
    user_info = get_current_user_info()
    
    print(f"Authentication check: {authenticated}")
    print(f"User info: {user_info}")
    print(f"================")
    
    if not authenticated or not user_info:
        print("Showing login layout")
        return login_layout(), None
    
    print(f"Showing main app for user: {user_info['name']}")
    
    # Main authenticated layout
    main_layout = html.Div([
        user_header(user_info),
        
        dbc.Container([
            dcc.Tabs(
                id="main-tabs",
                value="agent-tab",
                children=[
                    dcc.Tab(
                        label="🤖 Agent",
                        value="agent-tab",
                        children=[create_agent_tab()]
                    ),
                    dcc.Tab(
                        label="📋 Plan",
                        value="plan-tab",
                        children=[create_plan_tab()]
                    ),
                    dcc.Tab(
                        label="🔍 Research",
                        value="research-tab",
                        children=[create_research_tab()]
                    ),
                    dcc.Tab(
                        label="✍️ Draft",
                        value="draft-tab",
                        children=[create_draft_tab()]
                    ),
                    dcc.Tab(
                        label="🎯 Critique",
                        value="critique-tab",
                        children=[create_critique_tab()]
                    ),
                    dcc.Tab(
                        label="📚 My Essays",
                        value="history-tab",
                        children=[create_history_tab()]
                    ),
                    dcc.Tab(
                        label="⏰ Time Travel",
                        value="state-tab",
                        children=[create_state_management_tab()]
                    ),
                    dcc.Tab(
                        label="⚙️ Settings",
                        value="settings-tab",
                        children=[create_settings_tab(user_info)]
                    )
                ],
                className="custom-tabs"
            ),

            # Toast notifications for important events
            html.Div(id="notification-container"),
        ], fluid=True)
    ])
    
    return main_layout, user_info

# Generate essay callback
@app.callback(
    [
        Output("agent-output", "value"),
        Output("agent-status-badge", "children"),
        Output("agent-status-badge", "color"),
        Output("current-node-display", "children"),
        Output("next-node-display", "children"),
        Output("revision-display", "children"),
        Output("step-count-display", "children"),
        Output("thread-id-display", "children"),
        Output("session-store", "data"),
        Output("generate-icon", "children"),
        Output("stop-icon", "children")
    ],
    [
        Input("generate-btn", "n_clicks"),
        Input("stop-btn", "n_clicks")
    ],
    [
        State("topic-input", "value"),
        State("max-revisions-input", "value"),
        State("interrupt-after-checklist", "value"),
        State("session-store", "data"),
        State("agent-output", "value")
    ],
    prevent_initial_call=True
)
def handle_generate_execution(generate_clicks, stop_clicks, 
                            topic, max_revisions, interrupt_after, session_data, current_output):
    """Handle generate button execution and state management"""
    
    if not is_authenticated():
        return "Please log in first", "Unauthorized", "danger", "", "", "", "", "", None, no_update
    
    user_info = get_current_user_info()
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    with session_lock:
        try:
            if triggered_id == "generate-btn":
                # Debug: Print the interrupt_after settings received from UI
                print(f"🔧 Received interrupt_after from UI: {interrupt_after}")
                
                # Start new essay generation
                essay = Essay(
                    title=f"Essay: {topic[:50]}...",
                    topic=topic,
                    status='in_progress',
                    user_id=user_info['id']
                )
                db.session.add(essay)
                db.session.commit()
                
                session_id, thread_config, initial_state = essay_agent.create_session(
                    user_info['id'], essay.id, topic, max_revisions, interrupt_after
                )
                
                # Store session data
                session_data = {
                    'session_id': session_id,
                    'thread_config': thread_config,
                    'essay_id': essay.id,
                    'interrupt_after': interrupt_after
                }
                
                # Run first step
                result = essay_agent.run_step(thread_config, initial_state)
                
                if result['success']:
                    output = f"🚀 Started new essay generation!\n"
                    output += f"Topic: {topic}\n"
                    output += f"Session ID: {session_id}\n"
                    output += f"Current Step: {result['current_state'].get('lnode', 'unknown')}\n"
                    output += f"{'='*50}\n\n"
                    output += current_output or ""
                    
                    return (
                        output,
                        "Running",
                        "success",
                        result['current_state'].get('lnode', ''),
                        ', '.join(result['next_node']) if result['next_node'] else 'END',
                        str(result['current_state'].get('revision_number', 0)),
                        str(result['current_state'].get('count', 0)),
                        session_id[:8],
                        session_data,
                        no_update,
                        no_update
                    )
                else:
                    return (
                        f"❌ Error: {result['error']}",
                        "Error",
                        "danger",
                        "", "", "", "", "",
                        session_data,
                        no_update,
                        no_update
                    )
            
            elif triggered_id == "stop-btn":
                return (
                    (current_output or "") + "\n⏹️ Execution stopped by user.\n",
                    "Stopped",
                    "warning",
                    "", "", "", "", "",
                    session_data,
                    no_update,
                    no_update
                )
            
        except Exception as e:
            return (
                f"❌ Unexpected error: {str(e)}",
                "Error",
                "danger",
                "", "", "", "", "",
                session_data,
                no_update,
                no_update
            )
    
    # Default return
    return current_output or "", "Ready", "secondary", "", "", "", "", "", session_data, no_update, no_update

# Continue essay callback
@app.callback(
    [
        Output("agent-output", "value", allow_duplicate=True),
        Output("agent-status-badge", "children", allow_duplicate=True),
        Output("agent-status-badge", "color", allow_duplicate=True),
        Output("current-node-display", "children", allow_duplicate=True),
        Output("next-node-display", "children", allow_duplicate=True),
        Output("revision-display", "children", allow_duplicate=True),
        Output("step-count-display", "children", allow_duplicate=True),
        Output("thread-id-display", "children", allow_duplicate=True),
        Output("session-store", "data", allow_duplicate=True),
        Output("continue-icon", "children")
    ],
    [
        Input("continue-btn", "n_clicks")
    ],
    [
        State("session-store", "data"),
        State("agent-output", "value")
    ],
    prevent_initial_call=True
)
def handle_continue_execution(continue_clicks, session_data, current_output):
    """Handle continue button execution"""
    
    if not is_authenticated():
        return "Please log in first", "Unauthorized", "danger", "", "", "", "", "", None, no_update
    
    if not session_data:
        return "No active session to continue", "Error", "danger", "", "", "", "", "", None, no_update
    
    with session_lock:
        try:
            # Continue existing session
            thread_config = session_data['thread_config']
            result = essay_agent.run_step(thread_config)
            
            if result['success']:
                output = current_output or ""
                output += f"\n🔄 Continued execution...\n"
                output += f"Step: {result['current_state'].get('lnode', 'unknown')}\n"
                output += f"{'='*50}\n\n"
                
                next_nodes = result['next_node']
                if not next_nodes:
                    output += "✅ Essay generation completed!\n"
                    status = "Completed"
                    color = "success"
                else:
                    status = "Running"
                    color = "primary"
                
                return (
                    output,
                    status,
                    color,
                    result['current_state'].get('lnode', ''),
                    ', '.join(next_nodes) if next_nodes else 'END',
                    str(result['current_state'].get('revision_number', 0)),
                    str(result['current_state'].get('count', 0)),
                    session_data['session_id'][:8],
                    session_data,
                    no_update
                )
            else:
                return (
                    f"❌ Error: {result['error']}",
                    "Error",
                    "danger",
                    "", "", "", "", "",
                    session_data,
                    no_update
                )
                
        except Exception as e:
            return (
                f"❌ Unexpected error: {str(e)}",
                "Error",
                "danger",
                "", "", "", "", "",
                session_data,
                no_update
            )

# Reset callback
@app.callback(
    [
        Output("agent-output", "value", allow_duplicate=True),
        Output("agent-status-badge", "children", allow_duplicate=True),
        Output("agent-status-badge", "color", allow_duplicate=True),
        Output("current-node-display", "children", allow_duplicate=True),
        Output("next-node-display", "children", allow_duplicate=True),
        Output("revision-display", "children", allow_duplicate=True),
        Output("step-count-display", "children", allow_duplicate=True),
        Output("thread-id-display", "children", allow_duplicate=True),
        Output("session-store", "data", allow_duplicate=True),
        Output("reset-icon", "children")
    ],
    [
        Input("reset-btn", "n_clicks")
    ],
    [
        State("session-store", "data")
    ],
    prevent_initial_call=True
)
def handle_reset(n_clicks, session_data):
    """Handle reset button - clear session and UI state"""
    
    if not is_authenticated():
        return "Please log in first", "Unauthorized", "danger", "", "", "", "", "", None, no_update
    
    if n_clicks:
        # Reset session data
        reset_session_data = None
        
        return (
            "🔄 Session reset. Ready for new essay generation.\n",
            "Ready",
            "secondary", 
            "",
            "",
            "0",
            "0",
            "None",
            reset_session_data,
            no_update
        )
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, no_update

# Clear output callback
@app.callback(
    Output("agent-output", "value", allow_duplicate=True),
    Input("clear-output-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_output(n_clicks):
    if n_clicks:
        return ""
    return dash.no_update

# Plan management callbacks
@app.callback(
    [Output("plan-textarea", "value"), Output("refresh-plan-icon", "children")],
    [Input("refresh-plan-btn", "n_clicks")],
    [State("session-store", "data")],
    prevent_initial_call=True
)
def refresh_plan(n_clicks, session_data):
    """Refresh plan from agent state"""
    if not session_data or not is_authenticated():
        return "", no_update
    
    try:
        thread_config = session_data['thread_config']
        state = essay_agent.get_session_state(thread_config)
        return state.get('values', {}).get('plan', ''), no_update
    except:
        return "", no_update

@app.callback(
    [Output("plan-save-alert", "children"), Output("plan-save-alert", "color"), Output("plan-save-alert", "is_open"), Output("save-plan-icon", "children")],
    [Input("save-plan-btn", "n_clicks")],
    [State("plan-textarea", "value"), State("session-store", "data")],
    prevent_initial_call=True
)
def save_plan(n_clicks, plan_text, session_data):
    """Save plan changes"""
    if not n_clicks or not session_data or not is_authenticated():
        return "", "info", False, no_update
    
    try:
        thread_config = session_data['thread_config']
        result = essay_agent.update_state(thread_config, 'plan', plan_text, 'planner')
        
        if result.get('success'):
            return "✅ Plan saved successfully!", "success", True, no_update
        else:
            return f"❌ Error saving plan: {result.get('error')}", "danger", True, no_update
    except Exception as e:
        return f"❌ Error: {str(e)}", "danger", True, no_update

# Draft management callbacks
@app.callback(
    [Output("draft-textarea", "value"), Output("refresh-draft-icon", "children")],
    [Input("refresh-draft-btn", "n_clicks")],
    [State("session-store", "data")],
    prevent_initial_call=True
)
def refresh_draft(n_clicks, session_data):
    """Refresh draft from agent state"""
    if not session_data or not is_authenticated():
        return "", no_update
    
    try:
        thread_config = session_data['thread_config']
        state = essay_agent.get_session_state(thread_config)
        return state.get('values', {}).get('draft', ''), no_update
    except:
        return "", no_update

@app.callback(
    [Output("draft-save-alert", "children"), Output("draft-save-alert", "color"), Output("draft-save-alert", "is_open"), Output("save-draft-icon", "children")],
    [Input("save-draft-btn", "n_clicks")],
    [State("draft-textarea", "value"), State("session-store", "data")],
    prevent_initial_call=True
)
def save_draft(n_clicks, draft_text, session_data):
    """Save draft changes"""
    if not n_clicks or not session_data or not is_authenticated():
        return "", "info", False, no_update
    
    try:
        thread_config = session_data['thread_config']
        result = essay_agent.update_state(thread_config, 'draft', draft_text, 'generate')
        
        if result.get('success'):
            return "✅ Draft saved successfully!", "success", True, no_update
        else:
            return f"❌ Error saving draft: {result.get('error')}", "danger", True, no_update
    except Exception as e:
        return f"❌ Error: {str(e)}", "danger", True, no_update

# Critique management callbacks
@app.callback(
    [Output("critique-textarea", "value"), Output("refresh-critique-icon", "children")],
    [Input("refresh-critique-btn", "n_clicks")],
    [State("session-store", "data")],
    prevent_initial_call=True
)
def refresh_critique(n_clicks, session_data):
    """Refresh critique from agent state"""
    if not session_data or not is_authenticated():
        return "", no_update
    
    try:
        thread_config = session_data['thread_config']
        state = essay_agent.get_session_state(thread_config)
        return state.get('values', {}).get('critique', ''), no_update
    except:
        return "", no_update

# Research content callback
@app.callback(
    [Output("research-content-textarea", "value"), Output("research-queries-display", "children"), Output("refresh-research-icon", "children")],
    [Input("refresh-research-btn", "n_clicks")],
    [State("session-store", "data")],
    prevent_initial_call=True
)
def refresh_research(n_clicks, session_data):
    """Refresh research content from agent state"""
    if not session_data or not is_authenticated():
        return "", "", no_update
    
    try:
        thread_config = session_data['thread_config']
        state = essay_agent.get_session_state(thread_config)
        values = state.get('values', {})
        
        content = '\n\n'.join(values.get('content', []))
        queries = values.get('queries', [])
        
        queries_display = html.Div([
            html.H6("🔍 Research Queries:", className="fw-bold mb-2"),
            html.Ul([
                html.Li(query, className="small") for query in queries
            ]) if queries else html.P("No queries yet", className="text-muted small")
        ])
        
        return content, queries_display, no_update
    except:
        return "", "", no_update

# Essay history callbacks
@app.callback(
    Output("essays-list-container", "children"),
    [Input("main-tabs", "value"), Input("new-essay-btn", "n_clicks")],
    prevent_initial_call=True
)
def update_essays_list(active_tab, new_essay_clicks):
    """Update the essays list"""
    if active_tab != "history-tab" or not is_authenticated():
        return []
    
    user_info = get_current_user_info()
    essays = Essay.query.filter_by(user_id=user_info['id']).order_by(Essay.updated_at.desc()).all()
    
    if not essays:
        return dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "No essays yet. Create your first essay using the Agent tab!"
        ], color="info")
    
    essay_cards = []
    for essay in essays:
        card = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6(essay.title, className="card-title"),
                        html.P(essay.topic, className="card-text text-muted small"),
                    ], width=8),
                    dbc.Col([
                        dbc.Badge(essay.status.title(), 
                                color="success" if essay.status == "completed" else "primary",
                                className="mb-2"),
                        html.Br(),
                        html.Small(f"Rev: {essay.revision_number}", className="text-muted"),
                    ], width=2),
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button("View", id=f"view-essay-{essay.id}", color="outline-primary", size="sm"),
                            dbc.Button("Load", id=f"load-essay-{essay.id}", color="outline-success", size="sm"),
                            dbc.Button("Delete", id=f"delete-essay-{essay.id}", color="outline-danger", size="sm"),
                        ])
                    ], width=2)
                ]),
                html.Hr(),
                html.Small([
                    f"Created: {essay.created_at.strftime('%b %d, %Y')} • ",
                    f"Updated: {essay.updated_at.strftime('%b %d, %Y')} • ",
                    f"Words: {essay.word_count or 0}"
                ], className="text-muted")
            ])
        ], className="mb-3")
        essay_cards.append(card)
    
    return essay_cards

# State management callbacks
@app.callback(
    Output("state-snapshots-display", "value"),
    [Input("refresh-history-btn", "n_clicks")],
    [State("session-store", "data")],
    prevent_initial_call=True
)
def refresh_state_history(n_clicks, session_data):
    """Refresh state history display"""
    if not session_data or not is_authenticated():
        return "No active session"
    
    try:
        thread_config = session_data['thread_config']
        history = essay_agent.get_history(thread_config)
        
        if isinstance(history, dict) and 'error' in history:
            return f"Error loading history: {history['error']}"
        
        output = "State History:\n" + "="*50 + "\n\n"
        for i, state in enumerate(history):
            output += f"Step {state['step']}: {state['node']} -> {state['next_node']}\n"
            output += f"  Revision: {state['revision']}, Count: {state['count']}\n"
            output += f"  Timestamp: {state['timestamp']}\n\n"
        
        return output
    except Exception as e:
        return f"Error: {str(e)}"

# Enhanced UI callbacks for loading states and progress indicators
@app.callback(
    [
        Output("overall-progress", "style"),
        Output("overall-progress", "value"),
        Output("current-action-text", "children"),
        Output("output-overlay", "style"),
        Output("overlay-spinner-icon", "children")
    ],
    [
        Input("generate-btn", "n_clicks"),
        Input("continue-btn", "n_clicks"),
        Input("status-interval", "n_intervals")
    ],
    [
        State("session-store", "data")
    ],
    prevent_initial_call=True
)
def update_loading_states(generate_clicks, continue_clicks, n_intervals, session_data):
    """Update progress indicators (spinners are handled automatically by DBC)"""
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Default states
    progress_style = {"display": "none"}
    progress_value = 0
    action_text = "Ready"
    overlay_style = {"display": "none"}
    spinner_icon = no_update  # Don't show spinner when not active
    
    if triggered_id in ["generate-btn", "continue-btn"]:
        # Show progress indicators
        if triggered_id == "generate-btn":
            action_text = "Starting essay generation..."
        else:
            action_text = "Continuing workflow..."
            
        progress_style = {"display": "block"}
        progress_value = 10
        overlay_style = {"display": "block"}
        spinner_icon = no_update  # Trigger spinner
    
    elif session_data and n_intervals > 0:
        # Check if agent is running
        if session_data.get('status') == 'running':
            progress_style = {"display": "block"}
            progress_value = min(n_intervals * 5, 90)
            action_text = f"Processing step: {session_data.get('current_node', 'Unknown')}"
            overlay_style = {"display": "block"}
            spinner_icon = no_update  # Keep spinner active
    
    return (progress_style, progress_value, action_text, overlay_style, spinner_icon)

@app.callback(
    [
        Output("plan-word-count", "children"),
        Output("plan-char-count", "children"),
        Output("plan-last-updated", "children"),
        Output("draft-word-count", "children"),
        Output("draft-char-count", "children"),
        Output("draft-para-count", "children"),
        Output("draft-last-updated", "children"),
        Output("research-word-count", "children"),
        Output("sources-count", "children")
    ],
    [
        Input("plan-textarea", "value"),
        Input("draft-textarea", "value"),
        Input("research-content-textarea", "value")
    ],
    prevent_initial_call=True
)
def update_content_statistics(plan_content, draft_content, research_content):
    """Update word counts and other content statistics"""
    from datetime import datetime
    
    # Plan statistics
    plan_words = len(plan_content.split()) if plan_content else 0
    plan_chars = len(plan_content) if plan_content else 0
    
    # Draft statistics  
    draft_words = len(draft_content.split()) if draft_content else 0
    draft_chars = len(draft_content) if draft_content else 0
    draft_paras = len([p for p in draft_content.split('\n\n') if p.strip()]) if draft_content else 0
    
    # Research statistics
    research_words = len(research_content.split()) if research_content else 0
    sources = research_content.count('http') if research_content else 0
    
    current_time = datetime.now().strftime("%H:%M:%S")
    
    return (plan_words, plan_chars, current_time, draft_words, draft_chars, 
            draft_paras, current_time, research_words, sources)

@app.callback(
    Output("notification-container", "children"),
    [
        Input("save-plan-btn", "n_clicks"),
        Input("save-draft-btn", "n_clicks"),
        Input("export-draft-btn", "n_clicks")
    ],
    prevent_initial_call=True
)
def show_notifications(save_plan_clicks, save_draft_clicks, export_clicks):
    """Show toast notifications for user actions"""
    from components.agent_components import create_toast_notification
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    if triggered_id == "save-plan-btn":
        return create_toast_notification("Plan saved successfully! 📋", "success")
    elif triggered_id == "save-draft-btn":
        return create_toast_notification("Draft saved successfully! ✍️", "success")
    elif triggered_id == "export-draft-btn":
        return create_toast_notification("Draft exported! 📄", "info")
    
    return []

# Expose server for deployment
server = app.server

if __name__ == "__main__":
    # SSL Configuration
    ssl_context = None
    use_https = os.path.exists("certs/cert.pem") and os.path.exists("certs/key.pem")
    
    if use_https:
        ssl_context = ("certs/cert.pem", "certs/key.pem")
        server.config['SESSION_COOKIE_SECURE'] = True
        print("🔒 Running with HTTPS (SSL certificates found)")
        print("📝 App available at: https://localhost:8050")
    else:
        server.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP cookies
        print("⚠️  Running with HTTP (no SSL certificates found)")
        print("💡 Run 'python generate_cert.py' to create SSL certificates for HTTPS")
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        print("📝 App available at: http://localhost:8050")
    
    app.run(
        debug=os.environ.get('DASH_DEBUG', 'True').lower() == 'true', 
        host=os.environ.get('HOST', 'localhost'), 
        port=int(os.environ.get('PORT', 8050)), 
        ssl_context=ssl_context
    )
