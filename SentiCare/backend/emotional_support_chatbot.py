"""
Emotional Support Chatbot with Session Memory
Uses Groq API (Llama 3.1 8B) for conversational support
Maintains chat history per session using JSON files
"""

from groq import Groq
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json
import uuid
import os
from dotenv import load_dotenv

load_dotenv()


class ChatSession:
    """Manages individual chat session with memory"""
    
    def __init__(self, session_id: str, sessions_dir: Path):
        self.session_id = session_id
        self.sessions_dir = sessions_dir
        self.session_file = sessions_dir / f"{session_id}.json"
        self.messages: List[Dict] = []
        self.created_at = datetime.utcnow().isoformat()
        self.last_updated = self.created_at
        
        # Load existing session or create new
        if self.session_file.exists():
            self._load_session()
        else:
            self._initialize_session()
    
    def _initialize_session(self):
        """Initialize a new chat session"""
        self.messages = []
        self._save_session()
        print(f"New chat session created: {self.session_id}")
    
    def _load_session(self):
        """Load existing session from JSON"""
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.messages = data.get('messages', [])
                self.created_at = data.get('created_at', self.created_at)
                self.last_updated = data.get('last_updated', self.last_updated)
            print(f"Loaded existing session: {self.session_id} ({len(self.messages)} messages)")
        except Exception as e:
            print(f"Error loading session {self.session_id}: {e}")
            self._initialize_session()
    
    def _save_session(self):
        """Save session to JSON file"""
        try:
            session_data = {
                'session_id': self.session_id,
                'created_at': self.created_at,
                'last_updated': datetime.utcnow().isoformat(),
                'message_count': len(self.messages),
                'messages': self.messages
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            self.last_updated = session_data['last_updated']
        except Exception as e:
            print(f"Error saving session {self.session_id}: {e}")
    
    def add_message(self, role: str, content: str):
        """Add a message to the chat history"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.messages.append(message)
        self._save_session()
    
    def get_messages_for_llm(self) -> List[Dict]:
        """Get messages formatted for Groq API (without timestamps)"""
        return [
            {'role': msg['role'], 'content': msg['content']}
            for msg in self.messages
        ]
    
    def clear_history(self):
        """Clear all messages in the session"""
        self.messages = []
        self._save_session()
        print(f"Session {self.session_id} history cleared")
    
    def get_session_info(self) -> Dict:
        """Get session metadata"""
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'message_count': len(self.messages)
        }


class EmotionalSupportChatbot:
    """
    Emotional support chatbot with session-based memory
    Designed to provide empathetic, mood-lifting conversations
    """
    
    def __init__(self, sessions_dir: str = "chat_sessions"):
        """
        Initialize the chatbot
        
        Args:
            sessions_dir: Directory to store chat session JSON files
        """
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "openai/gpt-oss-20b"
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, Dict] = {}
        
        # System prompt for emotional support
        self.system_prompt = """You are Maitri, a compassionate and empathetic mental health support companion. Your role is to:

1. Listen actively and validate emotions
2. Provide supportive, non-judgmental responses
3. Offer coping strategies and gentle guidance
4. Encourage professional help when appropriate
5. Use warm, conversational language
6. Be aware of the user's recent mental health trends to provide personalized support

IMPORTANT GUIDELINES:
- Never diagnose conditions
- Always prioritize user safety
- If user mentions self-harm or suicide, encourage immediate professional help
- Be culturally sensitive and inclusive
- Use simple, accessible language
- Show genuine care and understanding

When you have access to the user's recent mental health scores, use this information to:
- Acknowledge improvements or challenges
- Provide context-aware support
- Celebrate progress
- Offer relevant coping strategies based on their trends"""
        
        print(f"Emotional Support Chatbot initialized")
        print(f"Sessions directory: {self.sessions_dir}")
    
    def create_session(self) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        session = ChatSession(session_id, self.sessions_dir)
        return session_id
    
    def get_session(self, session_id: str) -> ChatSession:
        """Get or create a chat session"""
        return ChatSession(session_id, self.sessions_dir)
    
    def chat(
        self, 
        session_id: str, 
        user_message: str, 
        temperature: float = 0.7, 
        max_tokens: int = 500,
        mental_health_context: Optional[List[Dict]] = None
    ) -> dict:
        """
        Chat with user in given session (message is already anonymized)
        """
        try:
            # Get or create session (this was missing!)
            session = self.get_session(session_id)
            
            # Add user message to history (already anonymized)
            session.add_message('user', user_message)
            
            # Prepare system prompt with mental health context
            enhanced_system_prompt = self.system_prompt
            
            if mental_health_context and len(mental_health_context) > 0:
                context_str = "\n\n**USER'S RECENT MENTAL HEALTH TRENDS (Last 5 Days):**\n"
                context_str += "Use this information to provide personalized, context-aware support.\n\n"
                
                for day_data in mental_health_context:
                    context_str += f"📅 {day_data['date']}:\n"
                    context_str += f"  • Depression: {day_data['depression']}/100\n"
                    context_str += f"  • Anxiety: {day_data['anxiety']}/100\n"
                    context_str += f"  • Stress: {day_data['stress']}/100\n"
                    context_str += f"  • Overall Mental Health: {day_data['overall']}/100\n\n"
                
                # Add trend analysis
                if len(mental_health_context) > 1:
                    latest = mental_health_context[0]
                    oldest = mental_health_context[-1]
                    
                    context_str += "**TRENDS:**\n"
                    
                    dep_change = latest['depression'] - oldest['depression']
                    anx_change = latest['anxiety'] - oldest['anxiety']
                    str_change = latest['stress'] - oldest['stress']
                    
                    if dep_change < -10:
                        context_str += "✅ Depression scores improving\n"
                    elif dep_change > 10:
                        context_str += "⚠️ Depression scores increasing - provide extra support\n"
                    
                    if anx_change < -10:
                        context_str += "✅ Anxiety levels decreasing\n"
                    elif anx_change > 10:
                        context_str += "⚠️ Anxiety levels rising - suggest calming techniques\n"
                    
                    if str_change < -10:
                        context_str += "✅ Stress levels improving\n"
                    elif str_change > 10:
                        context_str += "⚠️ Stress levels elevated - recommend stress management\n"
                
                context_str += "\nUse this context to provide empathetic, personalized responses that acknowledge their journey."
                
                enhanced_system_prompt += context_str
            
            # Get messages for LLM (last 10 for context)
            messages_for_llm = session.get_messages_for_llm()[-10:]
            
            # Get response from LLM with context
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': enhanced_system_prompt},
                    *messages_for_llm
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            assistant_message = response.choices[0].message.content
            
            # Add assistant response to history
            session.add_message('assistant', assistant_message)
            
            return {
                'success': True,
                'session_id': session_id,
                'assistant_message': assistant_message,
                'session_info': {
                    'message_count': len(session.messages),
                    'created_at': session.created_at,
                    'last_updated': session.last_updated
                }
            }
            
        except Exception as e:
            print(f"Chat error for session {session_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_chat_history(self, session_id: str) -> Dict:
        """Get the full chat history for a session"""
        try:
            session = self.get_session(session_id)
            return {
                'success': True,
                'session_id': session_id,
                'messages': session.messages,
                'session_info': session.get_session_info()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
    
    def clear_session(self, session_id: str) -> Dict:
        """Clear chat history for a session"""
        try:
            session = self.get_session(session_id)
            session.clear_history()
            return {
                'success': True,
                'message': 'Chat history cleared',
                'session_id': session_id
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
    
    def delete_session(self, session_id: str) -> Dict:
        """Delete a session file"""
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
                return {
                    'success': True,
                    'message': 'Session deleted',
                    'session_id': session_id
                }
            else:
                return {
                    'success': False,
                    'error': 'Session not found',
                    'session_id': session_id
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
    
    def list_sessions(self) -> List[Dict]:
        """List all active sessions"""
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                session_id = session_file.stem
                session = self.get_session(session_id)
                sessions.append(session.get_session_info())
            except Exception as e:
                print(f"Error reading session {session_file}: {e}")
        
        return sorted(sessions, key=lambda x: x['last_updated'], reverse=True)


# Example usage and testing
if __name__ == "__main__":
    # Initialize chatbot
    chatbot = EmotionalSupportChatbot()
    
    # Create a new session
    session_id = chatbot.create_session()
    print(f"\nCreated session: {session_id}\n")
    
    # Test conversation
    test_messages = [
        "Hi, I'm feeling a bit down today...",
        "Work has been really stressful lately",
        "Thanks, that helps. Do you have any tips for managing stress?"
    ]
    
    for msg in test_messages:
        print(f"User: {msg}")
        response = chatbot.chat(session_id, msg)
        
        if response['success']:
            print(f"Bot: {response['assistant_message']}\n")
        else:
            print(f"Error: {response['error']}\n")
    
    # Get chat history
    history = chatbot.get_chat_history(session_id)
    print(f"\nTotal messages in session: {history['session_info']['message_count']}")
    
    # List all sessions
    all_sessions = chatbot.list_sessions()
    print(f"\nActive sessions: {len(all_sessions)}")