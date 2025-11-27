# =====================================================
# FILE: app/services/ai_service.py
# Unified AI Service for Contract Drafting and Correspondence
# Supports both OpenAI and Claude/Anthropic APIs
# =====================================================

import asyncio
import time
import json
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.core.config import settings

# =====================================================
# CONTRACT DRAFTING AI SERVICE (OpenAI GPT-4)
# =====================================================

class ContractAIService:
    """Service for AI-powered contract drafting using ChatGPT-4"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4')
        self.max_tokens = getattr(settings, 'OPENAI_MAX_TOKENS', 2000)
    
    def draft_clause(
        self,
        clause_title: str,
        jurisdiction: str,
        business_context: Optional[str] = None,
        contract_type: Optional[str] = None,
        language: str = "en"
    ) -> Dict:
        """
        Draft a contract clause using ChatGPT-4
        
        Args:
            clause_title: Title/topic of the clause
            jurisdiction: Legal jurisdiction (e.g., "Qatar", "UAE", "UK")
            business_context: Additional business requirements
            contract_type: Type of contract (NDA, MSA, etc.)
            language: Language for drafting (en, ar)
        
        Returns:
            Dict with clause_body, suggestions, and metadata
        """
        
        # Build the prompt
        prompt = self._build_clause_prompt(
            clause_title=clause_title,
            jurisdiction=jurisdiction,
            business_context=business_context,
            contract_type=contract_type,
            language=language
        )
        
        try:
            # Call ChatGPT-4
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(jurisdiction, language)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,  # Balance between creativity and consistency
                top_p=0.9
            )
            
            # Extract the response
            clause_text = response.choices[0].message.content.strip()
            
            # Generate suggestions
            suggestions = self._generate_suggestions(
                clause_title=clause_title,
                jurisdiction=jurisdiction,
                contract_type=contract_type
            )
            
            return {
                "clause_body": clause_text,
                "suggestions": suggestions,
                "confidence_score": 0.85,
                "tokens_used": response.usage.total_tokens,
                "model": self.model
            }
            
        except Exception as e:
            raise Exception(f"AI drafting failed: {str(e)}")
    
    def _build_clause_prompt(
        self,
        clause_title: str,
        jurisdiction: str,
        business_context: Optional[str],
        contract_type: Optional[str],
        language: str
    ) -> str:
        """Build a detailed prompt for clause drafting"""
        
        prompt = f"""Draft a professional contract clause for: {clause_title}

**Contract Details:**
- Jurisdiction: {jurisdiction}
- Contract Type: {contract_type or 'General Commercial Contract'}
- Language: {'English' if language == 'en' else 'Arabic'}

"""
        
        if business_context:
            prompt += f"""**Business Context:**
{business_context}

"""
        
        prompt += f"""**Requirements:**
1. Draft a legally sound clause that complies with {jurisdiction} law
2. Use clear, professional language appropriate for commercial contracts
3. Include all essential elements for this type of clause
4. Make it balanced and fair to both parties
5. Follow best practices for contract drafting
6. Keep it concise but comprehensive

**Important Notes:**
- Do NOT add any preamble or explanation
- Provide ONLY the clause text
- Use proper legal terminology
- Structure it with clear paragraphs if needed
- Add watermark note: "DRAFT - REQUIRES LEGAL REVIEW"

Please draft the clause now:"""

        return prompt
    
    def _get_system_prompt(self, jurisdiction: str, language: str) -> str:
        """Get the system prompt for ChatGPT"""
        
        return f"""You are an expert legal contract drafting AI specializing in {jurisdiction} commercial law. 

Your role:
- Draft legally compliant contract clauses
- Use precise legal terminology
- Follow {jurisdiction} legal standards and conventions
- Ensure clarity and enforceability
- Balance protection for both parties

Guidelines:
- Be professional and formal
- Use standard contract language
- Include all necessary legal elements
- Avoid ambiguous terms
- Follow {'English' if language == 'en' else 'Arabic'} legal drafting conventions

