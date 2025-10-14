"""
Web Search Tool for LongContext Agent.
Provides web search capabilities using DuckDuckGo API for information retrieval.
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
from .base import BaseTool, ToolType

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))


class WebSearchTool(BaseTool):
    """Web search tool using DuckDuckGo"""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for current information and facts",
            tool_type=ToolType.WEB_SEARCH
        )
        self.base_url = "https://api.duckduckgo.com/"
        self.instant_url = "https://api.duckduckgo.com/"
        self.timeout = 10  # seconds
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate web search parameters"""
        if not isinstance(parameters, dict):
            return False
        
        if "query" not in parameters:
            return False
        
        query = parameters["query"]
        if not isinstance(query, str) or not query.strip():
            return False
        
        # Optional parameters validation
        if "max_results" in parameters:
            max_results = parameters["max_results"]
            if not isinstance(max_results, int) or max_results < 1 or max_results > 20:
                return False
        
        return True
    
    def _get_parameter_schema(self) -> Dict[str, Any]:
        """Return parameter schema for web search"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find information about"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results to return (default: 5)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "safe_search": {
                    "type": "string",
                    "enum": ["strict", "moderate", "off"],
                    "description": "Safe search setting (default: moderate)",
                    "default": "moderate"
                },
                "region": {
                    "type": "string",
                    "description": "Region for search results (e.g., 'us-en', 'uk-en')",
                    "default": "wt-wt"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web search with given parameters"""
        query = parameters["query"].strip()
        max_results = parameters.get("max_results", 5)
        safe_search = parameters.get("safe_search", "moderate")
        region = parameters.get("region", "wt-wt")
        
        try:
            # First try instant answer API
            instant_results = await self._get_instant_answer(query, safe_search, region)
            
            # Then get web search results
            search_results = await self._get_search_results(query, max_results, safe_search, region)
            
            # Process and format results
            formatted_results = self._format_results(instant_results, search_results, query)
            
            return {
                "query": query,
                "results": formatted_results,
                "total_results": len(search_results.get("results", [])),
                "has_instant_answer": bool(instant_results.get("abstract")),
                "search_metadata": {
                    "safe_search": safe_search,
                    "region": region,
                    "max_results": max_results
                }
            }
            
        except Exception as e:
            # Fallback to simple text-based search
            fallback_results = await self._fallback_search(query, max_results)
            
            if fallback_results:
                return {
                    "query": query,
                    "results": fallback_results,
                    "total_results": len(fallback_results),
                    "method": "fallback",
                    "warning": f"Primary search failed: {str(e)}"
                }
            
            raise Exception(f"Web search failed: {str(e)}")
    
    async def _get_instant_answer(self, query: str, safe_search: str, region: str) -> Dict[str, Any]:
        """Get instant answer from DuckDuckGo"""
        try:
            params = {
                'q': query,
                'format': 'json',
                'no_redirect': '1',
                'skip_disambig': '1',
                'safe_search': safe_search,
                'kl': region
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(self.instant_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        return {}
        except Exception:
            return {}
    
    async def _get_search_results(self, query: str, max_results: int, safe_search: str, region: str) -> Dict[str, Any]:
        """Get web search results"""
        try:
            # DuckDuckGo doesn't provide direct web results via API
            # This is a simplified implementation - in production you might use:
            # - Custom scraping (respecting robots.txt)
            # - Other search APIs (Bing, Google Custom Search)
            # - SerpApi or similar services
            
            # For now, return mock results structure
            return {
                "results": [],
                "query": query,
                "total": 0
            }
        except Exception:
            return {"results": [], "query": query, "total": 0}
    
    async def _fallback_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fallback search method using simple web scraping"""
        try:
            # This is a very simplified fallback
            # In production, you'd implement proper web scraping with:
            # - Respect for robots.txt
            # - Rate limiting
            # - User agent headers
            # - Error handling
            
            return [
                {
                    "title": f"Search result for: {query}",
                    "url": "https://example.com",
                    "snippet": f"Information about {query} can be found through various sources.",
                    "method": "fallback"
                }
            ]
        except Exception:
            return []
    
    def _format_results(self, instant_answer: Dict[str, Any], search_results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Format search results into consistent structure"""
        formatted_results = []
        
        # Add instant answer if available
        if instant_answer.get("Abstract"):
            formatted_results.append({
                "type": "instant_answer",
                "title": instant_answer.get("Heading", "Instant Answer"),
                "content": instant_answer["Abstract"],
                "url": instant_answer.get("AbstractURL", ""),
                "source": instant_answer.get("AbstractSource", "DuckDuckGo"),
                "relevance_score": 1.0
            })
        
        # Add definition if available
        if instant_answer.get("Definition"):
            formatted_results.append({
                "type": "definition",
                "title": f"Definition of {query}",
                "content": instant_answer["Definition"],
                "url": instant_answer.get("DefinitionURL", ""),
                "source": instant_answer.get("DefinitionSource", ""),
                "relevance_score": 0.95
            })
        
        # Add related topics
        related_topics = instant_answer.get("RelatedTopics", [])
        for i, topic in enumerate(related_topics[:3]):  # Limit to 3 related topics
            if isinstance(topic, dict) and topic.get("Text"):
                formatted_results.append({
                    "type": "related_topic",
                    "title": f"Related: {topic.get('Text', '')[:50]}...",
                    "content": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                    "relevance_score": 0.8 - (i * 0.1)
                })
        
        # Add web search results
        for i, result in enumerate(search_results.get("results", [])[:5]):
            formatted_results.append({
                "type": "web_result",
                "title": result.get("title", ""),
                "content": result.get("snippet", ""),
                "url": result.get("url", ""),
                "relevance_score": 0.7 - (i * 0.05)
            })
        
        # Sort by relevance score
        formatted_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return formatted_results
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        return text
    
    async def search_news(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for recent news articles"""
        try:
            # This would integrate with news APIs like NewsAPI, Bing News, etc.
            # For now, return a placeholder structure
            
            return {
                "query": query,
                "news_results": [
                    {
                        "title": f"Recent news about {query}",
                        "content": f"Latest developments regarding {query}...",
                        "source": "News Source",
                        "published_date": "2024-01-01T00:00:00Z",
                        "url": "https://example.com/news",
                        "type": "news"
                    }
                ],
                "total_results": 1,
                "search_type": "news"
            }
            
        except Exception as e:
            return {
                "query": query,
                "news_results": [],
                "error": str(e),
                "search_type": "news"
            }


class WikipediaTool(BaseTool):
    """Wikipedia search and article retrieval tool"""
    
    def __init__(self):
        super().__init__(
            name="wikipedia",
            description="Search Wikipedia for encyclopedic information",
            tool_type=ToolType.WIKIPEDIA
        )
        self.api_url = "https://en.wikipedia.org/api/rest_v1/"
        self.search_url = "https://en.wikipedia.org/w/api.php"
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate Wikipedia parameters"""
        if not isinstance(parameters, dict):
            return False
        
        if "query" not in parameters:
            return False
        
        query = parameters["query"]
        if not isinstance(query, str) or not query.strip():
            return False
        
        return True
    
    def _get_parameter_schema(self) -> Dict[str, Any]:
        """Return parameter schema for Wikipedia search"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic to search for on Wikipedia"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of search results (default: 3)",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                },
                "extract_length": {
                    "type": "integer",
                    "description": "Maximum length of article extract in characters (default: 500)",
                    "default": 500,
                    "minimum": 100,
                    "maximum": 1000
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Wikipedia search"""
        query = parameters["query"].strip()
        max_results = parameters.get("max_results", 3)
        extract_length = parameters.get("extract_length", 500)
        
        try:
            # Search for articles
            search_results = await self._search_wikipedia(query, max_results)
            
            # Get article extracts
            articles = []
            for result in search_results:
                article = await self._get_article_extract(result["title"], extract_length)
                if article:
                    articles.append(article)
            
            return {
                "query": query,
                "articles": articles,
                "total_found": len(search_results),
                "returned": len(articles)
            }
            
        except Exception as e:
            raise Exception(f"Wikipedia search failed: {str(e)}")
    
    async def _search_wikipedia(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search Wikipedia articles"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': query,
                'srlimit': limit,
                'srprop': 'titlesnippet|snippet'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('query', {}).get('search', [])
                    else:
                        return []
        except Exception:
            return []
    
    async def _get_article_extract(self, title: str, extract_length: int) -> Optional[Dict[str, Any]]:
        """Get article extract by title"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'prop': 'extracts|pageimages',
                'exintro': True,
                'explaintext': True,
                'exsectionformat': 'plain',
                'exchars': extract_length,
                'titles': title,
                'piprop': 'thumbnail',
                'pithumbsize': 300
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        pages = data.get('query', {}).get('pages', {})
                        
                        for page_id, page_data in pages.items():
                            if page_id != '-1':  # Valid page
                                return {
                                    "title": page_data.get('title', ''),
                                    "extract": page_data.get('extract', ''),
                                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                    "thumbnail": page_data.get('thumbnail', {}).get('source', ''),
                                    "page_id": page_id
                                }
            return None
        except Exception:
            return None


# Tool registration function
def register_search_tools():
    """Register all search tools"""
    from .base import get_tool_manager
    
    tool_manager = get_tool_manager()
    
    # Register web search tool
    web_search = WebSearchTool()
    tool_manager.register_tool(web_search)
    
    # Register Wikipedia tool
    wikipedia = WikipediaTool()
    tool_manager.register_tool(wikipedia)
    
    return tool_manager
