"""
LLM service for interacting with the language model API.
"""

import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

from ..models.intent import IntentType, IntentResult
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM API."""
    content: str
    success: bool
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None


class CircuitBreaker:
    """Circuit breaker for LLM API calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and (
                datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
            ):
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def on_success(self):
        """Record successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class LLMService:
    """Service for LLM API interactions."""
    
    def __init__(self):
        self.api_base = settings.LLM_API_BASE
        self.api_key = settings.LLM_API_KEY
        self.model_id = settings.MODEL_ID
        self.timeout = settings.LLM_TIMEOUT
        self.max_retries = settings.LLM_MAX_RETRIES
        self.circuit_breaker = CircuitBreaker()
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_few_shot_examples(self) -> List[Dict[str, str]]:
        """Get comprehensive few-shot examples for all 6 intent types."""
        return [
            # Grab drink examples
            {
                "input": "给我来一杯拿铁",
                "output": json.dumps({
                    "intent": "grab_drink",
                    "confidence": 0.9,
                    "entities": {"drink_name": "拿铁"}
                }, ensure_ascii=False)
            },
            {
                "input": "来杯大杯冰美式",
                "output": json.dumps({
                    "intent": "grab_drink", 
                    "confidence": 0.95,
                    "entities": {"drink_name": "美式", "size": "大杯", "temperature": "冰"}
                }, ensure_ascii=False)
            },
            {
                "input": "Give me two bottles of Coke",
                "output": json.dumps({
                    "intent": "grab_drink",
                    "confidence": 0.92,
                    "entities": {"drink_name": "Coke", "quantity": 2}
                }, ensure_ascii=False)
            },
            # Deliver drink examples
            {
                "input": "把这杯咖啡送到会议室",
                "output": json.dumps({
                    "intent": "deliver_drink",
                    "confidence": 0.9,
                    "entities": {"drink_name": "咖啡", "location": "会议室"}
                }, ensure_ascii=False)
            },
            {
                "input": "Please deliver the hot tea to the office",
                "output": json.dumps({
                    "intent": "deliver_drink",
                    "confidence": 0.88,
                    "entities": {"drink_name": "tea", "temperature": "hot", "location": "office"}
                }, ensure_ascii=False)
            },
            # Recommend drink examples
            {
                "input": "推荐点提神的饮料",
                "output": json.dumps({
                    "intent": "recommend_drink",
                    "confidence": 0.9,
                    "entities": {"preference": "提神"}
                }, ensure_ascii=False)
            },
            {
                "input": "What refreshing drinks do you have?",
                "output": json.dumps({
                    "intent": "recommend_drink",
                    "confidence": 0.85,
                    "entities": {"preference": "refreshing"}
                }, ensure_ascii=False)
            },
            # Cancel order examples
            {
                "input": "算了，不要了",
                "output": json.dumps({
                    "intent": "cancel_order",
                    "confidence": 0.95,
                    "entities": {}
                }, ensure_ascii=False)
            },
            {
                "input": "Cancel my coffee order",
                "output": json.dumps({
                    "intent": "cancel_order",
                    "confidence": 0.9,
                    "entities": {"drink_name": "coffee"}
                }, ensure_ascii=False)
            },
            # Query status examples
            {
                "input": "我的饮料好了吗",
                "output": json.dumps({
                    "intent": "query_status",
                    "confidence": 0.92,
                    "entities": {}
                }, ensure_ascii=False)
            },
            {
                "input": "Is my latte ready?",
                "output": json.dumps({
                    "intent": "query_status",
                    "confidence": 0.88,
                    "entities": {"drink_name": "latte"}
                }, ensure_ascii=False)
            },
            # Modify order examples
            {
                "input": "改成大杯的",
                "output": json.dumps({
                    "intent": "modify_order",
                    "confidence": 0.9,
                    "entities": {"size": "大杯"}
                }, ensure_ascii=False)
            },
            {
                "input": "Change it to hot milk tea",
                "output": json.dumps({
                    "intent": "modify_order",
                    "confidence": 0.85,
                    "entities": {"temperature": "hot", "drink_name": "milk tea"}
                }, ensure_ascii=False)
            }
        ]
    
    def create_prompt(self, user_input: str) -> str:
        """Create prompt with few-shot examples."""
        examples_text = ""
        for example in self.get_few_shot_examples():
            examples_text += f"输入: {example['input']}\n输出: {example['output']}\n\n"
        
        prompt = f"""你是一个饮料意图理解系统。分析用户输入，识别意图类型并提取实体信息。

支持的意图类型:
- grab_drink: 抓取/获取饮料的请求
- deliver_drink: 递送饮料到指定位置
- recommend_drink: 饮料推荐请求
- cancel_order: 取消订单请求
- query_status: 查询饮料状态
- modify_order: 修改订单内容

实体类型:
- drink_name: 饮料名称（咖啡、茶、可乐等）
- brand: 品牌信息（可口可乐、雪碧等）
- size: 规格大小（大杯、中杯、小杯、瓶装）
- temperature: 温度要求（热、温、冰、常温）
- quantity: 数量
- location: 位置信息
- preference: 偏好需求（提神、解腻、清爽、暖胃等）

请以JSON格式输出，包含intent、confidence(0-1)、entities字段。

示例:
{examples_text}
现在分析这个输入:
输入: {user_input}
输出:"""
        
        return prompt
    
    async def call_llm_api(self, user_input: str) -> LLMResponse:
        """Call LLM API with circuit breaker protection."""
        if not self.circuit_breaker.can_execute():
            return LLMResponse(
                content="",
                success=False,
                error_message="Circuit breaker OPEN - LLM service temporarily unavailable"
            )
        
        start_time = datetime.now()
        
        try:
            prompt = self.create_prompt(user_input)
            payload = {
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 300,
                "stream": False
            }
            
            session = await self.get_session()
            
            for attempt in range(self.max_retries + 1):
                try:
                    async with session.post(
                        f"{self.api_base}/chat/completions",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            content = data["choices"][0]["message"]["content"].strip()
                            
                            response_time = (datetime.now() - start_time).total_seconds() * 1000
                            self.circuit_breaker.on_success()
                            
                            return LLMResponse(
                                content=content,
                                success=True,
                                response_time_ms=int(response_time)
                            )
                        else:
                            error_text = await response.text()
                            logger.warning(f"LLM API returned status {response.status}: {error_text}")
                            
                            if attempt < self.max_retries:
                                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                                continue
                            else:
                                self.circuit_breaker.on_failure()
                                return LLMResponse(
                                    content="",
                                    success=False,
                                    error_message=f"LLM API error: {response.status} - {error_text}"
                                )
                
                except asyncio.TimeoutError:
                    logger.warning(f"LLM API timeout on attempt {attempt + 1}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    else:
                        self.circuit_breaker.on_failure()
                        return LLMResponse(
                            content="",
                            success=False,
                            error_message="LLM API timeout"
                        )
                
                except Exception as e:
                    logger.error(f"LLM API error on attempt {attempt + 1}: {str(e)}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    else:
                        self.circuit_breaker.on_failure()
                        return LLMResponse(
                            content="",
                            success=False,
                            error_message=f"LLM API error: {str(e)}"
                        )
        
        except Exception as e:
            self.circuit_breaker.on_failure()
            logger.error(f"Unexpected error in LLM API call: {str(e)}")
            return LLMResponse(
                content="",
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    async def test_connection(self) -> bool:
        """Test LLM API connectivity."""
        try:
            session = await self.get_session()
            async with session.get(f"{self.api_base}/models") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"LLM connection test failed: {str(e)}")
            return False


# Global LLM service instance
llm_service = LLMService()