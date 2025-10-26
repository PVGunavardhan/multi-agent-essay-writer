"""
Authentication module for the Essay Writer application
Handles OAuth integration and user management
"""
from flask import Flask, session, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized
from sqlalchemy.orm.exc import NoResultFound
from database.models import db, User, UserPreferences
from datetime import datetime
import os
import json

class OAuth(OAuthConsumerMixin, db.Model):
    """OAuth token storage model for Flask-Dance"""
    __tablename__ = 'flask_dance_oauth'
    
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    user = db.relationship("User")

def create_or_login_user(provider, provider_id, email, name, avatar_url):
    """Create or login user from OAuth data"""
    print("=== CREATE_OR_LOGIN_USER FUNCTION CALLED ===")
    print(f"Provider: {provider}")
    print(f"Provider ID: {provider_id}")
    print(f"Email: {email}")
    print(f"Name: {name}")
    print(f"Avatar URL: {avatar_url}")
    print(f"Current session before processing: {dict(session)}")
    
    try:
        # Import UserOAuthProvider
        from database.models import UserOAuthProvider
        
        # Validate input parameters
        if not email:
            print(f"WARNING: Email is empty, using fallback")
            email = f"{provider_id}@{provider}.local"
        
        if not name:
            print(f"WARNING: Name is empty, using provider_id")
            name = f"User_{provider_id}"
        
        print(f"Validated - Email: {email}, Name: {name}")
        
        # First, check if this specific provider connection already exists
        print("Checking if OAuth provider connection exists...")
        existing_provider = UserOAuthProvider.query.filter_by(
            provider=provider,
            provider_id=str(provider_id)
        ).first()
        
        if existing_provider:
            print(f"Found existing provider connection for user {existing_provider.user.email}")
            user = existing_provider.user
            # Update user info and provider-specific avatar
            user.name = name
            user.last_login = datetime.utcnow()
            
            # Update provider-specific avatar
            existing_provider.avatar_url = avatar_url
            
            db.session.commit()
            print("User info updated successfully")
        else:
            # Check if a user with this email exists (from any provider)
            print(f"Checking if user exists by email: {email}")
            existing_user = User.query.filter_by(email=email).first()
            
            if existing_user:
                print(f"Found existing user with email {email}, linking {provider} account")
                
                # Link the new provider to the existing user
                new_provider = UserOAuthProvider(
                    user_id=existing_user.id,
                    provider=provider,
                    provider_id=str(provider_id),
                    avatar_url=avatar_url
                )
                db.session.add(new_provider)
                
                # Update user info if needed
                if not existing_user.name and name:
                    existing_user.name = name
                if not existing_user.avatar_url and avatar_url:
                    existing_user.avatar_url = avatar_url
                existing_user.last_login = datetime.utcnow()
                
                db.session.commit()
                user = existing_user
                
                flash(f"Successfully linked your {provider.title()} account!", "success")
                print(f"Linked {provider} account to existing user {email}")
            else:
                print("No existing user found, creating new account...")
                # Create completely new user
                user = User(
                    email=email,
                    name=name,
                    avatar_url=avatar_url,
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow()
                )
                db.session.add(user)
                db.session.flush()  # Get the user ID
                
                # Create the OAuth provider connection
                oauth_provider = UserOAuthProvider(
                    user_id=user.id,
                    provider=provider,
                    provider_id=str(provider_id),
                    avatar_url=avatar_url
                )
                db.session.add(oauth_provider)
                
                print(f"New user created with ID: {user.id}")
                
                # Create default preferences
                preferences = UserPreferences(user_id=user.id)
                db.session.add(preferences)
                db.session.commit()
                
                flash(f"Welcome {name}! Your account has been created.", "success")
        
        # Login user with Flask-Login
        print("Attempting Flask-Login...")
        login_result = login_user(user, remember=True)
        print(f"Flask-Login result: {login_result}")
        print(f"Current user after login: {current_user}")
        print(f"Is authenticated: {current_user.is_authenticated}")
        
        # Store in session for Dash access
        print("Setting session variables...")
        session['user_authenticated'] = True
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        session['user_avatar_url'] = avatar_url  # Use current provider's avatar
        session['user_provider'] = provider  # Store current login provider
        session['user_created_at'] = user.created_at.strftime("%B %d, %Y") if user.created_at else ""
        session.permanent = True
        print(f"Session variables set: {dict(session)}")
        
        print(f"=== OAuth Success ===")
        print(f"User {name} logged in successfully")
        print(f"Session ID: {session.get('user_id')}")
        print(f"Flask-Login authenticated: {current_user.is_authenticated}")
        print(f"Session data: {dict(session)}")
        print(f"===================")
        
        return user  # Return user object instead of redirect
        
    except Exception as e:
        print(f"=== CRITICAL ERROR IN create_or_login_user ===")
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        print(f"=======================================")
        
        # Rollback any partial database changes
        try:
            db.session.rollback()
            print("Database session rolled back")
        except:
            pass
            
        flash(f"Authentication error: {str(e)}", "error")
        return None  # Return None instead of redirect