Always include a disclaimer that the draft requires legal review."""
    
    def _generate_suggestions(
        self,
        clause_title: str,
        jurisdiction: str,
        contract_type: Optional[str]
    ) -> List[str]:
        """Generate contextual suggestions for the drafted clause"""
        
        suggestions = []
        
        # Generic suggestions based on clause type
        clause_lower = clause_title.lower()
        
        if "payment" in clause_lower or "price" in clause_lower:
            suggestions.extend([
                "Consider specifying payment terms (net 30, net 60, etc.)",
                "Add late payment penalties or interest rates",
                "Include currency and exchange rate provisions",
                "Specify accepted payment methods"
            ])
        
        elif "termination" in clause_lower:
            suggestions.extend([
                "Define termination notice period clearly",
                "Specify consequences of early termination",
                "Include provisions for post-termination obligations",
                "Add force majeure termination rights"
            ])
        
        elif "confidential" in clause_lower or "nda" in clause_lower:
            suggestions.extend([
                "Specify confidentiality period (e.g., 5 years)",
                "Define what constitutes confidential information",
                "Include exceptions (public knowledge, legal requirements)",
                "Add provisions for return/destruction of information"
            ])
        
        elif "liability" in clause_lower or "indemnit" in clause_lower:
            suggestions.extend([
                "Consider capping liability amounts",
                "Exclude certain types of damages (consequential, indirect)",
                "Ensure insurance requirements are specified",
                "Balance indemnification obligations"
            ])
        
        elif "dispute" in clause_lower or "arbitration" in clause_lower:
            suggestions.extend([
                f"Verify arbitration rules comply with {jurisdiction} law",
                "Specify arbitration venue and language",
                "Consider mediation as a first step",
                "Define governing law for disputes"
            ])
        
        # Jurisdiction-specific suggestions
        if jurisdiction.lower() in ["qatar", "qar", "doha"]:
            suggestions.append("Ensure compliance with Qatar Civil Code")
            suggestions.append("Consider QICCA arbitration for disputes")
        
        elif jurisdiction.lower() in ["uae", "dubai", "abu dhabi"]:
            suggestions.append("Ensure compliance with UAE Federal Law")
            suggestions.append("Consider DIAC arbitration for disputes")
        
        elif jurisdiction.lower() in ["uk", "england", "london"]:
            suggestions.append("Ensure compliance with English law")
            suggestions.append("Consider LCIA arbitration for international disputes")
        
        # Generic legal suggestions
        suggestions.extend([
            "Have this clause reviewed by qualified legal counsel",
            "Ensure consistency with other contract provisions",
            "Verify all defined terms are properly capitalized"
        ])
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def analyze_contract_risks(
        self,
        contract_text: str,
        jurisdiction: str
    ) -> Dict:
        """
        Analyze a contract for potential risks using AI
        
        Args:
            contract_text: Full contract text
            jurisdiction: Legal jurisdiction
        
        Returns:
            Dict with risk analysis, red flags, and recommendations
        """
        
        prompt = f"""Analyze this contract for legal and business risks under {jurisdiction} law:

{contract_text[:4000]}  # Limit to avoid token limits

Provide a JSON response with:
1. overall_risk_level: "low", "medium", or "high"
2. red_flags: list of concerning clauses or terms
3. missing_clauses: essential clauses that should be included
4. recommendations: list of improvements
5. compliance_issues: specific {jurisdiction} law compliance concerns

