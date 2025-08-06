"""
Australian legal practitioner validation
"""

import re
from typing import Optional, Dict, Any
from ..models.enums import AustralianState

class AustralianPractitionerValidator:
    """Validate Australian legal practitioner numbers by state"""
    
    # Validation patterns for each Australian state/territory
    VALIDATION_PATTERNS = {
        AustralianState.NSW: {
            'pattern': r'^[0-9]{8}$',
            'description': 'NSW: 8 digits',
            'example': '12345678'
        },
        AustralianState.VIC: {
            'pattern': r'^[0-9]{7,8}$',
            'description': 'VIC: 7-8 digits',
            'example': '1234567'
        },
        AustralianState.QLD: {
            'pattern': r'^[0-9]{4,6}$',
            'description': 'QLD: 4-6 digits',
            'example': '12345'
        },
        AustralianState.WA: {
            'pattern': r'^[0-9]{4,5}$',
            'description': 'WA: 4-5 digits',
            'example': '1234'
        },
        AustralianState.SA: {
            'pattern': r'^[0-9]{4,5}$',
            'description': 'SA: 4-5 digits',
            'example': '1234'
        },
        AustralianState.TAS: {
            'pattern': r'^[0-9]{3,4}$',
            'description': 'TAS: 3-4 digits',
            'example': '123'
        },
        AustralianState.ACT: {
            'pattern': r'^[0-9]{3,4}$',
            'description': 'ACT: 3-4 digits',
            'example': '123'
        },
        AustralianState.NT: {
            'pattern': r'^[0-9]{3,4}$',
            'description': 'NT: 3-4 digits',
            'example': '123'
        }
    }
    
    @classmethod
    def validate_practitioner_number(cls, practitioner_number: str, state: AustralianState) -> Dict[str, Any]:
        """
        Validate Australian legal practitioner number for given state
        
        Args:
            practitioner_number: The practitioner number to validate
            state: The Australian state/territory
            
        Returns:
            Dict with validation result and details
        """
        if not practitioner_number or not state:
            return {
                'valid': False,
                'error': 'Practitioner number and state are required',
                'state': state.value if state else None
            }
        
        # Get validation pattern for state
        validation_info = cls.VALIDATION_PATTERNS.get(state)
        if not validation_info:
            return {
                'valid': False,
                'error': f'Validation not available for state: {state.value}',
                'state': state.value
            }
        
        # Validate format
        pattern = validation_info['pattern']
        if not re.match(pattern, practitioner_number.strip()):
            return {
                'valid': False,
                'error': f'Invalid format for {state.value}. Expected: {validation_info["description"]}',
                'expected_format': validation_info['description'],
                'example': validation_info['example'],
                'state': state.value
            }
        
        return {
            'valid': True,
            'state': state.value,
            'formatted_number': practitioner_number.strip(),
            'description': validation_info['description']
        }
    
    @classmethod
    def get_validation_requirements(cls, state: AustralianState) -> Optional[Dict[str, str]]:
        """Get validation requirements for a specific state"""
        validation_info = cls.VALIDATION_PATTERNS.get(state)
        if validation_info:
            return {
                'state': state.value,
                'description': validation_info['description'],
                'example': validation_info['example'],
                'pattern': validation_info['pattern']
            }
        return None
    
    @classmethod
    def get_all_state_requirements(cls) -> Dict[str, Dict[str, str]]:
        """Get validation requirements for all states"""
        return {
            state.value: {
                'description': info['description'],
                'example': info['example'],
                'pattern': info['pattern']
            }
            for state, info in cls.VALIDATION_PATTERNS.items()
        }
    
    @classmethod
    def is_valid_format(cls, practitioner_number: str, state: AustralianState) -> bool:
        """Quick check if practitioner number format is valid"""
        result = cls.validate_practitioner_number(practitioner_number, state)
        return result['valid']
    
    @classmethod
    def suggest_corrections(cls, practitioner_number: str, state: AustralianState) -> Dict[str, Any]:
        """Suggest corrections for invalid practitioner numbers"""
        validation_info = cls.VALIDATION_PATTERNS.get(state)
        if not validation_info:
            return {'suggestions': []}
        
        suggestions = []
        cleaned_number = re.sub(r'[^0-9]', '', practitioner_number)
        
        # Suggest removing non-digits
        if cleaned_number != practitioner_number:
            suggestions.append({
                'type': 'format',
                'suggestion': cleaned_number,
                'reason': 'Remove non-digit characters'
            })
        
        # Suggest padding with zeros if too short
        expected_length = cls._get_expected_length(validation_info['pattern'])
        if len(cleaned_number) < expected_length:
            padded = cleaned_number.zfill(expected_length)
            suggestions.append({
                'type': 'padding',
                'suggestion': padded,
                'reason': f'Pad with leading zeros to {expected_length} digits'
            })
        
        return {
            'original': practitioner_number,
            'state': state.value,
            'expected_format': validation_info['description'],
            'suggestions': suggestions
        }
    
    @staticmethod
    def _get_expected_length(pattern: str) -> int:
        """Extract expected length from regex pattern"""
        # Simple extraction for digit patterns like [0-9]{4,6}
        if '{' in pattern:
            parts = pattern.split('{')[1].split('}')[0]
            if ',' in parts:
                return int(parts.split(',')[1])  # Take maximum length
            else:
                return int(parts)
        return 8  # Default fallback