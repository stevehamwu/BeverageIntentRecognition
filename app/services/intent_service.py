"""
Core intent classification service.
"""

import json
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.intent import IntentType, IntentResult
from .llm_service import llm_service, LLMService

logger = logging.getLogger(__name__)


class IntentClassificationService:
    """Core service for intent classification and entity extraction."""
    
    def __init__(self, llm_service_instance: Optional[LLMService] = None):
        self.llm_service = llm_service_instance or llm_service
    
    async def analyze_intent(
        self, 
        user_input: str, 
        context: Optional[str] = None,
        include_raw_response: bool = False
    ) -> IntentResult:
        """Analyze user input and return intent classification result."""
        start_time = datetime.now()
        
        try:
            # Try LLM classification first
            llm_response = await self.llm_service.call_llm_api(user_input)
            
            if llm_response.success:
                try:
                    # Parse LLM JSON response
                    result_data = json.loads(llm_response.content)
                    intent = IntentType(result_data["intent"])
                    confidence = float(result_data["confidence"])
                    entities = result_data.get("entities", {})
                    
                    processing_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return IntentResult(
                        intent=intent,
                        confidence=confidence,
                        entities=entities,
                        raw_text=llm_response.content if include_raw_response else None,
                        processing_time_ms=int(processing_time)
                    )
                
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Failed to parse LLM response: {e}. Content: {llm_response.content}")
                    # Fall back to rule-based analysis
                    return await self._fallback_analysis(
                        user_input, 
                        f"LLM parsing error: {str(e)}",
                        include_raw_response,
                        start_time
                    )
            else:
                logger.warning(f"LLM API failed: {llm_response.error_message}")
                # Fall back to rule-based analysis
                return await self._fallback_analysis(
                    user_input, 
                    f"LLM API failed: {llm_response.error_message}",
                    include_raw_response,
                    start_time
                )
        
        except Exception as e:
            logger.error(f"Unexpected error in intent analysis: {str(e)}")
            return await self._fallback_analysis(
                user_input, 
                f"Unexpected error: {str(e)}",
                include_raw_response,
                start_time
            )
    
    async def _fallback_analysis(
        self, 
        user_input: str, 
        error_info: str,
        include_raw_response: bool = False,
        start_time: Optional[datetime] = None
    ) -> IntentResult:
        """Enhanced rule-based fallback for all 6 intent types."""
        if start_time is None:
            start_time = datetime.now()
        
        entities = {}
        
        # Intent classification keywords
        deliver_keywords = ["送", "递送", "送到", "送给", "拿给", "deliver", "bring", "take to"]
        recommend_keywords = ["推荐", "建议", "什么", "有没有", "清爽", "提神", "暖胃", "解腻", 
                             "recommend", "suggest", "what", "refreshing", "energizing"]
        cancel_keywords = ["取消", "算了", "不要了", "撤销", "不要", "cancel", "never mind", "forget"]
        query_keywords = ["好了吗", "做好了", "完成了", "状态", "进度", "怎么样了", 
                         "ready", "done", "finished", "status", "how"]
        modify_keywords = ["改成", "换成", "修改", "改为", "变成", "change", "modify", "switch"]
        
        # Determine intent
        user_input_lower = user_input.lower()
        if any(keyword in user_input for keyword in deliver_keywords):
            intent = IntentType.DELIVER_DRINK
        elif any(keyword in user_input for keyword in recommend_keywords):
            intent = IntentType.RECOMMEND_DRINK
        elif any(keyword in user_input for keyword in cancel_keywords):
            intent = IntentType.CANCEL_ORDER
        elif any(keyword in user_input for keyword in query_keywords):
            intent = IntentType.QUERY_STATUS
        elif any(keyword in user_input for keyword in modify_keywords):
            intent = IntentType.MODIFY_ORDER
        else:
            intent = IntentType.GRAB_DRINK
        
        # Entity extraction
        entities = self._extract_entities_fallback(user_input)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return IntentResult(
            intent=intent,
            confidence=0.6,  # Lower confidence for fallback
            entities=entities,
            raw_text=f"Fallback analysis: {error_info}" if include_raw_response else None,
            processing_time_ms=int(processing_time)
        )
    
    def _extract_entities_fallback(self, user_input: str) -> Dict[str, Any]:
        """Extract entities using rule-based approach."""
        entities = {}
        
        # Drink names (Chinese and English)
        drinks_cn = ["拿铁", "美式", "咖啡", "茶", "奶茶", "可乐", "雪碧", "橙汁", "果汁", "水"]
        drinks_en = ["latte", "americano", "coffee", "tea", "milk tea", "cola", "coke", 
                    "sprite", "juice", "water", "espresso", "cappuccino", "mocha"]
        
        for drink in drinks_cn + drinks_en:
            if drink in user_input.lower():
                entities["drink_name"] = drink
                break
        
        # Brands
        brands = ["可口可乐", "coca-cola", "coke", "雪碧", "sprite", "百事", "pepsi", "星巴克", "starbucks"]
        for brand in brands:
            if brand in user_input.lower():
                entities["brand"] = brand
                break
        
        # Sizes
        sizes_cn = ["大杯", "中杯", "小杯", "超大杯", "瓶装"]
        sizes_en = ["large", "medium", "small", "extra large", "bottle"]
        
        for size in sizes_cn + sizes_en:
            if size in user_input.lower():
                entities["size"] = size
                break
        
        # Temperature
        temps_cn = ["热", "冰", "温", "常温"]
        temps_en = ["hot", "iced", "cold", "warm", "room temperature"]
        
        for temp in temps_cn + temps_en:
            if temp in user_input.lower():
                entities["temperature"] = temp
                break
        
        # Preferences
        prefs_cn = ["提神", "清爽", "暖胃", "解腻"]
        prefs_en = ["energizing", "refreshing", "warming", "light"]
        
        for pref in prefs_cn + prefs_en:
            if pref in user_input.lower():
                entities["preference"] = pref
                break
        
        # Location
        locations_cn = ["会议室", "办公室", "前台", "休息室", "教室", "食堂"]
        locations_en = ["meeting room", "office", "reception", "lounge", "classroom", "cafeteria"]
        
        for loc in locations_cn + locations_en:
            if loc in user_input.lower():
                entities["location"] = loc
                break
        
        # Quantity (simple number extraction)
        # Chinese numbers
        chinese_numbers = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5}
        for chinese_num, value in chinese_numbers.items():
            if chinese_num in user_input:
                entities["quantity"] = value
                break
        
        # Arabic numbers
        quantity_match = re.search(r'(\d+)(?:[杯瓶个份]|(?:\s*(?:cup|bottle|glass|piece)s?))', user_input.lower())
        if quantity_match and "quantity" not in entities:
            entities["quantity"] = int(quantity_match.group(1))
        
        return entities
    
    async def validate_result(self, result: IntentResult) -> bool:
        """Validate the intent classification result."""
        try:
            # Check intent is valid
            if not isinstance(result.intent, IntentType):
                return False
            
            # Check confidence is in valid range
            if not (0.0 <= result.confidence <= 1.0):
                return False
            
            # Check entities are properly typed
            if not isinstance(result.entities, dict):
                return False
            
            # Validate entity values
            for key, value in result.entities.items():
                if key == "quantity" and not isinstance(value, (int, float)):
                    return False
                elif key == "confidence" and not (0.0 <= value <= 1.0):
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Result validation error: {str(e)}")
            return False


# Global intent service instance
intent_service = IntentClassificationService()