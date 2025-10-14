"""
Web Search Tool for LongContext Agent.
Provides web search capabilities using SerpAPI for information retrieval.
"""

import asyncio
import aiohttp
import json
import re
import os
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
sys.path.append(os.path.dirname(__file__))

from base import BaseTool
from models import ToolType


class WebSearchTool(BaseTool):
    """Web search tool using SerpAPI (Google Search)"""
    
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for current information, news, and facts using Google Search",
            tool_type=ToolType.WEB_SEARCH
        )
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.timeout = 15  # seconds
        self.fallback_enabled = True
    
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
        region = parameters.get("region", "us")
        
        try:
            # Check if SerpAPI is available and configured
            if not self.serpapi_key:
                raise Exception("SERPAPI_API_KEY not configured")
            
            if GoogleSearch is None:
                raise Exception("google-search-results package not installed")
            
            # Perform search using SerpAPI
            search_results = await self._search_with_serpapi(query, max_results, safe_search, region)
            
            # Format results
            formatted_results = self._format_serpapi_results(search_results, query)
            
            return {
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "search_engine": "google",
                "search_metadata": {
                    "safe_search": safe_search,
                    "region": region,
                    "max_results": max_results
                }
            }
            
        except Exception as e:
            # Fallback to simple search if enabled
            if self.fallback_enabled:
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
    
    async def _search_with_serpapi(self, query: str, max_results: int, safe_search: str, region: str) -> Dict[str, Any]:
        """Perform search using SerpAPI"""
        try:
            # Configure search parameters
            search_params = {
                "q": query,
                "api_key": self.serpapi_key,
                "engine": "google",
                "num": min(max_results, 10),  # Max 10 results per request
                "gl": region,  # Geographic location
                "hl": "en",    # Interface language
                "safe": "active" if safe_search == "strict" else "off",
                "no_cache": "false"  # Use cache for better performance
            }
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            search = GoogleSearch(search_params)
            results = await loop.run_in_executor(None, search.get_dict)
            
            return results
            
        except Exception as e:
            raise Exception(f"SerpAPI search failed: {str(e)}")
    
    def _format_serpapi_results(self, results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Format SerpAPI results into consistent structure"""
        formatted_results = []
        
        try:
            # Add knowledge graph/answer box if available
            if "knowledge_graph" in results:
                kg = results["knowledge_graph"]
                formatted_results.append({
                    "type": "knowledge_graph",
                    "title": kg.get("title", ""),
                    "content": kg.get("description", ""),
                    "url": kg.get("website", ""),
                    "source": "Google Knowledge Graph",
                    "relevance_score": 1.0,
                    "metadata": {
                        "type": kg.get("type", ""),
                        "attributes": kg.get("attributes", {})
                    }
                })
            
            # Add answer box if available
            if "answer_box" in results:
                ab = results["answer_box"]
                formatted_results.append({
                    "type": "answer_box",
                    "title": ab.get("title", "Direct Answer"),
                    "content": ab.get("answer", ab.get("snippet", "")),
                    "url": ab.get("displayed_link", ab.get("link", "")),
                    "source": ab.get("displayed_link", "Google"),
                    "relevance_score": 0.98
                })
            
            # Add organic search results
            organic_results = results.get("organic_results", [])
            for i, result in enumerate(organic_results):
                formatted_results.append({
                    "type": "web_result",
                    "title": result.get("title", ""),
                    "content": result.get("snippet", ""),
                    "url": result.get("link", ""),
                    "displayed_url": result.get("displayed_link", ""),
                    "source": result.get("displayed_link", ""),
                    "relevance_score": 0.9 - (i * 0.05),
                    "position": result.get("position", i + 1)
                })
            
            # Add news results if available
            news_results = results.get("news_results", [])
            for i, news in enumerate(news_results[:3]):  # Limit to 3 news items
                formatted_results.append({
                    "type": "news_result",
                    "title": news.get("title", ""),
                    "content": news.get("snippet", ""),
                    "url": news.get("link", ""),
                    "source": news.get("source", ""),
                    "date": news.get("date", ""),
                    "relevance_score": 0.85 - (i * 0.05),
                    "thumbnail": news.get("thumbnail", "")
                })
            
            # Sort by relevance score
            formatted_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return formatted_results
            
        except Exception as e:
            # Return basic structure if formatting fails
            return [{
                "type": "error",
                "title": "Search Results",
                "content": f"Search completed but formatting failed: {str(e)}",
                "url": "",
                "relevance_score": 0.5
            }]
    
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
            
            if not search_results:
                return {
                    "query": query,
                    "articles": [],
                    "total_found": 0,
                    "returned": 0,
                    "message": f"No Wikipedia articles found for '{query}'"
                }
            
            # Get article extracts
            articles = []
            for result in search_results:
                try:
                    article = await self._get_article_extract(result["title"], extract_length)
                    if article:
                        # Add search result metadata
                        article["search_snippet"] = result.get("snippet", "")
                        article["relevance_score"] = self._calculate_relevance(query, article)
                        articles.append(article)
                except Exception as e:
                    # Log but continue with other articles
                    print(f"Failed to get extract for {result.get('title', 'unknown')}: {e}")
                    continue
            
            # Sort by relevance score
            articles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return {
                "query": query,
                "articles": articles,
                "total_found": len(search_results),
                "returned": len(articles),
                "search_metadata": {
                    "extract_length": extract_length,
                    "max_results": max_results
                }
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
    
    def _calculate_relevance(self, query: str, article: Dict[str, Any]) -> float:
        """Calculate relevance score between query and article"""
        try:
            query_lower = query.lower()
            title_lower = article.get("title", "").lower()
            extract_lower = article.get("extract", "").lower()
            
            score = 0.0
            
            # Title match (highest weight)
            if query_lower in title_lower:
                score += 0.4
            elif any(word in title_lower for word in query_lower.split()):
                score += 0.2
            
            # Extract content match
            query_words = set(query_lower.split())
            extract_words = set(extract_lower.split())
            
            if query_words:
                common_words = query_words.intersection(extract_words)
                score += 0.3 * (len(common_words) / len(query_words))
            
            # Phrase match bonus
            if len(query.strip()) > 3 and query_lower in extract_lower:
                score += 0.3
            
            return min(1.0, score)
            
        except Exception:
            return 0.5  # Default relevance


# Tool registration function
def register_search_tools():
    """Register all search tools"""
    from base import get_tool_manager
    
    tool_manager = get_tool_manager()
    
    # Register web search tool
    web_search = WebSearchTool()
    tool_manager.register_tool(web_search)
    
    # Register Wikipedia tool
    wikipedia = WikipediaTool()
    tool_manager.register_tool(wikipedia)
    
    return tool_manager
