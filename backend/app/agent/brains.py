"""
Brain Provider Selection (B2.2).

Provides Brain 1 (Coordinator) and Brain 2 (Manager) abstraction over the LLM service.
Manual provider selection only - hardware auto-select deferred to B2.5.
"""

import json
import re
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm.types import LLMMessage, LLMOptions, LLMResponse, ProviderType
from app.logging_config import get_logger
from app.services.llm_service import get_llm_service

from .state import BrainDecision

logger = get_logger("agent.brains")


def _extract_json_object(text: str) -> Tuple[str, bool]:
    """
    Extract JSON object from text that may have surrounding content.

    Finds the first '{' and last '}' and extracts that substring.
    This handles cases where the model adds explanatory text before/after JSON.

    Returns:
        Tuple of (extracted_json, was_extracted)
    """
    first_brace = text.find('{')
    last_brace = text.rfind('}')

    if first_brace == -1 or last_brace == -1 or last_brace < first_brace:
        return text, False

    return text[first_brace:last_brace + 1], True


def _repair_json_strings(text: str) -> str:
    """
    Attempt to repair common JSON issues from LLM responses.

    Handles:
    - Unescaped newlines inside strings
    - Unescaped quotes inside strings
    - Trailing commas in arrays/objects
    """
    # Replace unescaped newlines inside strings with escaped version
    # This regex finds strings and replaces newlines within them
    def escape_newlines_in_string(match):
        content = match.group(1)
        # Escape actual newlines (not already escaped ones)
        content = content.replace('\n', '\\n')
        content = content.replace('\r', '\\r')
        return '"' + content + '"'

    # Match quoted strings (simple approach - may not handle all edge cases)
    # This pattern tries to match strings while preserving already-escaped chars
    try:
        # Simple approach: replace literal newlines in the entire text
        # that appear inside what looks like JSON string values
        lines = text.split('\n')
        result_lines = []
        in_string = False

        for i, line in enumerate(lines):
            # Count unescaped quotes to track if we're in a string
            quote_count = 0
            j = 0
            while j < len(line):
                if line[j] == '"' and (j == 0 or line[j-1] != '\\'):
                    quote_count += 1
                j += 1

            # If this line ends mid-string (odd number of quotes), we need to merge
            if in_string:
                # We're continuing a string from previous line
                if result_lines:
                    result_lines[-1] = result_lines[-1] + '\\n' + line
                else:
                    result_lines.append(line)
            else:
                result_lines.append(line)

            # Update in_string state for next line
            if quote_count % 2 == 1:
                in_string = not in_string

        text = '\n'.join(result_lines)
    except Exception:
        # If repair fails, return original
        pass

    # Remove trailing commas before ] or }
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    return text


class BrainCallError(Exception):
    """Raised when a brain call fails."""

    def __init__(self, message: str, brain: str, raw_response: Optional[str] = None):
        super().__init__(message)
        self.brain = brain
        self.raw_response = raw_response


