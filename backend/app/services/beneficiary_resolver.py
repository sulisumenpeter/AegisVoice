import re
import uuid
from sqlalchemy.orm import Session
from app.models.beneficiary import Beneficiary
from typing import Optional

WORD_TO_NUM = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9'
}

def normalize_reference(ref: str) -> str:
    normalized = ref.lower()
    
    # Replace word numbers with digits (must do this before stripping spaces)
    for word, digit in WORD_TO_NUM.items():
        normalized = re.sub(rf'\b{word}\b', digit, normalized)
        
    # Strip out common ASR artifacts that might precede the actual reference
    for word in ['beneficiary', 'benary', 'vendor', 'account', 'acc', 'id', 'number']:
        normalized = re.sub(rf'\b{word}\b', '', normalized)
        
    # Remove all non-alphanumeric characters (spaces, dashes, etc.)
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    
    return normalized

def resolve(db: Session, raw_ref: str) -> Optional[Beneficiary]:
    # 1. Fallback: If it's literally a valid UUID, try that directly.
    try:
        ben_uuid = uuid.UUID(raw_ref)
        ben = db.query(Beneficiary).filter(Beneficiary.id == ben_uuid).first()
        if ben:
            return ben
    except ValueError:
        pass

    # 2. Normalize and compare against seeded data.
    normalized_input = normalize_reference(raw_ref)
    
    if not normalized_input:
        return None
        
    # Fetch all beneficiaries (in a real app with 1M beneficiaries we'd index a normalized column, 
    # but for a demo app this is totally fine)
    beneficiaries = db.query(Beneficiary).all()
    
    for ben in beneficiaries:
        norm_acc = normalize_reference(ben.account_identifier)
        norm_name = normalize_reference(ben.name)
        
        # Exact match on normalized strings prevents fuzzy matching false positives
        if normalized_input == norm_acc or normalized_input == norm_name:
            return ben
            
    return None