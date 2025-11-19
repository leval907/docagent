from pydantic import BaseModel, Field, computed_field
from decimal import Decimal
from typing import Optional
from finance_core.models.financial_report import FinancialReport

class AnalyticsReport(BaseModel):
    financial_data_key: str = Field(..., description="Key of the source FinancialData document")
    
    # We need the source data to calculate these, but we might not want to store it all again.
    # However, for the computed_field to work, we need access to the values.
    # We can either pass the FinancialReport object to a factory method, or include the fields here.
    # A cleaner approach: A service that takes FinancialReport and produces AnalyticsReport.
    # But if we want Pydantic to handle it, we can make this model accept the values.
    
    # Let's define the fields that will be stored.
    working_capital_days: Optional[float] = None
    ar_days: Optional[float] = None
    inventory_days: Optional[float] = None
    ap_days: Optional[float] = None
    
    working_capital: Optional[float] = None
    current_ratio: Optional[float] = None
    net_debt: Optional[float] = None
    interest_cover: Optional[float] = None
    return_on_capital_employed: Optional[float] = None

    debt_to_equity: Optional[float] = None
    
    # Power of One (Impact values)
    poo_price_increase_1pct_profit: Optional[float] = None
    poo_volume_increase_1pct_profit: Optional[float] = None
    poo_cogs_reduction_1pct_profit: Optional[float] = None
    poo_overheads_reduction_1pct_profit: Optional[float] = None
    
    poo_price_increase_1pct_cash: Optional[float] = None
    poo_volume_increase_1pct_cash: Optional[float] = None # Usually same as profit or adjusted
    poo_cogs_reduction_1pct_cash: Optional[float] = None
    poo_overheads_reduction_1pct_cash: Optional[float] = None
    
    poo_ar_days_reduction_1day_cash: Optional[float] = None
    poo_inventory_days_reduction_1day_cash: Optional[float] = None
    poo_ap_days_increase_1day_cash: Optional[float] = None

    # Business Valuation
    valuation_ebitda: Optional[float] = None
    valuation_multiple: float = 4.0
    valuation_result: Optional[float] = None

    @classmethod
    def from_financial_report(cls, report: FinancialReport, key: str) -> 'AnalyticsReport':
        """Factory method to create AnalyticsReport from a FinancialReport."""
        
        # Helper to avoid division by zero
        def safe_div(n, d):
            return float(n / d) if d and d != 0 else 0.0

        # Convert Decimals to float for ratios
        revenue = float(report.revenue)
        cogs = float(report.cost_of_goods)
        equity = float(report.equity)
        total_assets = float(report.total_assets)
        
        # Debt components
        bank_loans_short = float(report.bank_loans_short_term)
        bank_loans_long = float(report.bank_loans_long_term)
        total_debt = bank_loans_short + bank_loans_long
        cash = float(report.cash)
        net_debt = total_debt - cash
        
        # Working Capital components
        ar = float(report.accounts_receivable)
        inventory = float(report.inventory)
        ap = float(report.accounts_payable)
        
        # Operating Profit for ROA/ROCE
        operating_profit = float(report.operating_profit)
        interest_paid = float(report.interest_paid)
        net_profit = float(report.net_profit)
        
        days_in_period = report.period_length * 30 # Approx
        if report.period_length == 12:
            days_in_period = 365

        # Ratios
        gross_margin_pct = safe_div(report.gross_margin, report.revenue) * 100
        operating_profit_pct = safe_div(report.operating_profit, report.revenue) * 100
        net_profit_pct = safe_div(report.net_profit, report.revenue) * 100
        
        roe = safe_div(net_profit, equity) * 100
        # Report uses Operating Profit for ROA
        roa = safe_div(operating_profit, total_assets) * 100
        asset_turnover = safe_div(revenue, total_assets)
        
        # Report uses Net Debt / Equity
        debt_to_equity = safe_div(net_debt, equity)
        
        # Interest Cover
        interest_cover = safe_div(operating_profit, interest_paid)
        
        # ROCE = Operating Profit / (Equity + Net Debt)
        capital_employed = equity + net_debt
        roce = safe_div(operating_profit, capital_employed) * 100
        
        # Current Ratio
        current_ratio = safe_div(report.current_assets, report.current_liabilities)

        # Days
        ar_days = safe_div(ar, revenue) * days_in_period
        inventory_days = safe_div(inventory, cogs) * days_in_period
        ap_days = safe_div(ap, cogs) * days_in_period # Using COGS as proxy for purchases
        
        # Trade Working Capital
        working_capital = ar + inventory - ap
        working_capital_days = ar_days + inventory_days - ap_days

        # --- Power of One Calculations ---
        # Impact on Profit
        poo_price_profit = revenue * 0.01
        poo_volume_profit = (revenue - cogs) * 0.01 # Gross Margin * 1%
        poo_cogs_profit = cogs * 0.01
        poo_overheads_profit = float(report.overheads) * 0.01
        
        # Impact on Cash (Simplified: usually same as profit for P&L items, except volume might need WC adjustment)
        # Report implies:
        # Price Increase 1%: Cash 51,690 vs Profit 66,120. Why? 
        # Maybe Tax effect? 66,120 * (1 - TaxRate)? 
        # Tax Rate: Tax Paid 115,300 / Net Profit Before Tax 525,300 = 21.9%.
        # 66,120 * (1 - 0.219) = 51,640. Close to 51,690.
        # Let's assume Cash Impact = Profit Impact * (1 - Tax Rate) for P&L items.
        # Tax Rate estimation:
        ebt = float(report.net_profit_before_tax)
        tax = float(report.tax_paid)
        tax_rate = safe_div(tax, ebt) if ebt > 0 else 0.0
        
        poo_price_cash = poo_price_profit * (1 - tax_rate)
        poo_volume_cash = poo_volume_profit * (1 - tax_rate) # Report says -4,855? 
        # Wait, Volume Increase 1% Cash Flow is NEGATIVE in report (-4,855).
        # This implies Working Capital drag exceeds Profit.
        # Profit 19,175. Cash -4,855. Diff ~ 24,000.
        # WC per $1 sales?
        # Let's skip complex Cash Flow modeling for Power of One for now unless requested, 
        # or just implement the Profit side which is clear.
        # But the Days impact is purely Cash.
        
        poo_ar_days_cash = revenue / days_in_period
        poo_inv_days_cash = cogs / days_in_period
        poo_ap_days_cash = cogs / days_in_period

        # --- Business Valuation ---
        # Report uses Adjusted EBITDA. We'll use EBITDA for now.
        ebitda = float(report.ebitda)
        valuation_val = (ebitda * 4.0) - net_debt

        return cls(
            financial_data_key=key,
            working_capital_days=round(working_capital_days, 2),
            ar_days=round(ar_days, 2),
            inventory_days=round(inventory_days, 2),
            ap_days=round(ap_days, 2),
            debt_to_equity=round(debt_to_equity, 2),
            roe=round(roe, 2),
            roa=round(roa, 2),
            asset_turnover=round(asset_turnover, 2),
            gross_margin_percent=round(gross_margin_pct, 2),
            operating_profit_percent=round(operating_profit_pct, 2),
            net_profit_percent=round(net_profit_pct, 2),
            working_capital=round(working_capital, 2),
            current_ratio=round(current_ratio, 2),
            net_debt=round(net_debt, 2),
            interest_cover=round(interest_cover, 2),
            return_on_capital_employed=round(roce, 2),
            
            # Power of One (Profit)
            poo_price_increase_1pct_profit=round(poo_price_profit, 2),
            poo_volume_increase_1pct_profit=round(poo_volume_profit, 2),
            poo_cogs_reduction_1pct_profit=round(poo_cogs_profit, 2),
            poo_overheads_reduction_1pct_profit=round(poo_overheads_profit, 2),
            
            # Power of One (Cash - Days only for now)
            poo_ar_days_reduction_1day_cash=round(poo_ar_days_cash, 2),
            poo_inventory_days_reduction_1day_cash=round(poo_inv_days_cash, 2),
            poo_ap_days_increase_1day_cash=round(poo_ap_days_cash, 2),
            
            # Valuation
            valuation_ebitda=round(ebitda, 2),
            valuation_result=round(valuation_val, 2)
        )

    def to_arango_doc(self) -> dict:
        return self.model_dump()
