from anthropic import Anthropic
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import re
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatbotClaudeService:
    
    def __init__(self):
        try:
            api_key = settings.CLAUDE_API_KEY
            if not api_key:
                logger.warning("⚠ CLAUDE_API_KEY not set - chatbot will use mock responses")
                self.client = None
                self.model = "mock-model"
            else:
                self.client = Anthropic(api_key=api_key)
                self.model = getattr(settings, 'CLAUDE_MODEL', 'claude-sonnet-4-20250514')
                logger.info(f"✅ Chatbot Claude AI initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize chatbot Claude client: {str(e)}")
            self.client = None
            self.model = "mock-model"
        
        self.max_tokens = getattr(settings, 'CLAUDE_MAX_TOKENS', 4000)
        self.temperature = getattr(settings, 'CLAUDE_TEMPERATURE', 0.7)

    async def generate_chat_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        tone: str = "formal",
        language: str = "en",
        contract_context: Optional[Dict] = None,
        user_role: Optional[str] = None,
        user_name: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            logger.info(f"🤖 Generating response: {user_message[:50]}...")
            
            if not self.client:
                return self._generate_mock_response(user_message, tone, language)
            
            full_response = ""
            async for chunk in self.generate_chat_response_stream(
                user_message=user_message,
                conversation_history=conversation_history,
                tone=tone,
                language=language,
                contract_context=contract_context,
                user_role=user_role,
                user_name=user_name,
                company_name=company_name
            ):
                full_response += chunk
            
            processing_time = int((time.time() - start_time) * 1000)
            word_count = len(full_response.split())
            
            logger.info(f"✅ Response generated: {word_count} words in {processing_time}ms")
            
            variants = await self._generate_response_variants(full_response, user_message, tone)
            clause_refs = self._extract_clause_references(full_response, contract_context)
            
            return {
                "success": True,
                "primary_response": full_response,
                "response": full_response,
                "variants": variants,
                "clause_references": clause_refs,
                "confidence_score": 0.95,
                "tokens_used": word_count,
                "processing_time_ms": processing_time,
                "model_used": self.model,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "tone": tone,
                    "language": language,
                    "has_contract_context": contract_context is not None
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}", exc_info=True)
            return self._generate_mock_response(user_message, tone, language)

    async def generate_chat_response_stream(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        tone: str = "formal",
        language: str = "en",
        contract_context: Optional[Dict] = None,
        user_role: Optional[str] = None,
        user_name: Optional[str] = None,
        company_name: Optional[str] = None
    ):
        try:
            if not self.client:
                async for chunk in self._generate_mock_streaming_response(user_message):
                    yield chunk
                return
            
            system_prompt = self._build_chatbot_system_prompt(
                tone=tone,
                language=language,
                contract_context=contract_context,
                user_role=user_role,
                user_name=user_name,
                company_name=company_name
            )
            
            messages = self._build_conversation_messages(user_message, conversation_history)
            
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"❌ Streaming error: {str(e)}", exc_info=True)
            yield f"\n\n❌ Error: {str(e)}"

    def _build_chatbot_system_prompt(
        self,
        tone: str = "formal",
        language: str = "en",
        contract_context: Optional[Dict] = None,
        user_role: Optional[str] = None,
        user_name: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> str:
        
        system_prompt = f"""You are CALIM360 AI Assistant, a specialized AI chatbot for contract lifecycle management in Qatar's construction, oil & gas, and infrastructure sectors.

**YOUR ROLE:**
- Provide expert guidance on contract creation, management, and compliance
- Help users navigate FIDIC, Qatar Civil Code, and QFCRA regulations
- Offer practical advice on contract workflows, obligations, and risk management
- Communicate in a {tone} tone while being helpful and professional

**RESPONSE LANGUAGE:** {language}

**CAPABILITIES:**
1. **Contract Drafting**: Guide template selection, clause customization, compliance
2. **Workflow Management**: Approval processes, multi-party signatures, tracking
3. **Compliance**: Qatar Civil Code, QFCRA regulations, FIDIC standards
4. **Risk Analysis**: Identify issues, suggest mitigation strategies
5. **Obligations Tracking**: Milestones, payment schedules, deliverables
6. **Correspondence**: Letter drafting, formal communications, dispute letters
"""

        if user_role:
            system_prompt += f"\n**USER ROLE:** {user_role}"
        
        if user_name:
            system_prompt += f"\n**USER NAME:** {user_name}"
            
        if company_name:
            system_prompt += f"\n**COMPANY:** {company_name}"

        if contract_context:
            system_prompt += f"""

**CURRENT CONTRACT CONTEXT:**
- Contract Number: {contract_context.get('contract_number', 'N/A')}
- Type: {contract_context.get('contract_type', 'N/A')}
- Value: {contract_context.get('contract_value', 'N/A')}
- Status: {contract_context.get('status', 'N/A')}
"""

        system_prompt += """

**RESPONSE GUIDELINES:**
- Be concise but comprehensive
- Cite specific clauses or regulations when relevant
- Provide actionable advice with clear next steps
- Use professional language appropriate for legal/business context
- If uncertain, acknowledge limitations and suggest consulting legal experts
- For Arabic responses, use formal business Arabic (فصحى)

**REMEMBER:**
- You assist with contract management, not legal advice
- Always recommend professional legal review for critical decisions
- Focus on practical guidance within CALIM360 capabilities

How can I help you today?
"""
        
        return system_prompt.strip()
    
    def _build_conversation_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]]
    ) -> List[Dict]:
        
        messages = []
        
        if conversation_history:
            for msg in conversation_history[-10:]:
                role = msg.get("role", "user")
                if role not in ["user", "assistant"]:
                    role = "assistant" if msg.get("sender_type") == "system" else "user"
                
                messages.append({
                    "role": role,
                    "content": msg.get("content", msg.get("message_content", ""))
                })
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages

    async def _generate_response_variants(
        self,
        primary_response: str,
        user_message: str,
        tone: str
    ) -> List[Dict]:
        
        return [{
            "variant_id": 1,
            "approach": "detailed",
            "response": primary_response,
            "confidence": 0.95,
            "best_for": "Users seeking comprehensive information"
        }]

    def _extract_clause_references(
        self,
        response_text: str,
        contract_context: Optional[Dict]
    ) -> List[Dict]:
        
        if not contract_context or 'clauses' not in contract_context:
            return []
        
        clause_refs = []
        clause_pattern = r'Clause\s+(\d+\.?\d*)'
        matches = re.findall(clause_pattern, response_text, re.IGNORECASE)
        
        for match in matches:
            for clause in contract_context.get('clauses', []):
                if clause.get('clause_number') == match:
                    clause_refs.append({
                        "clause_number": match,
                        "clause_id": clause.get('id'),
                        "title": clause.get('title'),
                        "relevance": "mentioned"
                    })
        
        return clause_refs

    def _calculate_confidence_score(self, response_obj: Any, text_length: int) -> float:
        base_confidence = 0.90
        if text_length < 100:
            base_confidence -= 0.10
        elif text_length > 3000:
            base_confidence -= 0.05
        return min(0.99, max(0.70, base_confidence))

    def _generate_mock_response(
        self,
        user_message: str,
        tone: str,
        language: str
    ) -> Dict[str, Any]:
        
        mock_text = """I can help you with contract lifecycle management! 

**Available Support:**
• **Template Selection**: Choose from FIDIC-compliant templates
• **Qatar Compliance**: Ensure all mandatory elements included
• **Risk Analysis**: Identify potential issues early
• **Workflow Management**: Track approvals and signatures

⚠️ **Note**: Claude API not configured. Set ANTHROPIC_API_KEY for full AI capabilities.

**How can I assist you further?**"""
        
        return {
            "success": True,
            "primary_response": mock_text,
            "response": mock_text,
            "variants": [{
                "variant_id": 1,
                "approach": "mock",
                "response": mock_text,
                "confidence": 0.50,
                "best_for": "Mock response"
            }],
            "clause_references": [],
            "confidence_score": 0.50,
            "tokens_used": 0,
            "processing_time_ms": 0,
            "model_used": "mock-model",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _generate_mock_streaming_response(self, user_message: str):
        
        mock_text = """I can help you with contract drafting! 

## Available Support

• **Template Selection**: FIDIC-compliant templates
• **Qatar Compliance**: All mandatory elements
• **Risk Analysis**: Identify potential issues

⚠️ **Note**: Claude API not configured.

**How can I assist you?**"""
        
        words = mock_text.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)


chatbot_claude_service = ChatbotClaudeService()