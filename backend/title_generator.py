"""
Title Generation Service
Generates meaningful conversation titles based on chat content using OpenAI API
"""

import os
import logging
from typing import List, Optional
from datetime import datetime

import openai
from openai import AsyncOpenAI

# Add shared directory to path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from models import BaseMessage, MessageRole

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generates conversation titles based on chat content"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            logger.warning("OPENAI_API_KEY not found. Title generation will use fallback titles.")
    
    async def generate_title(self, messages: List[BaseMessage], max_messages: int = 6) -> str:
        """
        Generate a concise, meaningful title for a conversation
        
        Args:
            messages: List of conversation messages
            max_messages: Maximum number of recent messages to consider
        
        Returns:
            Generated title string
        """
        try:
            if not messages:
                return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Take the first few messages to understand the conversation topic
            relevant_messages = messages[:max_messages]
            
            # Create a prompt for title generation
            conversation_text = self._format_messages_for_title_generation(relevant_messages)
            
            if not conversation_text.strip():
                return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Generate title using OpenAI or fallback
            if self.client:
                title = await self._call_openai_for_title(conversation_text)
            else:
                title = self._generate_fallback_title(relevant_messages)
            
            # Clean and validate the title
            clean_title = self._clean_title(title)
            
            logger.info(f"Generated title: '{clean_title}' from {len(relevant_messages)} messages")
            return clean_title
            
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    def _format_messages_for_title_generation(self, messages: List[BaseMessage]) -> str:
        """Format messages for title generation prompt"""
        formatted_messages = []
        
        for msg in messages:
            if msg.role in ['user', 'assistant']:
                # Truncate very long messages to keep prompt manageable
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                role = "Human" if msg.role == 'user' else "Assistant"
                formatted_messages.append(f"{role}: {content}")
        
        return "\n".join(formatted_messages)
    
    def _generate_fallback_title(self, messages: List[BaseMessage]) -> str:
        """Generate a fallback title when OpenAI API is not available"""
        if not messages:
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Extract keywords from the first user message
        first_user_message = None
        for msg in messages:
            if msg.role == MessageRole.USER:
                first_user_message = msg.content
                break
        
        if not first_user_message:
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Simple keyword extraction for fallback title
        keywords = self._extract_keywords_simple(first_user_message)
        
        if keywords:
            # Take first 2-3 keywords and create a title
            title_words = keywords[:3]
            title = " ".join(title_words).title()
            
            # Add "Discussion" or "Help" based on context
            if any(word in first_user_message.lower() for word in ['help', 'how', 'what', 'explain', '?']):
                title += " Help"
            else:
                title += " Discussion"
            
            return title
        
        return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    def _extract_keywords_simple(self, text: str) -> List[str]:
        """Simple keyword extraction from text"""
        # Common stop words to ignore
        stop_words = {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
            'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',
            'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until',
            'while', 'of', 'at', 'by', 'for', 'with', 'through', 'during', 'before', 'after',
            'above', 'below', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
            'further', 'then', 'once', 'can', 'could', 'would', 'should', 'may', 'might', 'must',
            'will', 'shall', 'help', 'please', 'hi', 'hello', 'thanks', 'thank'
        }
        
        # Clean and split text
        words = text.lower().replace('?', '').replace('!', '').replace('.', '').split()
        
        # Filter out stop words and short words
        keywords = []
        for word in words:
            if (len(word) >= 3 and 
                word not in stop_words and 
                word.isalpha() and 
                len(keywords) < 5):
                keywords.append(word)
        
        return keywords
    
    async def _call_openai_for_title(self, conversation_text: str) -> str:
        """Call OpenAI API to generate a title"""
        
        prompt = f"""Based on the following conversation, generate a concise, descriptive title (maximum 4-6 words) that captures the main topic or purpose of the discussion. The title should be clear and informative.

Conversation:
{conversation_text}

Generate a title that:
1. Is between 2-6 words
2. Captures the main topic or purpose
3. Is clear and professional
4. Does not include quotes or special formatting
5. Is suitable for a chat session name

Title:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that generates concise, meaningful titles for conversations. Always respond with just the title, no additional text or formatting."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.7,
                timeout=10
            )
            
            title = response.choices[0].message.content.strip()
            return title
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _clean_title(self, title: str) -> str:
        """Clean and validate the generated title"""
        if not title:
            return f"Chat {datetime.now().strftime('%Y-%m-%d')}"
        
        # Remove quotes and extra formatting
        title = title.strip('"\'').strip()
        
        # Remove common prefixes that the AI might add
        prefixes_to_remove = [
            "title:", "Title:", "TITLE:",
            "conversation about", "discussion about", 
            "chat about", "talk about"
        ]
        
        title_lower = title.lower()
        for prefix in prefixes_to_remove:
            if title_lower.startswith(prefix.lower()):
                title = title[len(prefix):].strip()
                break
        
        # Ensure reasonable length
        if len(title) > 50:
            title = title[:47] + "..."
        
        # If title is too short or generic, add fallback
        if len(title) < 3 or title.lower() in ['chat', 'conversation', 'discussion']:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        return title
    
    def should_generate_title(self, current_title: str, message_count: int) -> bool:
        """
        Determine if a title should be generated/updated
        
        Args:
            current_title: Current session title
            message_count: Number of messages in the conversation
        
        Returns:
            True if title should be generated
        """
        # Don't regenerate if we already have a custom title (not timestamp-based)
        if not self._is_default_title(current_title):
            return False
        
        # Generate title after the second exchange (4 messages total: user, assistant, user, assistant)
        if message_count == 4:
            return True
        
        return False
    
    def _is_default_title(self, title: str) -> bool:
        """Check if title is a default timestamp-based title"""
        if not title:
            return True
        
        # Check for common default patterns
        default_patterns = [
            "New Session", "New Conversation", "Chat ",
            "Conversation ", "Session "
        ]
        
        title_lower = title.lower()
        
        # Check if it starts with any default pattern
        for pattern in default_patterns:
            if title_lower.startswith(pattern.lower()):
                return True
        
        # Check if it's a date/time based title
        import re
        date_patterns = [
            r'chat \d{4}-\d{2}-\d{2}',
            r'session \d{4}-\d{2}-\d{2}',
            r'conversation \d{4}-\d{2}-\d{2}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, title_lower):
                return True
        
        return False


# Create singleton instance
title_generator = TitleGenerator()


async def generate_conversation_title(messages: List[BaseMessage]) -> str:
    """
    Convenience function to generate a conversation title
    
    Args:
        messages: List of conversation messages
    
    Returns:
        Generated title string
    """
    return await title_generator.generate_title(messages)


def should_update_title(current_title: str, message_count: int) -> bool:
    """
    Convenience function to check if title should be updated
    
    Args:
        current_title: Current session title
        message_count: Number of messages in the conversation
    
    Returns:
        True if title should be updated
    """
    return title_generator.should_generate_title(current_title, message_count)
