import requests
import pandas as pd
from io import StringIO
from typing import Dict
import os
import streamlit as st

class VulkanAPI:
    def __init__(self):
        self.base_url = os.getenv('VULKAN_API_URL')
        self.headers = {'X-API-KEY': os.getenv('WELL_API_KEY')}
    
    def get_transactions(self) -> pd.DataFrame:
        """Fetch all transactions from API"""
        try:
            response = requests.get(f"{self.base_url}/vault/data", headers=self.headers)
            response.raise_for_status()
            return pd.read_csv(StringIO(response.text))
        except requests.RequestException as e:
            st.error(f"Failed to fetch transactions from API: {e}")
            return pd.DataFrame()
    
    def get_budget(self, month: str) -> Dict:
        """Fetch budget data for specific month"""
        try:
            response = requests.get(f"{self.base_url}/vault/budget", headers=self.headers)
            response.raise_for_status()
            budget_data = response.json()
            return budget_data.get(month, {})
        except requests.RequestException as e:
            st.error(f"Failed to fetch budget from API: {e}")
            return {}