Format as valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a legal risk analysis AI specializing in {jurisdiction} commercial law."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.3  # Lower temperature for more analytical response
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                # Remove markdown code blocks if present
                if "```json" in analysis_text:
                    analysis_text = analysis_text.split("```json")[1].split("```")[0].strip()
                elif "```" in analysis_text:
                    analysis_text = analysis_text.split("```")[1].split("```")[0].strip()
                
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If not valid JSON, return structured response
                analysis = {
                    "overall_risk_level": "medium",
                    "red_flags": ["AI could not parse detailed analysis"],
                    "missing_clauses": [],
                    "recommendations": [analysis_text],
                    "compliance_issues": []
                }
            
            return analysis
            
        except Exception as e:
            raise Exception(f"Risk analysis failed: {str(e)}")
    
    def suggest_improvements(
        self,
        clause_text: str,
        jurisdiction: str,
        focus_area: Optional[str] = None
    ) -> Dict:
        """
        Suggest improvements to an existing clause
        
        Args:
            clause_text: The clause to improve
            jurisdiction: Legal jurisdiction
            focus_area: Specific area to focus on (clarity, fairness, compliance)
        
        Returns:
            Dict with improved version and explanation
        """
        
        focus = focus_area or "overall quality"
        
        prompt = f"""Review and improve this contract clause, focusing on {focus}:

{clause_text}

Jurisdiction: {jurisdiction}

Provide:
1. An improved version of the clause
2. Explanation of changes made
3. Why these improvements matter legally

Format as:
IMPROVED CLAUSE:
[improved text]

CHANGES MADE:
[bullet points of changes]

LEGAL RATIONALE:
[explanation]"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a contract improvement AI specializing in {jurisdiction} law."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.6
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse the structured response
            sections = {
                "improved_clause": "",
                "changes_made": [],
                "legal_rationale": ""
            }
            
            current_section = None
            for line in result_text.split('\n'):
                if "IMPROVED CLAUSE:" in line.upper():
                    current_section = "improved_clause"
                elif "CHANGES MADE:" in line.upper():
                    current_section = "changes_made"
                elif "LEGAL RATIONALE:" in line.upper():
                    current_section = "legal_rationale"
                elif current_section:
                    if current_section == "changes_made":
                        if line.strip().startswith('-') or line.strip().startswith('•'):
                            sections[current_section].append(line.strip()[1:].strip())
                    else:
                        sections[current_section] += line + "\n"
            
            return sections
            
        except Exception as e:
            raise Exception(f"Improvement suggestion failed: {str(e)}")


# =====================================================
# CORRESPONDENCE AI SERVICE
# =====================================================

async def process_correspondence_query(
    query_text: str,
    documents: List[Dict[str, Any]],
    tone: str = "formal",
    urgency: str = "normal",
    mode: str = "project"
) -> Dict[str, Any]:
    """
    Process correspondence query using AI
    
    Args:
        query_text: User's query
        documents: List of document metadata
        tone: Response tone
        urgency: Priority level
        mode: "project" or "document" level
        
    Returns:
        Dict with response_text, confidence_score, analysis_time, etc.
    """
    
    start_time = time.time()
    
    try:
        # Extract document content (implement document parsing)
        document_contents = await extract_document_contents(documents)
        
        # Build AI prompt
        prompt = build_ai_prompt(
            query_text=query_text,
            document_contents=document_contents,
            tone=tone,
            urgency=urgency,
            mode=mode
        )
        
        # Call AI API (OpenAI GPT-4 or alternative)
        ai_response = await call_ai_api(prompt, tone)
        
        # Parse and structure response
        structured_response = parse_ai_response(
            ai_response,
            documents,
            query_text
        )
        
        # Calculate metrics
        analysis_time = time.time() - start_time
        
        return {
            "response_text": structured_response["text"],
            "confidence_score": structured_response["confidence"],
            "analysis_time": round(analysis_time, 2),
            "source_references": structured_response["sources"],
            "recommendations": structured_response["recommendations"]
        }
        
    except Exception as e:
        # Fallback response
        return generate_fallback_response(query_text, documents, time.time() - start_time)


async def extract_document_contents(documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract text content from documents
    
    In production, implement:
    - PDF text extraction (PyPDF2, pdfplumber)
    - DOCX text extraction (python-docx)
    - Image OCR (Tesseract)
    - Table extraction
    """
    
    contents = []
    
    for doc in documents:
        # TODO: Implement actual document parsing
        # For now, return mock content
        content = {
            "document_id": doc["id"],
            "document_name": doc["name"],
            "content": f"[Content of {doc['name']} would be extracted here]",
            "metadata": {
                "type": doc.get("type", "unknown"),
                "url": doc.get("url", "")
            }
        }
        contents.append(content)
    
    return contents


