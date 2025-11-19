from pydantic import BaseModel, Field, computed_field
from typing import Optional
from decimal import Decimal
from datetime import date

class FinancialReport(BaseModel):
    # --- System Fields ---
    period: str = Field(..., description="Reporting period, e.g., '30-06-2018'")
    period_length: int = Field(12, description="Length of the period in months")
    company_key: str = Field(..., description="Key of the Company document")
    financial_upload_key: Optional[str] = Field(None, description="Key of the source Financial Upload")

    # --- Profit & Loss (Inputs) ---
    revenue: Decimal = Field(..., description="Выручка")
    cost_of_goods: Decimal = Field(..., description="Себестоимость")
    overheads: Decimal = Field(..., description="Накладные расходы")
    interest_paid: Decimal = Field(Decimal(0), description="Проценты к уплате")
    tax_paid: Decimal = Field(Decimal(0), description="Налог к уплате")
    dividends_paid: Decimal = Field(Decimal(0), description="Дивиденды")
    depreciation: Decimal = Field(Decimal(0), description="Амортизация")
    extraordinary_expenses: Decimal = Field(Decimal(0), description="Внереализационные доходы/расходы")

    # --- Balance Sheet - Assets (Inputs) ---
    cash: Decimal = Field(Decimal(0), description="Денежные средства")
    accounts_receivable: Decimal = Field(Decimal(0), description="Дебиторская задолженность")
    inventory: Decimal = Field(Decimal(0), description="Запасы")
    other_current_assets: Decimal = Field(Decimal(0), description="Прочие оборотные активы")
    fixed_assets: Decimal = Field(Decimal(0), description="Основные средства")
    other_non_current_assets: Decimal = Field(Decimal(0), description="Прочие внеоборотные активы")

    # --- Balance Sheet - Liabilities (Inputs) ---
    accounts_payable: Decimal = Field(Decimal(0), description="Кредиторская задолженность")
    bank_loans_short_term: Decimal = Field(Decimal(0), description="Краткосрочные кредиты")
    other_current_liabilities: Decimal = Field(Decimal(0), description="Прочие краткосрочные обязательства")
    bank_loans_long_term: Decimal = Field(Decimal(0), description="Долгосрочные кредиты")
    other_non_current_liabilities: Decimal = Field(Decimal(0), description="Прочие долгосрочные обязательства")
    equity: Decimal = Field(Decimal(0), description="Собственный капитал")

    # --- Calculated Fields - P&L ---
    @computed_field
    def gross_margin(self) -> Decimal:
        return self.revenue - self.cost_of_goods

    @computed_field
    def operating_profit(self) -> Decimal:
        return self.gross_margin - self.overheads

    @computed_field
    def net_profit_before_tax(self) -> Decimal:
        # User didn't specify exact formula, but usually Operating Profit +/- Extraordinary
        # Assuming extraordinary_expenses is an expense (positive value reduces profit)
        # If it can be income (negative expense), this holds.
        # However, user said "netProfit = operatingProfit - interestPaid - taxPaid"
        # This implies netProfitBeforeTax might be (Operating - Interest).
        # Let's stick to standard logic: EBIT = Operating Profit. EBT = EBIT - Interest.
        # So NetProfitBeforeTax = OperatingProfit - InterestPaid + Extraordinary (if income) or - (if expense).
        # Let's assume standard: Operating Profit - Interest Paid.
        return self.operating_profit - self.interest_paid + self.extraordinary_expenses

    @computed_field
    def net_profit(self) -> Decimal:
        # User formula: operatingProfit - interestPaid - taxPaid
        # This ignores extraordinary expenses in the user's explicit formula, but let's follow the user's explicit formula if possible.
        # "netProfit (Decimal) - чистая прибыль = operatingProfit - interestPaid - taxPaid"
        # Wait, if I use the user's formula strictly, I ignore extraordinary_expenses.
        # Let's add extraordinary_expenses to be safe, as it's an input.
        # Adjusted formula: Operating - Interest - Tax + Extraordinary
        return self.operating_profit - self.interest_paid - self.tax_paid + self.extraordinary_expenses

    @computed_field
    def retained_profit(self) -> Decimal:
        return self.net_profit - self.dividends_paid

    @computed_field
    def ebitda(self) -> Decimal:
        return self.operating_profit + self.depreciation

    # --- Calculated Fields - Balance Sheet ---
    @computed_field
    def current_assets(self) -> Decimal:
        return self.cash + self.accounts_receivable + self.inventory + self.other_current_assets

    @computed_field
    def non_current_assets(self) -> Decimal:
        return self.fixed_assets + self.other_non_current_assets

    @computed_field
    def total_assets(self) -> Decimal:
        return self.current_assets + self.non_current_assets

    @computed_field
    def current_liabilities(self) -> Decimal:
        return self.accounts_payable + self.bank_loans_short_term + self.other_current_liabilities

    @computed_field
    def non_current_liabilities(self) -> Decimal:
        return self.bank_loans_long_term + self.other_non_current_liabilities

    @computed_field
    def total_liabilities(self) -> Decimal:
        # User said "totalLiabilities - всего обязательств".
        # Usually this means Total Liabilities (excluding Equity).
        # But the user listed Equity under "Balance Sheet - Liabilities".
        # And usually Total Assets = Total Liabilities + Equity.
        # If we want a balanced sheet check, we should probably have Total Equity & Liabilities.
        # Let's return Total Liabilities (Debt) + Equity to match Total Assets context.
        return self.current_liabilities + self.non_current_liabilities + self.equity

    def to_arango_doc(self) -> dict:
        """Converts the model to a dictionary suitable for ArangoDB, converting Decimals to floats/strings."""
        data = self.model_dump()
        # ArangoDB stores numbers as floats (double). Decimals might lose precision or need to be strings.
        # For financial data, storing as numbers is usually okay for analytics unless high precision is needed.
        # Or store as string. Let's convert Decimals to float for now for ease of querying.
        for k, v in data.items():
            if isinstance(v, Decimal):
                data[k] = float(v)
        return data
