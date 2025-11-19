from decimal import Decimal
from finance_core.models.financial_report import FinancialReport
from finance_core.models.analytics import AnalyticsReport

def test_financial_logic():
    print("🧪 Testing Financial Logic with 2018 Data...")
    
    # 2018 Data
    data = {
        "period": "30-06-2018",
        "period_length": 12,
        "company_key": "test_company",
        "revenue": Decimal("6612000"),
        "cost_of_goods": Decimal("4694500"),
        "overheads": Decimal("1216200"),
        "interest_paid": Decimal("176000"),
        "tax_paid": Decimal("115300"),
        "dividends_paid": Decimal("150000"),
        "depreciation": Decimal("100000"),
        "extraordinary_expenses": Decimal("0"),
        
        "cash": Decimal("0"),
        "accounts_receivable": Decimal("1443000"),
        "inventory": Decimal("1550000"),
        "other_current_assets": Decimal("71000"),
        "fixed_assets": Decimal("1800000"),
        "other_non_current_assets": Decimal("150000"),
        
        "accounts_payable": Decimal("590000"),
        "bank_loans_short_term": Decimal("1643000"),
        "other_current_liabilities": Decimal("221000"),
        "bank_loans_long_term": Decimal("1200000"),
        "other_non_current_liabilities": Decimal("50000"),
        "equity": Decimal("1310000")
    }
    
    report = FinancialReport(**data)
    
    # Verify P&L
    assert report.gross_margin == Decimal("1917500"), f"Gross Margin mismatch: {report.gross_margin}"
    assert report.operating_profit == Decimal("701300"), f"Operating Profit mismatch: {report.operating_profit}"
    assert report.net_profit == Decimal("410000"), f"Net Profit mismatch: {report.net_profit}"
    assert report.retained_profit == Decimal("260000"), f"Retained Profit mismatch: {report.retained_profit}"
    assert report.ebitda == Decimal("801300"), f"EBITDA mismatch: {report.ebitda}"
    
    # Verify Balance Sheet
    assert report.total_assets == Decimal("5014000"), f"Total Assets mismatch: {report.total_assets}"
    # Note: My model's total_liabilities includes equity
    assert report.total_liabilities == Decimal("5014000"), f"Total Liabilities & Equity mismatch: {report.total_liabilities}"
    
    print("✅ FinancialReport Logic Verified.")
    
    # Verify Analytics
    analytics = AnalyticsReport.from_financial_report(report, "test_key")
    
    print("\n📊 Analytics Results:")
    print(f"Gross Margin %: {analytics.gross_margin_percent}% (Expected: 29.00%)")
    print(f"Operating Profit %: {analytics.operating_profit_percent}% (Expected: 10.61%)")
    print(f"Net Profit %: {analytics.net_profit_percent}% (Expected: 6.20%)")
    print(f"ROE: {analytics.roe}% (Expected: 31.30%)")
    print(f"ROA: {analytics.roa}% (Expected: 13.99%)")
    print(f"ROCE: {analytics.return_on_capital_employed}% (Expected: 16.89%)")
    print(f"Debt to Equity: {analytics.debt_to_equity} (Expected: 2.17)")
    print(f"Interest Cover: {analytics.interest_cover} (Expected: 3.98)")
    
    print(f"AR Days: {analytics.ar_days} (Expected: 79.66)")
    print(f"Inventory Days: {analytics.inventory_days} (Expected: 120.51)")
    print(f"AP Days: {analytics.ap_days} (Expected: 45.87)")
    print(f"Working Capital Days: {analytics.working_capital_days} (Expected: 154.30)")
    
    # Assertions with small tolerance
    assert abs(analytics.gross_margin_percent - 29.00) < 0.1
    assert abs(analytics.operating_profit_percent - 10.61) < 0.1
    assert abs(analytics.net_profit_percent - 6.20) < 0.1
    assert abs(analytics.roe - 31.30) < 0.1
    assert abs(analytics.roa - 13.99) < 0.1
    assert abs(analytics.return_on_capital_employed - 16.89) < 0.1
    assert abs(analytics.debt_to_equity - 2.17) < 0.1
    assert abs(analytics.interest_cover - 3.98) < 0.1
    
    assert abs(analytics.ar_days - 79.66) < 0.5
    assert abs(analytics.inventory_days - 120.51) < 0.5
    assert abs(analytics.ap_days - 45.87) < 0.5
    assert abs(analytics.working_capital_days - 154.30) < 0.5
    
    print("✅ Analytics Logic Verified.")

if __name__ == "__main__":
    test_financial_logic()