def build_ai_prompt(
    query_text: str,
    document_contents: List[Dict[str, str]],
    tone: str,
    urgency: str,
    mode: str
) -> str:
    """Build AI prompt for correspondence analysis"""
    
    # Tone instructions
    tone_instructions = {
        "default": "Provide a balanced, neutral response.",
        "appreciative": "Express gratitude and recognition in your response.",
        "assertive": "Be direct and confident without being aggressive.",
        "cautionary": "Offer warnings and careful advice.",
        "conciliatory": "Seek to calm and resolve conflicts.",
        "consultative": "Offer guidance and expert opinion.",
        "convincing": "Be persuasive and focus on changing perspectives.",
        "enthusiastic": "Show excitement and positive energy.",
        "formal": "Use professional and structured language.",
        "friendly": "Be warm, casual, and approachable.",
        "motivating": "Be encouraging and inspiring.",
        "professional": "Maintain polished and business-like tone."
    }
    
    urgency_context = {
        "low": "This is a routine inquiry with no immediate deadline.",
        "normal": "This requires attention in the normal course of business.",
        "high": "This is a high-priority matter requiring prompt attention.",
        "urgent": "This is an urgent matter requiring immediate action."
    }
    
    # Build document context
    doc_context = "\n\n".join([
        f"Document: {doc['document_name']}\n"
        f"Type: {doc['metadata']['type']}\n"
        f"Content:\n{doc['content'][:2000]}..."  # Limit to 2000 chars per doc
        for doc in document_contents
    ])
    
    prompt = f"""You are a legal and contract management AI assistant specializing in correspondence analysis.

CONTEXT:
- Analysis Mode: {mode.upper()}
- Number of Documents: {len(document_contents)}
- Urgency Level: {urgency.upper()}
- {urgency_context.get(urgency, urgency_context['normal'])}

DOCUMENTS PROVIDED:
{doc_context}

USER QUERY:
{query_text}

TONE REQUIREMENT:
{tone_instructions.get(tone, tone_instructions['formal'])}

INSTRUCTIONS:
1. Analyze the provided documents thoroughly
2. Answer the user's query comprehensively
3. Provide specific references to relevant sections in the documents
4. Include actionable recommendations
5. Maintain the requested tone throughout
6. Structure your response with:
   - Executive Summary (2-3 sentences)
   - Detailed Analysis
   - Key Findings
   - Recommendations
   - Source References

RESPONSE FORMAT:
Please provide your response in the following JSON structure:
{{
    "executive_summary": "Brief 2-3 sentence summary",
    "analysis": "Detailed analysis text",
    "key_findings": ["Finding 1", "Finding 2", ...],
    "recommendations": [
        {{
            "title": "Recommendation Title",
            "description": "Description",
            "priority": "high|normal|low",
            "action_items": ["Action 1", "Action 2"]
        }}
    ],
    "source_references": [
        {{
            "document_id": "id",
            "document_name": "name",
            "page_number": null,
            "section": "section name",
            "excerpt": "relevant text excerpt",
            "relevance_score": 0.0-1.0
        }}
    ],
    "confidence_score": 0-100
}}

Provide your response now:"""
    
    return prompt


async def call_ai_api(prompt: str, tone: str) -> str:
    """
    Call AI API (OpenAI GPT-4)
    
    TODO: Implement actual OpenAI API call when API key is configured
    """
    
    # MOCK RESPONSE for development
    # Replace with actual API call in production
    await asyncio.sleep(2)  # Simulate API delay
    
    mock_response = {
        "executive_summary": "Based on the analysis of the provided documents, the contract includes specific termination clauses that allow for termination with 30 days written notice. However, certain conditions must be met to avoid penalties.",
        "analysis": """The documents reveal several key aspects regarding contract management and correspondence:

1. **Termination Rights**: The contract explicitly provides termination rights to both parties under specific circumstances. These include material breach, force majeure events, and mutual agreement.

2. **Notice Requirements**: A minimum of 30 days written notice is required for termination. The notice must be sent via registered mail to the addresses specified in the contract.

3. **Financial Implications**: Early termination may result in liquidated damages equivalent to 10% of the remaining contract value, unless termination is due to the other party's breach.

4. **Dispute Resolution**: Before termination, parties are required to attempt resolution through the dispute resolution mechanism outlined in Section 15 of the agreement.

5. **Documentation Requirements**: All correspondence related to termination must reference the specific contract clauses and provide detailed justification.""",
        "key_findings": [
            "30-day notice period required for termination",
            "Liquidated damages of 10% may apply",
            "Mandatory dispute resolution before termination",
            "Specific documentation requirements must be met",
            "Force majeure provisions provide protection"
        ],
        "recommendations": [
            {
                "title": "Prepare Formal Termination Notice",
                "description": "Draft a comprehensive termination notice that references all relevant contract clauses and provides detailed justification",
                "priority": "high",
                "action_items": [
                    "Review Section 12.3 of the contract",
                    "Prepare evidence of grounds for termination",
                    "Consult with legal counsel",
                    "Send via registered mail"
                ]
            },
            {
                "title": "Initiate Dispute Resolution",
                "description": "Attempt resolution through contractual dispute mechanism before proceeding with termination",
                "priority": "high",
                "action_items": [
                    "Schedule mediation session",
                    "Prepare position statement",
                    "Gather supporting documentation"
                ]
            }
        ],
        "source_references": [
            {
                "document_id": "doc-1",
                "document_name": "Main Service Agreement.pdf",
                "page_number": 15,
                "section": "Section 12.3 - Termination by Either Party",
                "excerpt": "Either party may terminate this Agreement by providing not less than thirty (30) days written notice...",
                "relevance_score": 0.95
            }
        ],
        "confidence_score": 92
    }
    
    return json.dumps(mock_response)


