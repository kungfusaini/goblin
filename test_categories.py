#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from streamlit_budget import load_and_process_data
from datetime import date

def test_category_display():
    """Test that the category display logic works correctly"""
    
    # Test with current data
    selected_date = date(2026, 1, 1)
    df, has_budget, budget_dict = load_and_process_data(selected_date, use_api=False)
    
    print("Budget categories:", list(budget_dict.keys()))
    
    if not df.empty:
        df_display = df.reset_index()
        if 'Category' not in df_display.columns:
            df_display['Category'] = df.index.get_level_values(0).values
        
        transaction_categories = df_display['Category'].unique()
        print("Transaction categories:", list(transaction_categories))
        
        # Test the new logic for getting all categories
        all_categories = set(budget_dict.keys()) if budget_dict else set()
        all_categories.update(df_display['Category'].unique() if not df_display.empty else [])
        categories = list(all_categories)
        
        print("All categories that should be displayed:", sorted(categories))
        
        # Get total rows
        total_rows = df.loc[df.index.get_level_values(1) == 'Total'].copy()
        total_rows['Category'] = total_rows.index.get_level_values(0)
        
        # Test category budget lookup
        category_budgets = {}
        for category in categories:
            category_budgets[category] = budget_dict.get(category, 0.0)
            
        print("Category budgets:")
        for category, budget in category_budgets.items():
            print(f"  {category}: £{budget}")
            
        # Test the category summary handling
        print("\nTesting category summary handling:")
        for category in categories:
            category_row = total_rows[total_rows['Category'] == category]
            if category_row.empty:
                print(f"  {category}: No transactions (budget only)")
                budget = budget_dict.get(category, 0)
                actual = 0
                remaining = budget
            else:
                category_summary = category_row.iloc[0]
                budget = category_summary['Budget']
                actual = category_summary['Actual']
                remaining = category_summary['Remaining']
                print(f"  {category}: Budget £{budget}, Actual £{actual}, Remaining £{remaining}")
    else:
        print("No data found")

if __name__ == "__main__":
    test_category_display()