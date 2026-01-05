import pandas as pd
import streamlit as st
import plotly.express as px
import base64
from datetime import datetime, date
import calendar
import json
import os
import sys
from vulkan_api import VulkanAPI

def get_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

@st.cache_data
def load_and_process_data(selected_date=None, use_api=True):
    current_month = selected_date.strftime("%Y-%m") if selected_date else datetime.now().strftime("%Y-%m")
    
    if use_api:
        # API-based data loading
        api = VulkanAPI()
        df = api.get_transactions()
        budget_dict = api.get_budget(current_month)
    else:
        # Local file-based data loading
        df = pd.read_csv('test/testout.csv')
        with open('test/testbudget.json', 'r') as f:
            budget_data = json.load(f)
        budget_dict = budget_data.get(current_month, {})
    
    # Check if budget exists
    has_budget = len(budget_dict) > 0
    
    # Calculate total budget from source (not just categories with transactions)
    total_budget = sum(budget_dict.values()) if budget_dict else 0
    
    # Filter out 'Fun' category
    if not df.empty:
        df = df[df['Category'] != 'Fun']
    
    # Filter data by selected month if provided
    if selected_date and not df.empty:
        # Convert Date column to datetime if it's not already
        df['Date'] = pd.to_datetime(df['Date'])
        # Filter for selected month and year
        year, month = selected_date.year, selected_date.month
        df = df[(df['Date'].dt.year == year) & (df['Date'].dt.month == month)]
        # Convert back to string format for consistency
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    
    # Return empty DataFrame if no data found
    if df.empty:
        empty_df = pd.DataFrame(columns=['Budget', 'Actual', 'Remaining', 'Percentage', 'Overspend', 'Notes'], 
                               index=pd.MultiIndex.from_tuples([], names=['Category', 'SubCategory']))
        return empty_df, has_budget
    
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
    
    # Apply budget amounts to category totals from API or local data
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
    # Avoid division by zero - simpler approach
    total_rows = final_view.loc[total_rows_mask]
    for idx in total_rows.index:
        budget = final_view.loc[idx, 'Budget']
        actual = final_view.loc[idx, 'Actual']
        if budget > 0:
            final_view.loc[idx, 'Percentage'] = (actual / budget * 100).round(1)
    
    # Reorder columns
    final_view = final_view[['Budget', 'Actual', 'Remaining', 'Percentage', 'Overspend', 'Notes']]
    
    return final_view, has_budget, budget_dict