def parse_ai_response(
    ai_response: str,
    documents: List[Dict[str, Any]],
    query_text: str
) -> Dict[str, Any]:
    """Parse and structure AI response"""
    
    try:
        # Try to parse JSON response
        response_data = json.loads(ai_response)
        
        # Build formatted text response
        formatted_text = f"""**EXECUTIVE SUMMARY**

{response_data.get('executive_summary', '')}

**DETAILED ANALYSIS**

{response_data.get('analysis', '')}

**KEY FINDINGS**

"""
        
        for i, finding in enumerate(response_data.get('key_findings', []), 1):
            formatted_text += f"{i}. {finding}\n"
        
        formatted_text += "\n**RECOMMENDATIONS**\n\n"
        
        for rec in response_data.get('recommendations', []):
            formatted_text += f"**{rec['title']}** (Priority: {rec['priority'].upper()})\n"
            formatted_text += f"{rec['description']}\n\n"
            if rec.get('action_items'):
                formatted_text += "Action Items:\n"
                for action in rec['action_items']:
                    formatted_text += f"- {action}\n"
            formatted_text += "\n"
        
        return {
            "text": formatted_text,
            "confidence": response_data.get('confidence_score', 85),
            "sources": response_data.get('source_references', []),
            "recommendations": response_data.get('recommendations', [])
        }
        
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "text": ai_response,
            "confidence": 75,
            "sources": [],
            "recommendations": []
        }


def generate_fallback_response(
    query_text: str,
    documents: List[Dict[str, Any]],
    analysis_time: float
) -> Dict[str, Any]:
    """Generate fallback response when AI service is unavailable"""
    
    response_text = f"""**Analysis of Your Query**

I have reviewed your query: "{query_text}"

**Documents Analyzed**:
"""
    
    for i, doc in enumerate(documents, 1):
        response_text += f"{i}. {doc['name']}\n"
    
    response_text += """

**Initial Assessment**:

Based on the documents provided, I recommend:

1. **Document Review**: Please carefully review all referenced documents
2. **Legal Consultation**: Consider consulting with legal counsel for specific advice
3. **Risk Assessment**: Evaluate potential risks and mitigation strategies
4. **Action Plan**: Develop a comprehensive action plan with timelines

**Next Steps**:

- Schedule a meeting with relevant stakeholders
- Gather additional documentation if needed
- Prepare a detailed position statement
- Consider alternative resolution options

**Note**: This is a preliminary analysis. For detailed insights, please ensure all relevant documents are uploaded and try your query again.
"""
    
    return {
        "response_text": response_text,
        "confidence_score": 60,
        "analysis_time": round(analysis_time, 2),
        "source_references": [],
        "recommendations": [
            {
                "title": "Comprehensive Document Review",
                "description": "Review all contract documents thoroughly",
                "priority": "high",
                "action_items": ["Review primary contract", "Check amendments", "Verify signatures"]
            }
        ]
    }


# =====================================================
# ADDITIONAL AI FEATURES
# =====================================================

async def generate_correspondence_draft(
    context: str,
    tone: str,
    recipient: str,
    purpose: str
) -> str:
    """Generate correspondence draft using AI"""
    
    # TODO: Implement AI-powered draft generation
    mock_draft = f"""Dear {recipient},

I hope this message finds you well.

{context}

We look forward to your response and continued collaboration.

Best regards,
[Your Name]
"""
    
    return mock_draft


async def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment of correspondence"""
    
    # TODO: Implement sentiment analysis
    return {
        "sentiment": "neutral",
        "confidence": 0.85,
        "emotions": {
            "positive": 0.3,
            "neutral": 0.5,
            "negative": 0.2
        }
    }


async def extract_key_terms(text: str) -> List[str]:
    """Extract key terms from correspondence"""
    
    # Simple mock implementation
    words = re.findall(r'\b\w{4,}\b', text.lower())
    common_words = {'that', 'this', 'with', 'from', 'have', 'been', 'will', 'your'}
    key_terms = [w for w in set(words) if w not in common_words][:10]
    
    return key_terms


# =====================================================
# SERVICE INSTANCES
# =====================================================

# Create singleton instances
contract_ai_service = ContractAIService()
ai_service = contract_ai_service  # Alias for backward compatibility