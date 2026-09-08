"""Auto-improvement engine - CANNOT self-promote (Owner only)"""

import json
import hashlib
import copy
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from audit_engine import AuditLogger

logger = logging.getLogger(__name__)


class EvolutionLoop:
    """Generate and nominate variants (CANNOT promote)"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger

    def propose_variants(self, top_strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate ±10% parameter variations"""
        variants = []

        # Extract parameters
        params = top_strategy.get('params', {})

        # Generate ±10% variations
        for param_name, param_value in params.items():
            if not isinstance(param_value, (int, float)):
                continue

            for delta in [-0.10, -0.05, 0.05, 0.10]:
                variant = copy.deepcopy(top_strategy)
                variant['params'][param_name] = param_value * (1 + delta)

                # Generate variant hash
                variant_hash = hashlib.sha256(
                    json.dumps(variant, sort_keys=True).encode()
                ).hexdigest()

                variants.append({
                    'parent_hash': top_strategy.get('hash'),
                    'variant_hash': variant_hash,
                    'params': variant['params'],
                    'mutation': f"{param_name} *= {1+delta:.2f}",
                    'status': 'PROPOSED',
                    'timestamp': datetime.utcnow().isoformat()
                })

                # Log proposal
                self.audit.append({
                    'type': 'VARIANT_PROPOSED',
                    'variant_hash': variant_hash,
                    'parent_hash': top_strategy.get('hash'),
                    'mutation': f"{param_name} *= {1+delta:.2f}"
                })

        logger.info(f"Generated {len(variants)} variants from {top_strategy.get('name')}")
        return variants

    def nominate_for_review(self, top_variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Nominate candidates for Guardian → Owner review (NO auto-promotion)"""
        nominated = []

        for variant in top_variants:
            variant_hash = variant['variant_hash']
            score = variant.get('score', 0)

            # Log nomination
            self.audit.append({
                'type': 'VARIANT_NOMINATED',
                'variant_hash': variant_hash,
                'score': score,
                'nominated_by': 'AUTO_IMPROVEMENT_ENGINE',
                'next_step': 'GUARDIAN_EVALUATION'
            })

            nominated.append({
                'variant_hash': variant_hash,
                'score': score,
                'status': 'AWAITING_GUARDIAN',
                'nominated_at': datetime.utcnow().isoformat()
            })

        logger.info(f"Nominated {len(nominated)} variants for Guardian review")
        return nominated

    def evaluate_with_guardian(self, nominated_variants: List[Dict[str, Any]],
                              guardian_evaluator) -> List[Dict[str, Any]]:
        """Submit variants to Guardian (blocks if evidence missing)"""
        reviewed = []

        for variant in nominated_variants:
            variant_hash = variant['variant_hash']

            # Call Guardian
            try:
                guardian_result = guardian_evaluator.evaluate(variant_hash)

                if guardian_result['verdict'] == 'PASS':
                    # Guardian passed, but ownership approval still required
                    self.audit.append({
                        'type': 'GUARDIAN_PASSED',
                        'variant_hash': variant_hash,
                        'verdict': 'PASS',
                        'next_step': 'AWAITING_OWNER_APPROVAL'
                    })

                    reviewed.append({
                        'variant_hash': variant_hash,
                        'guardian_verdict': 'PASS',
                        'status': 'AWAITING_OWNER_APPROVAL',
                        'reviewed_at': datetime.utcnow().isoformat()
                    })

                    logger.info(f"Variant {variant_hash[:8]}... passed Guardian, awaiting owner approval")

                else:
                    # Guardian rejected
                    self.audit.append({
                        'type': 'GUARDIAN_REJECTED',
                        'variant_hash': variant_hash,
                        'verdict': guardian_result['verdict'],
                        'reason': guardian_result.get('reasoning', 'Unknown')
                    })

                    reviewed.append({
                        'variant_hash': variant_hash,
                        'guardian_verdict': guardian_result['verdict'],
                        'status': 'REJECTED',
                        'reason': guardian_result.get('reasoning'),
                        'reviewed_at': datetime.utcnow().isoformat()
                    })

                    logger.info(f"Variant {variant_hash[:8]}... rejected by Guardian")

            except Exception as e:
                self.audit.append({
                    'type': 'GUARDIAN_ERROR',
                    'variant_hash': variant_hash,
                    'error': str(e)
                })

                reviewed.append({
                    'variant_hash': variant_hash,
                    'status': 'GUARDIAN_ERROR',
                    'error': str(e)
                })

        return reviewed

    def send_owner_approval_request(self, variants_awaiting_approval: List[Dict[str, Any]]) -> None:
        """Notify owner of pending approvals (cannot auto-approve)"""
        if not variants_awaiting_approval:
            return

        self.audit.append({
            'type': 'OWNER_APPROVAL_REQUESTED',
            'variant_count': len(variants_awaiting_approval),
            'variants': [v['variant_hash'] for v in variants_awaiting_approval],
            'timestamp': datetime.utcnow().isoformat()
        })

        # Send email/notification (implementation in main server)
        logger.warning(f"⚠ {len(variants_awaiting_approval)} variants awaiting owner approval")

    def IMPOSSIBLE_SELF_PROMOTE(self):
        """This method intentionally does not exist"""
        raise NotImplementedError(
            "Auto-improvement cannot promote. Owner decision only. "
            "See send_owner_approval_request() and owner_auth.py"
        )

    def IMPOSSIBLE_BYPASS_GUARDIAN(self):
        """This method intentionally does not exist"""
        raise NotImplementedError(
            "Guardian evaluation is mandatory. No bypass path exists."
        )


class VariantAnalyzer:
    """Identify top performers for variant generation"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger

    def identify_top_performers(self, backtest_results: List[Dict[str, Any]],
                               top_count: int = 5) -> List[Dict[str, Any]]:
        """Find top performers for variation"""
        # Sort by Sharpe ratio or P&L
        sorted_results = sorted(
            backtest_results,
            key=lambda x: x.get('sharpe_ratio', x.get('pnl', 0)),
            reverse=True
        )

        top = sorted_results[:top_count]

        logger.info(f"Top {len(top)} performers identified")
        return top

    def suggest_indicators(self, top_strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest indicators based on winning patterns"""
        suggestions = []

        # Simple heuristic: suggest complementary indicators
        current_indicators = top_strategy.get('indicators', [])

        candidate_indicators = [
            {'name': 'RSI', 'confidence': 0.7},
            {'name': 'MACD', 'confidence': 0.6},
            {'name': 'Bollinger Bands', 'confidence': 0.5},
            {'name': 'Stochastic', 'confidence': 0.55}
        ]

        for candidate in candidate_indicators:
            if candidate['name'] not in current_indicators:
                suggestions.append(candidate)

        logger.info(f"Suggested {len(suggestions)} indicators")
        return suggestions
