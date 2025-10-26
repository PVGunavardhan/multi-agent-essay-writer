"""
Authentication components for Dash UI
"""
from dash import html, dcc
import dash_bootstrap_components as dbc

def login_layout():
    """Create the login page layout"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H1("Essay Writer AI", className="text-center mb-4", style={'color': '#2c3e50'}),
                        html.P("AI-powered essay writing with multi-agent collaboration", 
                               className="text-center text-muted mb-4"),
                        
                        html.Hr(),
                        
                        html.Div([
                            dbc.Button([
                                html.I(className="fab fa-google me-2"),
                                "Sign in with Google"
                            ], 
                            color="danger", 
                            href="/login/google",
                            external_link=True,
                            className="mb-3 w-100"),
                            
                            dbc.Button([
                                html.I(className="fab fa-github me-2"),
                                "Sign in with GitHub"
                            ], 
                            color="dark", 
                            href="/login/github",
                            external_link=True,
                            className="w-100"),
                        ]),
                        
                        html.Hr(className="mt-4"),
                        html.P([
                            "🔒 Secure OAuth authentication • ",
                            "💾 Your essays are saved • ",
                            "🚀 Multi-agent AI writing"
                        ], className="text-center small text-muted")
                    ])
                ], className="shadow")
            ], width=6, lg=4)
        ], justify="center", className="min-vh-100 align-items-center")
    ], fluid=True, className="login-bg")

def user_header(user_info):
    """Create user header component"""
    return dbc.Navbar([
        dbc.Container([
            dbc.NavbarBrand([
                html.I(className="fas fa-pen-fancy me-2"),
                "Essay Writer AI"
            ], className="fw-bold"),
            
            dbc.Nav([
                dbc.DropdownMenu([
                    dbc.DropdownMenuItem([
                        html.Div([
                            html.Img(src=user_info.get('avatar_url', ''), 
                                    className="rounded-circle me-2", 
                                    style={'width': '24px', 'height': '24px'}),
                            html.Div([
                                html.Span(user_info.get('name', 'User'), className="fw-bold"),
                                html.Small(f" via {user_info.get('provider', 'oauth').title()}", 
                                         className="text-muted d-block")
                            ], className="d-inline-block")
                        ], className="d-flex align-items-center")
                    ], header=True),
                    dbc.DropdownMenuItem(divider=True),
                    dbc.DropdownMenuItem("My Profile", href="#"),
                    dbc.DropdownMenuItem("Settings", href="#"),
                    dbc.DropdownMenuItem(divider=True),
                    dbc.DropdownMenuItem("Logout", href="/logout", external_link=True),
                ], 
                label=[
                    html.Div([
                        html.Img(src=user_info.get('avatar_url', ''), 
                                className="rounded-circle me-2", 
                                style={'width': '32px', 'height': '32px'}),
                        html.Span(user_info.get('name', 'User'), className="d-none d-md-inline"),
                        html.I(className=f"fab fa-{user_info.get('provider', 'user')} ms-1 text-muted",
                               style={'fontSize': '12px'})
                    ], className="d-flex align-items-center")
                ],
                nav=True)
            ], navbar=True, className="ms-auto")
        ], fluid=True)
    ], 
    # color="light", 
    className="mb-3")

def loading_spinner():
    """Create loading spinner component"""
    return dbc.Spinner([
        html.Div("Processing...", className="mt-3")
    ], color="primary")

def error_alert(message):
    """Create error alert component"""
    return dbc.Alert([
        html.I(className="fas fa-exclamation-triangle me-2"),
        message
    ], color="danger", dismissable=True)

def success_alert(message):
    """Create success alert component"""
    return dbc.Alert([
        html.I(className="fas fa-check-circle me-2"),
        message
    ], color="success", dismissable=True)

def info_alert(message):
    """Create info alert component"""
    return dbc.Alert([
        html.I(className="fas fa-info-circle me-2"),
        message
    ], color="info", dismissable=True)
