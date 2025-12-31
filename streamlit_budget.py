import pandas as pd
import streamlit as st
import plotly.express as px

def load_and_process_data():
    # Load data and filter out 'Fun' category
    df = pd.read_csv('testout.csv')
    df = df[df['Category'] != 'Fun']
    
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
    
    return final_view

def main():
    # Make page full width
    st.set_page_config(layout="wide")
    
# Set page title and load data
    st.set_page_config(page_title="Goblin", page_icon="🟢")
    
    st.markdown("# 🟢 Goblin")
    
    # Load and process data
    df = load_and_process_data()
    
    # Calculate overall totals
    total_rows = df.loc[df.index.get_level_values(1) == 'Total']
    total_budget = total_rows['Budget'].sum()
    total_actual = total_rows['Actual'].sum()
    total_remaining = total_rows['Remaining'].sum()
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Budget", f"£{total_budget:,.2f}")
    with col2:
        st.metric("Total Spent", f"£{total_actual:,.2f}")
    with col3:
        if total_remaining >= 0:
            st.markdown(f"<span style='color:green; font-size:14px;'>Total Remaining</span><br><span style='color:green; font-size:32px; font-weight:bold;'>£{total_remaining:,.2f}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color:red; font-size:14px;'>Total Overspent</span><br><span style='color:red; font-size:32px; font-weight:bold;'>£{abs(total_remaining):,.2f}</span>", unsafe_allow_html=True)
    with col4:
        total_percentage = (total_actual / total_budget * 100) if total_budget > 0 else 0
        st.metric("Budget Used", f"{total_percentage:.1f}%")
    
    st.divider()
    
    # Create two columns layout for pie chart and category bars
    col_bars, col_pie = st.columns([1, 1])
    
    with col_pie:
        st.markdown("## Spending Breakdown")
        
        # Get actual spending data for pie chart
        total_rows = df.loc[df.index.get_level_values(1) == 'Total'].copy()
        total_rows['Category'] = total_rows.index.get_level_values(0)
        
        # Prepare data for pie chart
        pie_data = total_rows[['Category', 'Actual']].copy()
        pie_data = pie_data[pie_data['Actual'] > 0]  # Only show categories with spending
        
        # Create pie chart
        if not pie_data.empty:
            fig = px.pie(pie_data, values='Actual', names='Category', 
                        title='Total Spending by Category')
            
            # Customize the chart
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label', 
                showlegend=False,
                hovertemplate='£%{value:.2f}<extra></extra>'
            )
            fig.update_layout(height=500)
            
            st.plotly_chart(fig, use_container_width=True)
    
    with col_bars:
        st.markdown("## Category Details")
        
        # Create collapsible categories with summary bars
        df_display = df.reset_index()
        
        # If Category is not a column, extract it from the original index
        if 'Category' not in df_display.columns:
            df_display['Category'] = df.index.get_level_values(0).values
        
        categories = df_display['Category'].unique()
        
        # Get total rows for summary data
        total_rows = df.loc[df.index.get_level_values(1) == 'Total'].copy()
        total_rows['Category'] = total_rows.index.get_level_values(0)
        
        # Get total rows for summary data
        total_rows = df.loc[df.index.get_level_values(1) == 'Total'].copy()
        total_rows['Category'] = total_rows.index.get_level_values(0)
        
        # Sort categories by budget amount (descending)
        category_budgets = {}
        for category in categories:
            category_summary = total_rows[total_rows['Category'] == category]
            if not category_summary.empty:
                category_budgets[category] = category_summary.iloc[0]['Budget']
            else:
                category_budgets[category] = 0
        
        sorted_categories = sorted(category_budgets.items(), key=lambda x: x[1], reverse=True)
        
        for category, _ in sorted_categories:
            # Get data for this category
            category_data = df_display[df_display['Category'] == category].copy()
            
            # Get summary data for this category
            category_summary = total_rows[total_rows['Category'] == category].iloc[0]
            budget = category_summary['Budget']
            actual = category_summary['Actual']
            remaining = category_summary['Remaining']
            
            # Create expander with status next to it
            col1, col2 = st.columns([4, 1])
            
            with col1:
                with st.expander(f"**{category}**", expanded=False):
                    # Show progress bar at the top
                    if budget > 0:
                        percentage_used = min(actual / budget * 100, 100)
                        st.progress(min(percentage_used / 100, 1.0))
                        st.caption(f"{percentage_used:.1f}% used")
                    # Show summary metrics first
                    col1a, col2a = st.columns(2)
                    
                    with col1a:
                        st.metric("Total Budget", f"£{budget:,.2f}")
                        
                    with col2a:
                        st.metric("Total Spent", f"£{actual:,.2f}")
                    
    
                    
                    # Show detailed subcategory information
                    # Note: after reset_index(), SubCategory is "level_1"
                    category_display = pd.DataFrame({
                        'SubCategory': category_data['level_1'],
                        'Actual': category_data['Actual']
                    })
                    
                    # Filter out Total and empty rows
                    mask = (category_display['SubCategory'] != 'Total') & (category_display['SubCategory'].notna()) & (category_display['SubCategory'] != '')
                    category_display = category_display[mask]
                    
# Calculate contribution percentage for each subcategory
                    category_display['Contribution'] = (category_display['Actual'] / actual * 100).round(1) if actual > 0 else 0
                    
                    # Show subcategory table with contribution
                    st.dataframe(category_display.style.format({
                        'Actual': '£{:,.2f}',
                        'Contribution': '{:.1f}%'
                    }), use_container_width=True, hide_index=True)
                    
                    # Add "See Transactions" dropdown
                    with st.expander("See Transactions", expanded=False):
                        # Load original transaction data for this category
                        transactions_df = pd.read_csv('testout.csv')
                        category_transactions = transactions_df[transactions_df['Category'] == category].copy()
                        
                        # Format and display transactions
                        category_transactions = category_transactions[['Date', 'Name', 'Amount', 'SubCategory', 'PaymentMethod', 'Notes']].copy()
                        category_transactions = category_transactions.iloc[::-1]
                        
                        st.dataframe(category_transactions.style.format({'Amount': '£{:,.2f}'}), use_container_width=True, hide_index=True)
            
            with col2:
                # Show only colored status on the right
                if budget > 0:
                    if remaining >= 0:
                        st.markdown(f"<span style='color:green; font-size:20px; font-weight:bold;'>£{remaining:,.2f}</span><br><span style='color:green; font-size:14px;'>left</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:red; font-size:20px; font-weight:bold;'>£{abs(remaining):,.2f}</span><br><span style='color:red; font-size:14px;'>overspent</span>", unsafe_allow_html=True)
                else:
                    st.write("No<br>budget")
            
            
    
    

if __name__ == "__main__":
    main()