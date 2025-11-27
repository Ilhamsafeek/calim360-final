# test_claude_integration.py
from app.services.claude_service import claude_service

# Test clause drafting
result = claude_service.draft_clause(
    clause_title="Payment Terms",
    jurisdiction="Qatar",
    contract_type="Service Agreement",
    business_context="30-day payment terms, 10% retention",
    party_role="contractor"
)

print("✅ Claude API Integration Test")
print(f"Clause Body: {result['clause_body'][:200]}...")
print(f"Confidence: {result['confidence_score']}")
print(f"Suggestions: {result['suggestions']}")