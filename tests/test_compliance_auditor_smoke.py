import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent))

from oricli_core.brain.modules.regulatory_compliance_auditor import RegulatoryComplianceAuditor

def test_auditor():
    print("Initializing RegulatoryComplianceAuditor...")
    auditor = RegulatoryComplianceAuditor()
    auditor.initialize()
    
    print("\n--- Test 1: Compliant Plan (Strict) ---")
    compliant_plan = [
        "1. Collect user_email and immediately encrypt it",
        "2. Store the encrypted data in secure database"
    ]
    result = auditor.execute("audit_plan", {"plan": compliant_plan})
    assert result['compliant'] is True
    
    print("\n--- Test 2: Non-Compliant Plan (GDPR Violation) ---")
    bad_plan = [
        "1. Collect user_email from form",
        "2. Store user_email directly in logs for debugging", # Violation: Missing encryption/anonymization
        "3. Send welcome email"
    ]
    result = auditor.execute("audit_plan", {"plan": bad_plan})
    assert result['compliant'] is False
    assert len(result['violations']) >= 1
    
    print("\n--- Test 3: Split Step Plan (Valid) ---")
    split_plan = [
        "1. Collect user_email from form",
        "2. Encrypt user_email with AES-256",
        "3. Store encrypted data"
    ]
    result = auditor.execute("audit_plan", {"plan": split_plan})
    assert result['compliant'] is True

    print("\n--- Test 4: HIPAA Violation ---")
    hipaa_plan = [
        "1. Read patient_id from database",
        "2. Upload patient_id to public S3 bucket", # Violation: No encryption, public sink
    ]
    result = auditor.execute("audit_plan", {"plan": hipaa_plan})
    assert result['compliant'] is False
    assert len(result['violations']) >= 1

if __name__ == "__main__":
    test_auditor()
