with open('app/api/api_v1/obligations/obligations.py', 'r') as f:
    content = f.read()

# Replace the generate-ai endpoint definition
old_endpoint = '''@router.post("/generate-ai")
async def generate_obligations_ai(
    data: AIObligationGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Use AI to extract obligations from contract content"""
    try:
        # Get contract
        contract = db.query(Contract).filter(
            Contract.id == data.contract_id,
            Contract.company_id == current_user.company_id
        ).first()'''

new_endpoint = '''@router.post("/generate-ai/{contract_id}")
async def generate_obligations_ai(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Use AI to extract obligations from contract content"""
    try:
        # Get contract
        contract = db.query(Contract).filter(
            Contract.id == contract_id,
            Contract.company_id == current_user.company_id
        ).first()'''

content = content.replace(old_endpoint, new_endpoint)

# Also fix the reference to data.contract_id later in the function
content = content.replace('Contract.id == data.contract_id,', 'Contract.id == contract_id,')
content = content.replace('ContractVersion.contract_id == data.contract_id', 'ContractVersion.contract_id == contract_id')

with open('app/api/api_v1/obligations/obligations.py', 'w') as f:
    f.write(content)

print("✅ Fixed generate-ai endpoint to accept contract_id in path")
