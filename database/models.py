"""
Database models for the Essay Writer application
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and essay ownership"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    avatar_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    essays = db.relationship('Essay', backref='author', lazy=True, cascade='all, delete-orphan')
    agent_sessions = db.relationship('AgentSession', backref='user', lazy=True, cascade='all, delete-orphan')
    oauth_providers = db.relationship('UserOAuthProvider', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'providers': [provider.provider for provider in self.oauth_providers],
            'created_at': self.created_at.isoformat(),
            'essay_count': len(self.essays)
        }

class UserOAuthProvider(db.Model):
    """Model to track OAuth provider connections for users"""
    __tablename__ = 'user_oauth_providers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # 'google' or 'github'
    provider_id = db.Column(db.String(100), nullable=False)
    avatar_url = db.Column(db.String(200))  # Store provider-specific avatar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate provider connections
    __table_args__ = (db.UniqueConstraint('user_id', 'provider', name='_user_provider_uc'),
                      db.UniqueConstraint('provider', 'provider_id', name='_provider_id_uc'))
    
    def __repr__(self):
        return f'<UserOAuthProvider {self.provider}:{self.provider_id}>'

class Essay(db.Model):
    """Essay model to store user essays"""
    __tablename__ = 'essays'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(500), nullable=False)
    plan = db.Column(db.Text)
    draft = db.Column(db.Text)
    critique = db.Column(db.Text)
    final_essay = db.Column(db.Text)
    
    # Essay metadata
    status = db.Column(db.String(50), default='draft')  # draft, in_progress, completed
    revision_number = db.Column(db.Integer, default=1)
    word_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    agent_sessions = db.relationship('AgentSession', backref='essay', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Essay {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'topic': self.topic,
            'plan': self.plan,
            'draft': self.draft,
            'critique': self.critique,
            'final_essay': self.final_essay,
            'status': self.status,
            'revision_number': self.revision_number,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class AgentSession(db.Model):
    """Track agent execution sessions and state"""
    __tablename__ = 'agent_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    thread_id = db.Column(db.String(100), nullable=False)
    current_node = db.Column(db.String(50))
    next_node = db.Column(db.String(50))
    
    # Agent state data
    agent_state = db.Column(db.Text)  # JSON serialized state
    execution_log = db.Column(db.Text)  # Execution history
    
    # Session metadata
    status = db.Column(db.String(50), default='active')  # active, paused, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    essay_id = db.Column(db.Integer, db.ForeignKey('essays.id'), nullable=True)
    
    def __repr__(self):
        return f'<AgentSession {self.session_id}>'
    
    def get_state(self):
        """Deserialize agent state from JSON"""
        if self.agent_state:
            return json.loads(self.agent_state)
        return {}
    
    def set_state(self, state_dict):
        """Serialize agent state to JSON"""
        self.agent_state = json.dumps(state_dict)
        
    def add_log_entry(self, entry):
        """Add entry to execution log"""
        current_log = json.loads(self.execution_log) if self.execution_log else []
        current_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'entry': entry
        })
        self.execution_log = json.dumps(current_log)

class UserPreferences(db.Model):
    """User-specific preferences and settings"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Essay preferences
    default_max_revisions = db.Column(db.Integer, default=2)
    preferred_writing_style = db.Column(db.String(50), default='academic')
    auto_research = db.Column(db.Boolean, default=True)
    
    # API preferences
    preferred_model = db.Column(db.String(100), default='llama-3.3-70b-versatile')
    custom_prompts = db.Column(db.Text)  # JSON for custom prompts
    
    # UI preferences
    theme = db.Column(db.String(50), default='light')
    auto_save = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('preferences', uselist=False))
    
    def to_dict(self):
        return {
            'default_max_revisions': self.default_max_revisions,
            'preferred_writing_style': self.preferred_writing_style,
            'auto_research': self.auto_research,
            'preferred_model': self.preferred_model,
            'custom_prompts': json.loads(self.custom_prompts) if self.custom_prompts else {},
            'theme': self.theme,
            'auto_save': self.auto_save
        }
