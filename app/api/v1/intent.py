"""
Intent analysis API endpoints.
"""

import asyncio
import time
from typing import List
import logging

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from ...models.request import IntentAnalysisRequest, BatchIntentAnalysisRequest
from ...models.response import IntentAnalysisResponse, BatchIntentAnalysisResponse
from ...services.intent_service import intent_service
from ...services.cache_service import cache_service
from ...utils.metrics import metrics_manager

logger = logging.getLogger(__name__)
router = APIRouter()


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


@router.post(
    "/intent/analyze",
    response_model=IntentAnalysisResponse,
    summary="Analyze single text input for drink intent",
    description="Classify user input to determine beverage-related intent and extract relevant entities"
)
async def analyze_intent(
    request_data: IntentAnalysisRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    request_id: str = Depends(get_request_id)
) -> IntentAnalysisResponse:
    """
    Analyze a single text input for drink intent classification.
    
    This endpoint processes natural language input to:
    - Classify the intent (grab_drink, recommend_drink, deliver_drink, etc.)
    - Extract relevant entities (drink_name, size, temperature, etc.)
    - Return confidence scores and processing metadata
    
    The system uses a combination of LLM processing and rule-based fallback
    to ensure high availability and accuracy.
    """
    try:
        start_time = time.time()
        
        # Check cache first
        cached_result = await cache_service.get(request_data.text, request_data.context)
        if cached_result:
            logger.info(f"Cache hit for request {request_id}")
            metrics_manager.record_cache_operation("get", "hit")
            
            # Update response with request metadata
            response = IntentAnalysisResponse(
                **cached_result.dict(),
                request_id=request_id,
                cached=True
            )
            
            # Record metrics in background
            background_tasks.add_task(
                metrics_manager.record_intent_classification,
                response.intent.value,
                response.confidence
            )
            
            return response
        else:
            metrics_manager.record_cache_operation("get", "miss")
        
        # Perform intent analysis
        result = await intent_service.analyze_intent(
            user_input=request_data.text,
            context=request_data.context,
            include_raw_response=request_data.include_raw_response
        )
        
        # Validate result
        if not await intent_service.validate_result(result):
            logger.error(f"Invalid result for request {request_id}: {result}")
            raise HTTPException(
                status_code=500,
                detail="Intent analysis produced invalid result"
            )
        
        # Cache successful result
        background_tasks.add_task(
            cache_service.set,
            request_data.text,
            result,
            request_data.context
        )
        metrics_manager.record_cache_operation("set", "success")
        
        # Create response
        response = IntentAnalysisResponse(
            **result.dict(),
            request_id=request_id,
            cached=False
        )
        
        # Record metrics in background
        background_tasks.add_task(
            metrics_manager.record_intent_classification,
            response.intent.value,
            response.confidence
        )
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(
            f"Intent analysis completed for request {request_id}",
            extra={
                "intent": response.intent.value,
                "confidence": response.confidence,
                "processing_time_ms": round(processing_time, 2),
                "entities_count": len(response.entities)
            }
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in intent analysis for request {request_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during intent analysis"
        )


@router.post(
    "/batch/analyze",
    response_model=BatchIntentAnalysisResponse,
    summary="Analyze multiple text inputs for drink intent",
    description="Process multiple inputs in parallel for efficient batch intent classification"
)
async def analyze_batch_intent(
    request_data: BatchIntentAnalysisRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    request_id: str = Depends(get_request_id)
) -> BatchIntentAnalysisResponse:
    """
    Analyze multiple text inputs for drink intent classification.
    
    This endpoint processes multiple inputs efficiently by:
    - Running analyses in parallel when requested
    - Utilizing cache for previously processed inputs
    - Providing detailed batch processing statistics
    - Handling partial failures gracefully
    
    Maximum batch size is limited to 50 inputs for performance reasons.
    """
    try:
        start_time = time.time()
        
        if len(request_data.inputs) > 50:
            raise HTTPException(
                status_code=400,
                detail="Batch size exceeds maximum limit of 50 inputs"
            )
        
        logger.info(
            f"Starting batch analysis for request {request_id}",
            extra={
                "batch_size": len(request_data.inputs),
                "parallel_processing": request_data.parallel_processing
            }
        )
        
        results = []
        success_count = 0
        error_count = 0
        
        async def process_single_input(input_data: IntentAnalysisRequest) -> IntentAnalysisResponse:
            """Process a single input within the batch."""
            try:
                # Check cache first
                cached_result = await cache_service.get(input_data.text, input_data.context)
                if cached_result:
                    metrics_manager.record_cache_operation("get", "hit")
                    return IntentAnalysisResponse(**cached_result.dict(), cached=True)
                else:
                    metrics_manager.record_cache_operation("get", "miss")
                
                # Perform analysis
                result = await intent_service.analyze_intent(
                    user_input=input_data.text,
                    context=input_data.context,
                    include_raw_response=input_data.include_raw_response
                )
                
                # Cache result
                background_tasks.add_task(
                    cache_service.set,
                    input_data.text,
                    result,
                    input_data.context
                )
                
                # Record metrics
                background_tasks.add_task(
                    metrics_manager.record_intent_classification,
                    result.intent.value,
                    result.confidence
                )
                
                return IntentAnalysisResponse(**result.dict(), cached=False)
            
            except Exception as e:
                logger.error(f"Error processing batch input: {str(e)}")
                # Return a default error response
                from ...models.intent import IntentType, IntentResult
                error_result = IntentResult(
                    intent=IntentType.GRAB_DRINK,
                    confidence=0.0,
                    entities={"error": str(e)},
                    raw_text=None,
                    processing_time_ms=0
                )
                return IntentAnalysisResponse(**error_result.dict(), cached=False)
        
        # Process inputs
        if request_data.parallel_processing:
            # Parallel processing
            tasks = [process_single_input(input_data) for input_data in request_data.inputs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"Batch item {i} failed: {str(result)}")
                    # Create error response
                    from ...models.intent import IntentType, IntentResult
                    error_result = IntentResult(
                        intent=IntentType.GRAB_DRINK,
                        confidence=0.0,
                        entities={"error": "Processing failed"},
                        raw_text=None,
                        processing_time_ms=0
                    )
                    processed_results.append(IntentAnalysisResponse(**error_result.dict(), cached=False))
                else:
                    success_count += 1
                    processed_results.append(result)
            
            results = processed_results
        else:
            # Sequential processing
            results = []
            for input_data in request_data.inputs:
                try:
                    result = await process_single_input(input_data)
                    results.append(result)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Sequential batch processing error: {str(e)}")
                    # Create error response
                    from ...models.intent import IntentType, IntentResult
                    error_result = IntentResult(
                        intent=IntentType.GRAB_DRINK,
                        confidence=0.0,
                        entities={"error": str(e)},
                        raw_text=None,
                        processing_time_ms=0
                    )
                    results.append(IntentAnalysisResponse(**error_result.dict(), cached=False))
        
        # Calculate total processing time
        total_processing_time = (time.time() - start_time) * 1000
        
        # Create batch response
        response = BatchIntentAnalysisResponse(
            results=results,
            total_processed=len(request_data.inputs),
            success_count=success_count,
            error_count=error_count,
            total_processing_time_ms=int(total_processing_time),
            request_id=request_id
        )
        
        logger.info(
            f"Batch analysis completed for request {request_id}",
            extra={
                "total_processed": response.total_processed,
                "success_count": response.success_count,
                "error_count": response.error_count,
                "total_time_ms": response.total_processing_time_ms
            }
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in batch intent analysis for request {request_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error during batch intent analysis"
        )