import re

with open('app/api/api_v1/obligations/obligations.py', 'r') as f:
    content = f.read()

# Find the delete try block and add SET FOREIGN_KEY_CHECKS
old_pattern = r'(# ✅ DELETE RELATED RECORDS IN CORRECT ORDER\s+try:)'
new_code = r'\1\n            # Disable foreign key checks to force delete\n            db.execute(text("SET FOREIGN_KEY_CHECKS=0"))'

content = re.sub(old_pattern, new_code, content)

# Add re-enable after the final commit
old_pattern2 = r'(db\.commit\(\)\s+logger\.info\(f"✅ Obligation.*deleted successfully"\))'
new_code2 = r'db.execute(text("SET FOREIGN_KEY_CHECKS=1"))\n            \1'

content = re.sub(old_pattern2, new_code2, content)

with open('app/api/api_v1/obligations/obligations.py', 'w') as f:
    f.write(content)

print("✅ Updated delete function to disable FK checks")