def main():
    # Check for test mode flag
    use_api = '--test' not in sys.argv
    
    # Set page configuration
    st.set_page_config(layout="wide", page_title="Goblin", page_icon="goblin-mascot.png")
    
    # Reduce top margin of main content
    st.markdown("""
    <style>
    .stMainBlockContainer.block-container {
        padding-top: 30px !important;
        margin-top: 0 !important;
    }
    
    .main .block-container {
        padding-top: 30px !important;
        margin-top: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.3rem;">
        <img src="data:image/png;base64,{}" width="50" style="margin: 0;">
        <h1 style="margin: 0;">Goblin</h1>
    </div>
    """.format(get_base64("goblin-mascot.png")), unsafe_allow_html=True)
    
    # Month selector
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = date.today().replace(day=1)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("← Previous", key="prev_month"):
            if st.session_state.selected_date.month == 1:
                st.session_state.selected_date = st.session_state.selected_date.replace(year=st.session_state.selected_date.year - 1, month=12)
            else:
                st.session_state.selected_date = st.session_state.selected_date.replace(month=st.session_state.selected_date.month - 1)
            st.rerun()
    
    with col2:
        month_name = calendar.month_name[st.session_state.selected_date.month]
        st.markdown(f"<h2 style='text-align: center; margin: 0;'>{month_name} {st.session_state.selected_date.year}</h2>", unsafe_allow_html=True)
    
    with col3:
        if st.button("Next →", key="next_month"):
            if st.session_state.selected_date.month == 12:
                st.session_state.selected_date = st.session_state.selected_date.replace(year=st.session_state.selected_date.year + 1, month=1)
            else:
                st.session_state.selected_date = st.session_state.selected_date.replace(month=st.session_state.selected_date.month + 1)
            st.rerun()
    
    # Load and process data with selected month
    df, has_budget, budget_dict = load_and_process_data(st.session_state.selected_date, use_api=use_api)
    
    # Show budget warning if no budget detected
    if not has_budget:
        st.error("🚨 No budget detected for selected month - showing $0 for all categories")
    
    # Check if no data found for selected month
    if df.empty:
        st.warning(f"No data found for {calendar.month_name[st.session_state.selected_date.month]} {st.session_state.selected_date.year}")
        return
    
    # Calculate overall totals
    total_rows = df.loc[df.index.get_level_values(1) == 'Total']
    total_actual = total_rows['Actual'].sum()
    total_remaining = total_rows['Remaining'].sum()
    # Note: total_budget is now calculated in load_and_process_data function
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Budget", f"£{sum(budget_dict.values()):,.2f}")
    with col2:
        st.metric("Total Spent", f"£{total_actual:,.2f}")
    with col3:
        remaining_budget = sum(budget_dict.values()) - total_actual if budget_dict else -total_actual
        if remaining_budget >= 0:
            st.markdown(f"<span style='color:green; font-size:14px;'>Total Remaining</span><br><span style='color:green; font-size:32px; font-weight:bold;'>£{remaining_budget:,.2f}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color:red; font-size:14px;'>Total Overspent</span><br><span style='color:red; font-size:32px; font-weight:bold;'>£{abs(remaining_budget):,.2f}</span>", unsafe_allow_html=True)
    with col4:
        total_percentage = (total_actual / sum(budget_dict.values()) * 100) if budget_dict and sum(budget_dict.values()) > 0 else 0
        st.metric("Budget Used", f"{total_percentage:.1f}%")
    
    st.divider()
    
    # Create tabs for Out, Budget, and In
    tab_out, tab_budget, tab_in = st.tabs(["Out", "Budget", "In"])
    
    with tab_out:
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
            
            st.plotly_chart(fig, width="stretch")
        
        # Load all transactions to calculate credit spending
        if use_api:
            api_instance = VulkanAPI()
            all_transactions = api_instance.get_transactions()
        else:
            all_transactions = pd.read_csv('test/testout.csv')
        all_transactions['Date'] = pd.to_datetime(all_transactions['Date'])
        
        # Filter for selected month and credit payments
        year, month = st.session_state.selected_date.year, st.session_state.selected_date.month
        credit_transactions = all_transactions[
            (all_transactions['Date'].dt.year == year) & 
            (all_transactions['Date'].dt.month == month) &
            (all_transactions['PaymentMethod'].str.contains('Credit', case=False, na=False))
        ]
        
        total_credit_spending = credit_transactions['Amount'].sum()
        
        # Display total credit spending
        st.metric("Credit Pot", f"£{total_credit_spending:,.2f}")
        
        # Show credit transactions if any
        if not credit_transactions.empty:
            with st.expander("View Credit Transactions", expanded=False):
                credit_display = credit_transactions[['Date', 'Name', 'Amount', 'SubCategory']].copy()
                credit_display = credit_display.iloc[::-1]  # Most recent first
                st.dataframe(credit_display.style.format({'Amount': '£{:,.2f}'}), width="stretch", hide_index=True)
    
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
}), width="stretch", hide_index=True)
                    
                    # Add "See Transactions" dropdown
                    with st.expander("See Transactions", expanded=False):
                        # Load original transaction data for this category
                        if use_api:
                            api_instance = VulkanAPI()
                            transactions_df = api_instance.get_transactions()
                        else:
                            transactions_df = pd.read_csv('test/testout.csv')
                        category_transactions = transactions_df[transactions_df['Category'] == category].copy()
                        
                        # Format and display transactions
                        category_transactions = category_transactions[['Date', 'Name', 'Amount', 'SubCategory', 'PaymentMethod', 'Notes']].copy()
                        category_transactions = category_transactions.iloc[::-1]
                        
                        st.dataframe(category_transactions.style.format({'Amount': '£{:,.2f}'}), width="stretch", hide_index=True)
            
            with col2:
                # Show only colored status on the right
                if budget > 0:
                    if remaining >= 0:
                        st.markdown(f"<span style='color:green; font-size:20px; font-weight:bold;'>£{remaining:,.2f}</span><br><span style='color:green; font-size:14px;'>left</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:red; font-size:20px; font-weight:bold;'>£{abs(remaining):,.2f}</span><br><span style='color:red; font-size:14px;'>overspent</span>", unsafe_allow_html=True)
                else:
                    st.write("No budget")
    
    with tab_budget:
        st.markdown("## 📊 Budget Overview")
        
        # Get current month budget data
        current_month = st.session_state.selected_date.strftime("%Y-%m")
        if use_api:
            api = VulkanAPI()
            budget_data = api.get_budget(current_month)
        else:
            with open('test/testbudget.json', 'r') as f:
                all_budget_data = json.load(f)
            budget_data = all_budget_data.get(current_month, {})
        
        if budget_data:
            st.write(f"**Budget for {current_month}:**")
            
            # Create two columns for budget display
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Budget Categories")
                # Create a DataFrame for better display
                budget_df = pd.DataFrame(list(budget_data.items()), columns=['Category', 'Amount'])
                budget_df = budget_df.sort_values('Amount', ascending=False)
                
                # Display budget table
                st.dataframe(
                    budget_df.style.format({'Amount': '£{:,.2f}'}),
                    width="stretch",
                    hide_index=True
                )
            
            with col2:
                st.markdown("### Budget Summary")
                total_monthly_budget = sum(budget_data.values())
                st.metric("Total Monthly Budget", f"£{total_monthly_budget:,.2f}")
                
                # Show budget breakdown
                st.markdown("### Top Categories")
                top_categories = budget_df.head(5)  # Top 5 categories
                for _, row in top_categories.iterrows():
                    percentage = (row['Amount'] / total_monthly_budget * 100) if total_monthly_budget > 0 else 0
                    st.write(f"**{row['Category']}**: £{row['Amount']:,.2f} ({percentage:.1f}%)")
        else:
            st.warning(f"No budget data found for {current_month}")
    
    with tab_in:
                st.markdown("## 💰 Income")
                st.write("Income tracking coming soon...")
                # TODO: Add income tracking functionality here
    
    # Add footer with raw data buttons
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("📊 View Raw Transactions", key="view_transactions"):
            # Create transaction data for display
            if use_api:
                api_instance = VulkanAPI()
                all_transactions = api_instance.get_transactions()
            else:
                all_transactions = pd.read_csv('test/testout.csv')
            
            # Format date and sort by date (newest first)
            all_transactions['Date'] = pd.to_datetime(all_transactions['Date'])
            all_transactions = all_transactions.sort_values('Date', ascending=False)
            all_transactions['Date'] = all_transactions['Date'].dt.strftime('%Y-%m-%d')
            
            # Store in session state for the modal
            st.session_state.show_raw_transactions = all_transactions
            st.session_state.show_raw_transactions_modal = True
            st.rerun()
    
    with col2:
        if st.button("💰 View Raw Budget", key="view_budget"):
            # Create budget data for display
            current_month = st.session_state.selected_date.strftime("%Y-%m")
            if use_api:
                api = VulkanAPI()
                budget_data = api.get_budget(current_month)
            else:
                with open('test/testbudget.json', 'r') as f:
                    all_budget_data = json.load(f)
                budget_data = all_budget_data.get(current_month, {})
            
            # Store in session state for the modal
            st.session_state.show_raw_budget = budget_data
            st.session_state.show_raw_budget_modal = True
            st.rerun()
    
    with col3:
        st.markdown(f"<small style='color: gray;'>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>", unsafe_allow_html=True)
    
    # Modals for raw data display
    if st.session_state.get('show_raw_transactions_modal', False):
        st.session_state.show_raw_transactions_modal = False
        with st.expander("📊 Raw Transaction Data", expanded=True):
            transactions_df = st.session_state.show_raw_transactions
            st.dataframe(
                transactions_df.style.format({'Amount': '£{:,.2f}'}),
                width="stretch",
                height=600
            )
            st.markdown(f"**Total Transactions:** {len(transactions_df)}")
            st.markdown(f"**Date Range:** {transactions_df['Date'].min()} to {transactions_df['Date'].max()}")
            if st.button("Close Transactions", key="close_transactions"):
                del st.session_state.show_raw_transactions
                st.rerun()
    
    if st.session_state.get('show_raw_budget_modal', False):
        st.session_state.show_raw_budget_modal = False
        with st.expander("💰 Raw Budget Data", expanded=True):
            budget_data = st.session_state.show_raw_budget
            if budget_data:
                budget_df = pd.DataFrame(list(budget_data.items()), columns=['Category', 'Amount'])
                budget_df = budget_df.sort_values('Amount', ascending=False)
                st.dataframe(
                    budget_df.style.format({'Amount': '£{:,.2f}'}),
                    width="stretch"
                )
                st.markdown(f"**Total Budget:** £{sum(budget_data.values()):,.2f}")
                st.markdown(f"**Categories:** {len(budget_data)}")
            else:
                st.warning("No budget data found for selected month")
            if st.button("Close Budget", key="close_budget"):
                del st.session_state.show_raw_budget
                st.rerun()

if __name__ == "__main__":
    main()