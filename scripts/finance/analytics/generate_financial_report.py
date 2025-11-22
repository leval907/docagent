import os
from arango import ArangoClient
from sentence_transformers import SentenceTransformer
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Config
ARANGO_URL = "http://localhost:8529"
ARANGO_DB = "finance_analytics"
ARANGO_USER = "root"
ARANGO_PASSWORD = "strongpassword"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

class FinancialAnalyst:
    def __init__(self):
        self.client = ArangoClient(hosts=ARANGO_URL)
        self.db = self.client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD)
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
    def search_methodology(self, query, limit=3):
        """Finds relevant methodology chunks using vector search."""
        query_embedding = self.model.encode(query).tolist()
        
        # Note: In a real production setup with ArangoSearch, we would use a VIEW.
        # Since we didn't set up the View in the previous step (we skipped it for simplicity),
        # we will do a brute-force cosine similarity in AQL for this demo.
        # For small datasets (like our 25 chunks), this is instant.
        
        aql = """
        FOR doc IN document_chunks
            LET cosine_sim = COSINE_SIMILARITY(doc.embedding, @query_vec)
            SORT cosine_sim DESC
            LIMIT @limit
            RETURN {
                text: doc.text,
                score: cosine_sim,
                source: doc.source
            }
        """
        
        cursor = self.db.aql.execute(aql, bind_vars={"query_vec": query_embedding, "limit": limit})
        return list(cursor)

    def get_account_balance(self, account_code):
        """Calculates balance for an account from the graph."""
        # This is a simplified calculation. 
        # In reality, we need to sum debits and credits correctly based on account type.
        # For now, we sum 'amount' from Incurred edges or Transactions.
        
        # Try Incurred edges (Costs, CashFlow)
        aql_incurred = """
        FOR e IN Incurred
            FILTER e.account == @code
            RETURN e.amount
        """
        cursor = self.db.aql.execute(aql_incurred, bind_vars={"code": account_code})
        total = sum([x for x in cursor])
        
        # Try Transactions (Suppliers 60)
        if account_code == '60':
            aql_trans = """
            FOR t IN Transactions
                RETURN t.debt_end
            """
            cursor = self.db.aql.execute(aql_trans)
            total = sum([x for x in cursor])
            
        return total

    def calculate_liquidity(self):
        print("\n🔍 Analyzing Liquidity...")
        
        # 1. Find Methodology
        docs = self.search_methodology("Как рассчитать коэффициент текущей ликвидности?")
        print(f"   ℹ️  Methodology found in: {docs[0]['source']}")
        print(f"   📖 Context: {docs[0]['text'][:150]}...")
        
        # 2. Get Data (Simplified mapping based on standard Russian accounting)
        # Current Assets (OA) ~ Cash (50, 51, 52) + AR (62) + Inventory (10, 41, 43)
        # Current Liabilities (TO) ~ AP (60, 76) + Short-term loans (66)
        
        cash = self.get_account_balance('51') + self.get_account_balance('50')
        # We don't have 62 fully imported yet in edges, but let's assume 0 if missing
        ar = self.get_account_balance('62') 
        inventory = self.get_account_balance('10') + self.get_account_balance('41')
        
        current_assets = cash + ar + inventory
        
        ap = self.get_account_balance('60')
        loans = self.get_account_balance('66')
        
        current_liabilities = ap + loans
        
        if current_liabilities == 0:
            ratio = 0
        else:
            ratio = current_assets / current_liabilities
            
        print(f"   💰 Current Assets: {current_assets:,.2f}")
        print(f"   📉 Current Liabilities: {current_liabilities:,.2f}")
        print(f"   📊 Current Liquidity Ratio: {ratio:.2f}")
        
        return ratio

    def calculate_power_of_one(self):
        print("\n🔍 Analyzing 'Power of One'...")
        
        # 1. Find Methodology
        docs = self.search_methodology("Влияние изменения цены на 1% на денежный поток")
        print(f"   ℹ️  Methodology found in: {docs[0]['source']}")
        
        # 2. Calculate Impact (Hypothetical)
        # Need Revenue and Profit
        # Revenue ~ Credit turnover of 90.01 (Sales)
        # We don't have 90.01 fully mapped in edges yet, let's estimate from Inflows (51) as proxy for Revenue
        
        revenue_proxy = self.get_account_balance('51') # Cash Inflow
        
        impact_price_1pct = revenue_proxy * 0.01
        
        print(f"   💵 Estimated Revenue (Cash Inflow): {revenue_proxy:,.2f}")
        print(f"   🚀 Impact of +1% Price on Cash Flow: +{impact_price_1pct:,.2f}")

    def run(self):
        print("🤖 Financial Analyst Agent Started")
        print("================================")
        
        self.calculate_liquidity()
        self.calculate_power_of_one()
        
        print("\n✅ Analysis Complete.")

if __name__ == "__main__":
    analyst = FinancialAnalyst()
    analyst.run()
