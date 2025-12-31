##
import pandas as pd

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("Streamlit not installed. Run: pip install streamlit")

df = pd.read_csv('testout.csv')

pivot_table = df.pivot_table(
    index=['Category', 'SubCategory'], 
    values='Amount', 
    aggfunc='sum'
).rename(columns={'Amount': 'Actual'})

pivot_table['Budget'] = 0.0
pivot_table['Overspend'] = pivot_table['Actual'] - pivot_table['Budget']
pivot_table['Notes'] = ""

def add_totals(group):
    totals = group.sum(numeric_only=True).to_frame().T
    totals.index = pd.MultiIndex.from_tuples([(group.index[0][0], 'Total')])
    totals['Notes'] = ""
    return pd.concat([group, totals])

final_view = pivot_table.groupby(level=0, sort=False).apply(add_totals).reset_index(level=0, drop=True)

# Apply budget amounts to category totals after they're created
budget_df = pd.read_csv('testbudget.csv')
budget_dict = dict(zip(budget_df['Category'], budget_df['Amount']))

for category, budget in budget_dict.items():
    # Find the total row for this category and set its budget
    total_mask = final_view.index.get_level_values(1) == 'Total'
    category_mask = final_view.index.get_level_values(0) == category
    combined_mask = total_mask & category_mask
    if combined_mask.any():
        final_view.loc[combined_mask, 'Budget'] = budget

# Recalculate overspend after setting budgets (only for total rows)
final_view['Overspend'] = 0.0
total_rows_mask = final_view.index.get_level_values(1) == 'Total'
final_view.loc[total_rows_mask, 'Overspend'] = final_view.loc[total_rows_mask, 'Actual'] - final_view.loc[total_rows_mask, 'Budget']

# Add remaining budget column and percentage
final_view['Remaining'] = 0.0
final_view['Percentage'] = 0.0
final_view.loc[total_rows_mask, 'Remaining'] = final_view.loc[total_rows_mask, 'Budget'] - final_view.loc[total_rows_mask, 'Actual']
final_view.loc[total_rows_mask, 'Percentage'] = (final_view.loc[total_rows_mask, 'Actual'] / final_view.loc[total_rows_mask, 'Budget'] * 100).round(1)

# Reorder columns to include new columns
final_view = final_view[['Budget', 'Actual', 'Remaining', 'Percentage', 'Overspend', 'Notes']]

def display_data(df):
    """Display the budget data either in console or Streamlit"""
    if STREAMLIT_AVAILABLE:
        st.title("Budget Overview")
        
        # Add some summary metrics
        total_budget = df.loc[df.index.get_level_values(1) == 'Total', 'Budget'].sum()
        total_actual = df.loc[df.index.get_level_values(1) == 'Total', 'Actual'].sum()
        total_overspend = df.loc[df.index.get_level_values(1) == 'Total', 'Overspend'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Budget", f"${total_budget:,.2f}")
        with col2:
            st.metric("Total Actual", f"${total_actual:,.2f}")
        with col3:
            st.metric("Total Overspend", f"${total_overspend:,.2f}")
        
        # Display the main table
        st.dataframe(df, use_container_width=True)
        
        # Add download button
        csv = df.to_csv().encode('utf-8')
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name='budget_report.csv',
            mime='text/csv',
        )
    else:
        print(df)

def main():
    # Generate the final view
    
    # Load data
    df = pd.read_csv('testout.csv')
    
    # Create pivot table
    pivot_table = df.pivot_table(
        index=['Category', 'SubCategory'], 
        values='Amount', 
        aggfunc='sum'
    ).rename(columns={'Amount': 'Actual'})
    
    # Initialize columns
    pivot_table['Budget'] = 0.0
    pivot_table['Overspend'] = pivot_table['Actual'] - pivot_table['Budget']
    pivot_table['Notes'] = ""
    
    # Add totals
    def add_totals(group):
        totals = group.sum(numeric_only=True).to_frame().T
        totals.index = pd.MultiIndex.from_tuples([(group.index[0][0], 'Total')])
        totals['Notes'] = ""
        return pd.concat([group, totals])
    
    final_view = pivot_table.groupby(level=0, sort=False).apply(add_totals).reset_index(level=0, drop=True)
    
    # Apply budget amounts to category totals
    budget_df = pd.read_csv('testbudget.csv')
    budget_dict = dict(zip(budget_df['Category'], budget_df['Amount']))
    
    for category, budget in budget_dict.items():
        total_mask = final_view.index.get_level_values(1) == 'Total'
        category_mask = final_view.index.get_level_values(0) == category
        combined_mask = total_mask & category_mask
        if combined_mask.any():
            final_view.loc[combined_mask, 'Budget'] = budget
    
    # Calculate overspend only for total rows
    final_view['Overspend'] = 0.0
    total_rows_mask = final_view.index.get_level_values(1) == 'Total'
    final_view.loc[total_rows_mask, 'Overspend'] = final_view.loc[total_rows_mask, 'Actual'] - final_view.loc[total_rows_mask, 'Budget']
    
    # Add remaining budget and percentage
    final_view['Remaining'] = 0.0
    final_view['Percentage'] = 0.0
    final_view.loc[total_rows_mask, 'Remaining'] = final_view.loc[total_rows_mask, 'Budget'] - final_view.loc[total_rows_mask, 'Actual']
    final_view.loc[total_rows_mask, 'Percentage'] = (final_view.loc[total_rows_mask, 'Actual'] / final_view.loc[total_rows_mask, 'Budget'] * 100).round(1)
    
    # Reorder columns
    final_view = final_view[['Budget', 'Actual', 'Remaining', 'Percentage', 'Overspend', 'Notes']]
    
    # Display the data
    display_data(final_view)

if __name__ == "__main__":
    main()