def init_auth(app: Flask):
    """Initialize authentication for the Flask app"""
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Point to our login route
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # OAuth Blueprints with proper SQLAlchemy storage
    google_bp = make_google_blueprint(
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        storage=SQLAlchemyStorage(OAuth, db.session, user=current_user)
    )
    
    github_bp = make_github_blueprint(
        client_id=os.environ.get("GITHUB_CLIENT_ID"),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET"),
        scope="user:email",
        storage=SQLAlchemyStorage(OAuth, db.session, user=current_user)
    )
    
    app.register_blueprint(google_bp, url_prefix="/login")
    app.register_blueprint(github_bp, url_prefix="/login")
    
    # Debug route to show all available routes
    @app.route("/auth/debug/routes")
    def debug_routes():
        """Debug route to show all available routes"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.endpoint}: {rule.rule}")
        return "<br>".join(routes)
    
    # OAuth authorized signal handlers
    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        """Handle Google OAuth callback via Flask-Dance signal"""
        print("=== GOOGLE OAUTH SIGNAL CALLBACK ===")
        print(f"Blueprint: {blueprint.name}")
        print(f"Token received: {token is not None}")
        print(f"Session before processing: {dict(session)}")
        
        if not token:
            print("No token received from Google")
            flash("Failed to log in with Google.", "error")
            return False
        
        try:
            # Use token directly for API call instead of blueprint.session
            import requests
            headers = {
                'Authorization': f"Bearer {token['access_token']}"
            }
            resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)
            
            if not resp.ok:
                print(f"Failed to fetch Google user info: {resp.text}")
                flash("Failed to fetch user info from Google", "error")
                return False
            
            user_info = resp.json()
            print(f"Google user info received: {user_info}")
            
            # Create or login user
            user = create_or_login_user(
                provider='google',
                provider_id=user_info['id'],
                email=user_info['email'],
                name=user_info['name'],
                avatar_url=user_info.get('picture', '')
            )
            
            if user:
                print(f"Google OAuth success for user: {user.id}")
                return False  # Let Flask-Dance handle token storage
            else:
                print("Failed to create/login user")
                flash("Authentication failed", "error")
                return False
                
        except Exception as e:
            print(f"Google OAuth signal error: {str(e)}")
            import traceback
            traceback.print_exc()
            flash("Google authentication error", "error")
            return False
    
    @oauth_authorized.connect_via(github_bp)
    def github_logged_in(blueprint, token):
        """Handle GitHub OAuth callback via Flask-Dance signal"""
        print("=== GITHUB OAUTH SIGNAL CALLBACK ===")
        print(f"Blueprint: {blueprint.name}")
        print(f"Token received: {token is not None}")
        print(f"Session before processing: {dict(session)}")
        
        if not token:
            print("No token received from GitHub")
            flash("Failed to log in with GitHub.", "error")
            return False
        
        try:
            # Use token directly for API call instead of blueprint.session
            import requests
            headers = {
                'Authorization': f"token {token['access_token']}",
                'User-Agent': 'Essay-Writer-App'
            }
            resp = requests.get("https://api.github.com/user", headers=headers)
            
            if not resp.ok:
                print(f"Failed to fetch GitHub user info: {resp.text}")
                flash("Failed to fetch user info from GitHub", "error")
                return False
            
            user_info = resp.json()
            print(f"GitHub user info received: {user_info}")
            
            # If email is null, try to get it from GitHub's email API
            email = user_info.get('email')
            if not email:
                print("Email not provided in user info, fetching from emails API...")
                email_resp = requests.get("https://api.github.com/user/emails", headers=headers)
                if email_resp.ok:
                    emails = email_resp.json()
                    print(f"GitHub emails response: {emails}")
                    # Find primary email or first verified email
                    for email_info in emails:
                        if email_info.get('primary', False) and email_info.get('verified', False):
                            email = email_info['email']
                            print(f"Found primary verified email: {email}")
                            break
                    # If no primary, take first verified email
                    if not email:
                        for email_info in emails:
                            if email_info.get('verified', False):
                                email = email_info['email']
                                print(f"Found verified email: {email}")
                                break
                else:
                    print(f"Failed to fetch emails: {email_resp.text}")
            
            # If still no email, create a placeholder
            if not email:
                email = f"{user_info['login']}@github.local"
                print(f"No email found, using placeholder: {email}")
            
            # Create or login user
            user = create_or_login_user(
                provider='github',
                provider_id=str(user_info['id']),
                email=email,
                name=user_info.get('name') or user_info['login'],
                avatar_url=user_info.get('avatar_url', '')
            )
            
            if user:
                print(f"GitHub OAuth success for user: {user.id}")
                return False  # Let Flask-Dance handle token storage
            else:
                print("Failed to create/login user")
                flash("Authentication failed", "error")
                return False
                
        except Exception as e:
            print(f"GitHub OAuth signal error: {str(e)}")
            import traceback
            traceback.print_exc()
            flash("GitHub authentication error", "error")
            return False
    
    # Test route to verify OAuth setup
    @app.route("/auth/test")
    def auth_test():
        print("=== AUTH TEST ROUTE CALLED ===")
        return "Auth routes are working!"
    
    # Login route for Flask-Login redirects
    @app.route("/auth/login")
    def auth_login():
        print("=== AUTH LOGIN ROUTE CALLED ===")
        print("Redirecting to main page for login")
        return redirect("/")
    
    @app.route("/logout")
    @login_required
    def logout():
        """Logout user and clear session"""
        print("=== LOGOUT ROUTE CALLED ===")
        print(f"Current user before logout: {current_user.id if current_user.is_authenticated else 'Anonymous'}")
        
        # Clear OAuth tokens from database if user exists
        # Clear Flask-Login
        logout_user()
        print("Flask-Login user logged out")
        
        # Clear all user session data
        session.pop('user_authenticated', None)
        session.pop('user_id', None)
        session.pop('user_name', None)
        session.pop('user_email', None)
        session.pop('user_avatar_url', None)
        session.pop('user_provider', None)
        session.pop('user_created_at', None)
        
        # Clear OAuth-specific session data
        session.pop('google_oauth_token', None)
        session.pop('github_oauth_token', None)
        session.pop('google_oauth_state', None)
        session.pop('github_oauth_state', None)
        
        # Clear any Flask-Dance specific session data
        for key in list(session.keys()):
            if 'oauth' in key.lower() or 'token' in key.lower():
                session.pop(key, None)
        
        print("All session data cleared")
        print(f"Session after logout: {dict(session)}")
        flash("You have been logged out successfully", "info")
        return redirect("/")
    
    return google_bp, github_bp

def require_auth(f):
    """Decorator to require authentication for Dash callbacks"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}
        return f(*args, **kwargs)
    return decorated_function
