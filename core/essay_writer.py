"""
Enhanced Essay Writer with user management and persistence
Based on the original helper.py but enhanced for multi-user support
"""
import warnings
warnings.filterwarnings("ignore", message=".*TqdmWarning.*")

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Optional
import operator
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from langchain_groq import ChatGroq
from pydantic.v1 import BaseModel
from tavily import TavilyClient
import os
import sqlite3
import json
from datetime import datetime
import uuid

class AgentState(TypedDict):
    task: str
    lnode: str
    plan: str
    draft: str
    critique: str
    content: List[str]
    queries: List[str]
    revision_number: int
    max_revisions: int
    count: Annotated[int, operator.add]
    user_id: Optional[int]
    essay_id: Optional[int]
    session_id: Optional[str]

class Queries(BaseModel):
    queries: List[str]

class EnhancedEssayWriter:
    """Enhanced essay writer with user management and persistence"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        self.tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        
        # Build base graph structure (will be recompiled with dynamic interrupts)
        self.builder = self._build_graph_structure()
        self.base_graph = None  # Will be compiled dynamically
        
        # Prompts
        self.PLAN_PROMPT = (
            "You are an expert writer tasked with writing a high level outline of a short 3 paragraph essay. "
            "Write such an outline for the user provided topic. Give the three main headers of an outline of "
            "the essay along with any relevant notes or instructions for the sections."
        )
        
        self.WRITER_PROMPT = (
            "You are an essay assistant tasked with writing excellent 3 paragraph essays. "
            "Generate the best essay possible for the user's request and the initial outline. "
            "If the user provides critique, respond with a revised version of your previous attempts. "
            "Utilize all the information below as needed: \n"
            "------\n"
            "{content}"
        )
        
        self.RESEARCH_PLAN_PROMPT = (
            "You are a researcher charged with providing information that can "
            "be used when writing the following essay. Generate a list of search "
            "queries that will gather any relevant information. Only generate 3 queries max."
        )
        
        self.REFLECTION_PROMPT = (
            "You are a teacher grading a 3 paragraph essay submission. "
            "Generate critique and recommendations for the user's submission. "
            "Provide detailed recommendations, including requests for length, depth, style, etc."
        )
        
        self.RESEARCH_CRITIQUE_PROMPT = (
            "You are a researcher charged with providing information that can "
            "be used when making any requested revisions (as outlined below). "
            "Generate a list of search queries that will gather any relevant information. "
            "Only generate 2 queries max."
        )
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph_structure(self):
        """Build the LangGraph structure without compilation"""
        builder = StateGraph(AgentState)
        builder.add_node("planner", self.plan_node)
        builder.add_node("research_plan", self.research_plan_node)
        builder.add_node("generate", self.generation_node)
        builder.add_node("reflect", self.reflection_node)
        builder.add_node("research_critique", self.research_critique_node)
        builder.set_entry_point("planner")
        
        builder.add_conditional_edges(
            "generate", 
            self.should_continue, 
            {END: END, "reflect": "reflect"}
        )
        builder.add_edge("planner", "research_plan")
        builder.add_edge("research_plan", "generate")
        builder.add_edge("reflect", "research_critique")
        builder.add_edge("research_critique", "generate")
        
        return builder
    
    def _build_graph(self, interrupt_after=[]):
        """Build the LangGraph workflow with dynamic interrupt configuration"""
        
        # Check if node names are valid 
        if interrupt_after and any(node not in self.builder.nodes.keys() for node in interrupt_after):
            raise ValueError(f"Invalid node names in interrupt_after: {interrupt_after}, valid nodes are: {list(self.builder.nodes.keys())}")
        
        if not interrupt_after:
            interrupt_after = None
        
        # Use in-memory SQLite for agent state
        memory = SqliteSaver(conn=sqlite3.connect(":memory:", check_same_thread=False))
        return self.builder.compile(
            checkpointer=memory,
            interrupt_after=interrupt_after
        )
    
    def create_session(self, user_id: int, essay_id: int, topic: str, max_revisions: int = 2, interrupt_after=[]):
        """Create a new agent session for a user with dynamic interrupt configuration"""
        session_id = str(uuid.uuid4())

        # Print interrupt_after for debugging
        if interrupt_after:
            print("🔧 No interrupt_after provided, graph won't be interrupted.")
        else:
            print(f"🔧 Building graph with interrupt_after: {interrupt_after}")
        
        # Rebuild graph with user's interrupt_after configuration
        self.graph = self._build_graph(interrupt_after)
        
        initial_state = {
            'task': topic,
            'max_revisions': max_revisions,
            'revision_number': 0,
            'lnode': "", 
            'plan': "", 
            'draft': "", 
            'critique': "", 
            'content': [],
            'queries': [],
            'count': 0,
            'user_id': user_id,
            'essay_id': essay_id,
            'session_id': session_id
        }
        
        thread_config = {"configurable": {"thread_id": session_id}}
        return session_id, thread_config, initial_state
    
    def run_step(self, thread_config, initial_state=None):
        """Run one step of the agent"""
        try:
            response = self.graph.invoke(initial_state, thread_config)
            current_state = self.graph.get_state(thread_config)
            
            return {
                'success': True,
                'response': response,
                'current_state': current_state.values,
                'next_node': current_state.next,
                'metadata': current_state.metadata
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'current_state': None,
                'next_node': None
            }
    
    def get_session_state(self, thread_config):
        """Get current state of an agent session"""
        try:
            current_state = self.graph.get_state(thread_config)
            return {
                'values': current_state.values,
                'next_node': current_state.next,
                'metadata': current_state.metadata
            }
        except Exception as e:
            return {'error': str(e)}
    
    def update_state(self, thread_config, key: str, value, as_node: str):
        """Update a specific value in the agent state"""
        try:
            current_state = self.graph.get_state(thread_config)
            current_state.values[key] = value
            self.graph.update_state(thread_config, current_state.values, as_node=as_node)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_history(self, thread_config):
        """Get execution history for a session"""
        try:
            history = []
            for state in self.graph.get_state_history(thread_config):
                if state.metadata.get('step', 0) < 1:
                    continue
                history.append({
                    'step': state.metadata.get('step'),
                    'node': state.values.get('lnode'),
                    'next_node': state.next,
                    'revision': state.values.get('revision_number'),
                    'count': state.values.get('count'),
                    'timestamp': state.config['configurable'].get('checkpoint_id')
                })
            return history
        except Exception as e:
            return {'error': str(e)}
    
    # Original node functions (slightly modified for user context)
    def plan_node(self, state: AgentState):
        messages = [
            SystemMessage(content=self.PLAN_PROMPT), 
            HumanMessage(content=state['task'])
        ]
        response = self.model.invoke(messages)
        
        # Save to database if essay_id provided
        if self.db and state.get('essay_id'):
            from database.models import Essay
            essay = self.db.query(Essay).get(state['essay_id'])
            if essay:
                essay.plan = response.content
                essay.updated_at = datetime.utcnow()
                self.db.commit()
        
        return {
            "plan": response.content,
            "lnode": "planner",
            "count": 1,
        }
    
    def research_plan_node(self, state: AgentState):
        queries = self.model.with_structured_output(Queries).invoke([
            SystemMessage(content=self.RESEARCH_PLAN_PROMPT),
            HumanMessage(content=state['task'])
        ])
        
        content = state['content'] or []
        for q in queries.queries:
            response = self.tavily.search(query=q, max_results=2)
            for r in response['results']:
                content.append(r['content'])
        
        return {
            "content": content,
            "queries": queries.queries,
            "lnode": "research_plan",
            "count": 1,
        }
    
    def generation_node(self, state: AgentState):
        content = "\n\n".join(state['content'] or [])
        user_message = HumanMessage(
            content=f"{state['task']}\n\nHere is my plan:\n\n{state['plan']}"
        )
        messages = [
            SystemMessage(content=self.WRITER_PROMPT.format(content=content)),
            user_message
        ]
        response = self.model.invoke(messages)
        
        # Save to database if essay_id provided
        if self.db and state.get('essay_id'):
            from database.models import Essay
            essay = self.db.query(Essay).get(state['essay_id'])
            if essay:
                essay.draft = response.content
                essay.revision_number = state.get("revision_number", 1) + 1
                essay.updated_at = datetime.utcnow()
                essay.word_count = len(response.content.split())
                self.db.commit()
        
        return {
            "draft": response.content, 
            "revision_number": state.get("revision_number", 1) + 1,
            "lnode": "generate",
            "count": 1,
        }
    
    def reflection_node(self, state: AgentState):
        messages = [
            SystemMessage(content=self.REFLECTION_PROMPT), 
            HumanMessage(content=state['draft'])
        ]
        response = self.model.invoke(messages)
        
        # Save to database if essay_id provided
        if self.db and state.get('essay_id'):
            from database.models import Essay
            essay = self.db.query(Essay).get(state['essay_id'])
            if essay:
                essay.critique = response.content
                essay.updated_at = datetime.utcnow()
                self.db.commit()
        
        return {
            "critique": response.content,
            "lnode": "reflect",
            "count": 1,
        }
    
    def research_critique_node(self, state: AgentState):
        queries = self.model.with_structured_output(Queries).invoke([
            SystemMessage(content=self.RESEARCH_CRITIQUE_PROMPT),
            HumanMessage(content=state['critique'])
        ])
        
        content = state['content'] or []
        for q in queries.queries:
            response = self.tavily.search(query=q, max_results=2)
            for r in response['results']:
                content.append(r['content'])
        
        return {
            "content": content,
            "lnode": "research_critique",
            "count": 1,
        }
    
    def should_continue(self, state):
        if state["revision_number"] > state["max_revisions"]:
            # Mark essay as completed in database
            if self.db and state.get('essay_id'):
                from database.models import Essay
                essay = self.db.query(Essay).get(state['essay_id'])
                if essay:
                    essay.status = 'completed'
                    essay.final_essay = state.get('draft')
                    essay.completed_at = datetime.utcnow()
                    self.db.commit()
            return END
        return "reflect"