async def call_brain_1(
    system_prompt: str,
    user_prompt: str,
    db_session: AsyncSession,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> LLMResponse:
    """
    Call Brain 1 (Coordinator) with the given prompts.

    Brain 1 is configured for fast response (typically flash model).

    Args:
        system_prompt: System instruction for B1
        user_prompt: User message/query
        db_session: Database session for credential lookup
        run_id: Optional run ID for tracking
        session_id: Optional session ID for tracking

    Returns:
        LLMResponse from the provider
    """
    settings = get_settings()
    service = get_llm_service()

    # Build messages
    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    # Build options with B1 config
    options = LLMOptions(
        model=settings.brain_1_model,
        temperature=0.3,  # Lower temperature for more deterministic classification
        max_tokens=2000,
        run_id=run_id,
        session_id=session_id,
    )

    # Get provider type
    try:
        provider_type = ProviderType(settings.brain_1_provider)
    except ValueError:
        raise BrainCallError(
            f"Unknown Brain 1 provider: {settings.brain_1_provider}",
            brain="B1",
        )

    logger.debug(
        "Calling Brain 1",
        extra={
            "extra_fields": {
                "provider": provider_type.value,
                "model": settings.brain_1_model,
            }
        },
    )

    return await service.complete(messages, options, db_session, provider_type)


async def call_brain_2(
    system_prompt: str,
    user_prompt: str,
    db_session: AsyncSession,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> LLMResponse:
    """
    Call Brain 2 (Manager) with the given prompts.

    Brain 2 is configured for complex reasoning (typically flagship model).

    Args:
        system_prompt: System instruction for B2
        user_prompt: User message/query
        db_session: Database session for credential lookup
        run_id: Optional run ID for tracking
        session_id: Optional session ID for tracking

    Returns:
        LLMResponse from the provider
    """
    settings = get_settings()
    service = get_llm_service()

    # Build messages
    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    # Build options with B2 config
    options = LLMOptions(
        model=settings.brain_2_model,
        temperature=0.5,  # Moderate temperature for reasoning
        max_tokens=4000,
        run_id=run_id,
        session_id=session_id,
    )

    # Get provider type
    try:
        provider_type = ProviderType(settings.brain_2_provider)
    except ValueError:
        raise BrainCallError(
            f"Unknown Brain 2 provider: {settings.brain_2_provider}",
            brain="B2",
        )

    logger.debug(
        "Calling Brain 2",
        extra={
            "extra_fields": {
                "provider": provider_type.value,
                "model": settings.brain_2_model,
            }
        },
    )

    return await service.complete(messages, options, db_session, provider_type)


def parse_json_response(
    response_text: str,
    brain: str,
) -> Dict[str, Any]:
    """
    Parse JSON from a brain response, handling common issues.

    Uses multiple strategies to extract and parse JSON:
    1. Remove markdown code fences
    2. Extract JSON object from surrounding text
    3. Repair common JSON issues (newlines in strings, trailing commas)

    Args:
        response_text: Raw response text from the brain
        brain: "B1" or "B2" for error messages

    Returns:
        Parsed JSON as dict

    Raises:
        BrainCallError: If JSON parsing fails after all repair attempts
    """
    original_text = response_text
    text = response_text.strip()

    # Log raw response for debugging (truncated)
    logger.debug(
        f"{brain} raw response (first 500 chars)",
        extra={"extra_fields": {"response": text[:500]}}
    )

    # Step 1: Remove markdown code fences if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Step 2: Try to parse as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass  # Continue to extraction/repair

    # Step 3: Try to extract JSON object from surrounding text
    extracted, was_extracted = _extract_json_object(text)
    if was_extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            text = extracted  # Use extracted text for repair attempts

    # Step 4: Try to repair common issues
    repaired = _repair_json_strings(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Step 5: Last resort - try extracting and repairing together
    if was_extracted:
        repaired_extracted = _repair_json_strings(extracted)
        try:
            return json.loads(repaired_extracted)
        except json.JSONDecodeError:
            pass

    # All attempts failed - log the raw response and raise error
    logger.error(
        f"{brain} JSON parsing failed after all repair attempts",
        extra={
            "extra_fields": {
                "original_text": original_text[:1000],
                "extracted_text": extracted[:500] if was_extracted else "N/A",
                "repaired_text": repaired[:500],
            }
        }
    )

    # Try to parse one more time to get the actual error message
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        raise BrainCallError(
            f"{brain} returned invalid JSON: {e}",
            brain=brain,
            raw_response=original_text[:500],
        )

    # This shouldn't be reached, but just in case
    raise BrainCallError(
        f"{brain} returned invalid JSON (unknown error)",
        brain=brain,
        raw_response=original_text[:500],
    )


def parse_brain_decision(
    response_text: str,
    brain: str,
) -> BrainDecision:
    """
    Parse a BrainDecision from a brain response.

    Args:
        response_text: Raw response text from the brain
        brain: "B1" or "B2" for error messages

    Returns:
        BrainDecision instance

    Raises:
        BrainCallError: If parsing fails
    """
    data = parse_json_response(response_text, brain)

    # Validate required fields
    if "decision" not in data:
        raise BrainCallError(
            f"{brain} response missing 'decision' field",
            brain=brain,
            raw_response=response_text[:500],
        )

    if "intent" not in data:
        raise BrainCallError(
            f"{brain} response missing 'intent' field",
            brain=brain,
            raw_response=response_text[:500],
        )

    return BrainDecision.from_dict(data)


async def call_brain_1_for_decision(
    system_prompt: str,
    user_prompt: str,
    db_session: AsyncSession,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    retry_on_parse_error: bool = True,
) -> BrainDecision:
    """
    Call Brain 1 and parse the response as a BrainDecision.

    Args:
        system_prompt: System instruction for B1
        user_prompt: User message/query
        db_session: Database session
        run_id: Optional run ID
        session_id: Optional session ID
        retry_on_parse_error: If True, retry once with stricter prompt on parse error

    Returns:
        BrainDecision from B1
    """
    response = await call_brain_1(system_prompt, user_prompt, db_session, run_id, session_id)

    try:
        return parse_brain_decision(response.content, "B1")
    except BrainCallError as e:
        if not retry_on_parse_error:
            raise

        # Retry with stricter prompt
        logger.warning(
            "B1 returned invalid JSON, retrying with stricter prompt",
            extra={
                "extra_fields": {
                    "error": str(e),
                    "raw": e.raw_response[:200] if e.raw_response else "N/A"
                }
            }
        )
        strict_prompt = (
            "ERROR: Your response was not valid JSON.\n\n"
            "RETRY NOW - Output EXACTLY this format:\n"
            '{"decision":"answer","intent":"answer_only","tool_name":null,"target_artifacts":[],"plan_steps":[],"key_risks":[],"summary":"your summary here"}\n\n'
            "RULES:\n"
            "- Start with { end with }\n"
            "- NO text before or after\n"
            "- NO markdown\n"
            "- ALL strings single line\n"
            "- Valid values: decision=answer/use_tool/ask_user/escalate, intent=answer_only/plan_only/run_bash/ask_user/escalate\n\n"
            f"Original request: {user_prompt}\n\n"
            "OUTPUT JSON NOW:"
        )
        response = await call_brain_1(system_prompt, strict_prompt, db_session, run_id, session_id)
        return parse_brain_decision(response.content, "B1")


async def call_brain_2_for_decision(
    system_prompt: str,
    user_prompt: str,
    db_session: AsyncSession,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    retry_on_parse_error: bool = True,
) -> BrainDecision:
    """
    Call Brain 2 and parse the response as a BrainDecision.

    Args:
        system_prompt: System instruction for B2
        user_prompt: User message/query
        db_session: Database session
        run_id: Optional run ID
        session_id: Optional session ID
        retry_on_parse_error: If True, retry once with stricter prompt on parse error

    Returns:
        BrainDecision from B2
    """
    response = await call_brain_2(system_prompt, user_prompt, db_session, run_id, session_id)

    try:
        return parse_brain_decision(response.content, "B2")
    except BrainCallError as e:
        if not retry_on_parse_error:
            raise

        # Retry with stricter prompt
        logger.warning(
            "B2 returned invalid JSON, retrying with stricter prompt",
            extra={
                "extra_fields": {
                    "error": str(e),
                    "raw": e.raw_response[:200] if e.raw_response else "N/A"
                }
            }
        )
        strict_prompt = (
            "ERROR: Your response was not valid JSON.\n\n"
            "RETRY NOW - Output EXACTLY this format:\n"
            '{"decision":"answer","intent":"answer_only","tool_name":null,"target_artifacts":[],"plan_steps":[],"key_risks":[],"summary":"your summary here"}\n\n'
            "RULES:\n"
            "- Start with { end with }\n"
            "- NO text before or after\n"
            "- NO markdown\n"
            "- ALL strings single line\n"
            "- Valid values: decision=answer/use_tool/ask_user/escalate, intent=answer_only/plan_only/run_bash/ask_user/escalate\n\n"
            f"Original request: {user_prompt}\n\n"
            "OUTPUT JSON NOW:"
        )
        response = await call_brain_2(system_prompt, strict_prompt, db_session, run_id, session_id)
        return parse_brain_decision(response.content, "B2")
