"""Constants for Case Manager E2E tests.

Imported from case-manager-automation repository:
https://git.exness.io/trading-anti-fraud/case-manager-automation
"""

from enum import Enum


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Connections(Enum):
    STRONG = "strong"
    FAR = "far"
    NO = "no"


class InvestigationOutcome(Enum):
    CLEAR = "clear"
    ABUSIVE = "abusive"
    SUSPICIOUS = "suspicious"


class AbuseType(Enum):
    ARBITRAGE = "Arbitrage"
    B2B = "B2B"
    BONUS = "Bonus"
    CLOSE_HEDGE = "CloseHedge"
    DIVIDENDS = "Dividends"
    GAP_TOXICITY = "GapToxicity"
    MIRROR_LOCK = "MirrorLock"
    OTHER = "Other"
    PRICING = "Pricing"
    ROLLOVER = "Rollover"
    STOP_ORDERS = "StopOrders"
    SWAP_FREE = "SwapFree"
    TOXICITY = "Toxicity"


class Process(Enum):
    ABUSE_ALERTS = "abuse_alerts"
    ARBITRAGE_CHECK = "arbitrage_check"
    BONUS_CHECK = "bonus_check"
    CONNECTION = "connection"
    MIRROR_CHECK = "mirror_check"
    NULL_REPORT = "null_report"
    PROFITABILITY_ALERTS = "profitability_alerts"
    ROLLOVER_CHECK = "rollover_check"
    STOP_ORDERS_CHECK = "stop_orders_check"
    SWAP_CHECK = "swap_check"
    TOP_EQUITY_CHECK = "top_equity_check"
    TOP_PROFIT_CHECK = "top_profit_check"
    TOP_VOLUME_CHECK = "top_volume_check"


# Validation rules from source code analysis:
# Monitoring case required: title, user_uids (valid UUID), abuse_type, process, severity, description, jira_tickets
#   If severity=critical: link required + files required
# Reporting case required: user_uids (valid UUID), abuse_type, symbol, severity, description
#   If severity=critical: link required (no files needed)
#   If severity!=critical: files required + suspicious_timeframe required
