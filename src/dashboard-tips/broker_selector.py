# broker_selector.py - Reusable Broker Selection Component

from shiny import reactive, render
from shiny.express import input, ui
from typing import List, Dict, Any
from enum import Enum
import plotly.express as px
import pandas as pd

class BrokerStatus(Enum):
    """
    Learning Note: Using Enums for better type safety and code maintainability
    This pattern prevents typos and makes broker status explicit
    """
    ACTIVE = "active"
    COMING_SOON = "coming_soon"
    DISABLED = "disabled"

# Broker Configuration - Easy to extend when adding new brokers
BROKER_CONFIG = {
    "coinbase": {
        "label": "Coinbase",
        "status": BrokerStatus.ACTIVE,
        "color": "#1652F0",  # Coinbase brand color
        "icon": "💰"
    },
    "schwab": {
        "label": "Charles Schwab", 
        "status": BrokerStatus.COMING_SOON,
        "color": "#00A0DF",  # Schwab brand color
        "icon": "🏦"
    }
}

def create_broker_selector(
    input_id: str = "selected_brokers",
    label: str = "Select Brokers",
    show_status: bool = True
) -> None:
    """
    Creates a broker multi-select component with status indicators
    
    Learning Points:
    - Functional component pattern for reusability
    - Configuration-driven UI generation
    - Status-aware option rendering
    """
    
    # Generate options with status indicators
    options = []
    labels = []
    
    for broker_id, config in BROKER_CONFIG.items():
        status_indicator = ""
        if show_status and config["status"] == BrokerStatus.COMING_SOON:
            status_indicator = " (Coming Soon)"
        elif show_status and config["status"] == BrokerStatus.DISABLED:
            status_indicator = " (Disabled)"
            
        option_label = f"{config['icon']} {config['label']}{status_indicator}"
        
        options.append(broker_id)
        labels.append(option_label)
    
    # Create the multi-select input
    ui.input_checkbox_group(
        input_id,
        label,
        choices=dict(zip(options, labels)),
        selected=["coinbase"],  # Default to Coinbase since it's active
        inline=True
    )

@reactive.calc
def get_active_brokers() -> List[str]:
    """
    Reactive calculation to get currently selected and available brokers
    
    Learning Note: Reactive calculations automatically update when dependencies change
    This is the foundation of reactive programming in Shiny
    """
    selected = input.selected_brokers() or []
    
    # Filter out disabled brokers and brokers not yet implemented
    active_brokers = []
    for broker in selected:
        if (broker in BROKER_CONFIG and 
            BROKER_CONFIG[broker]["status"] in [BrokerStatus.ACTIVE, BrokerStatus.COMING_SOON]):
            active_brokers.append(broker)
    
    return active_brokers

@reactive.calc  
def get_broker_display_info() -> Dict[str, Any]:
    """
    Get display information for selected brokers
    Useful for legends, colors, and UI feedback
    """
    active = get_active_brokers()
    
    return {
        broker: {
            "label": BROKER_CONFIG[broker]["label"],
            "color": BROKER_CONFIG[broker]["color"],
            "icon": BROKER_CONFIG[broker]["icon"],
            "available": BROKER_CONFIG[broker]["status"] == BrokerStatus.ACTIVE
        }
        for broker in active
    }

# Example Usage Component
def create_broker_aware_chart(data_fetcher_func, chart_title: str = "Portfolio Data"):
    """
    Example of how to use broker selection in charts
    
    Learning Points:
    - Separation of data fetching from presentation
    - Conditional rendering based on broker availability
    - User feedback for unavailable data
    """
    
    @render.ui
    def broker_status_display():
        """Show which brokers are selected and their status"""
        broker_info = get_broker_display_info()
        
        if not broker_info:
            return ui.div("No brokers selected", class_="alert alert-warning")
        
        status_items = []
        for broker_id, info in broker_info.items():
            status_class = "text-success" if info["available"] else "text-warning"
            status_text = "Active" if info["available"] else "Coming Soon"
            
            status_items.append(
                ui.span([
                    info["icon"], " ", info["label"], " - ",
                    ui.span(status_text, class_=status_class)
                ], class_="me-3")
            )
        
        return ui.div([
            ui.strong("Selected Brokers: "),
            *status_items
        ], class_="mb-3 p-2 bg-light rounded")
    
    @render.plot
    def filtered_chart():
        """Render chart with broker filtering applied"""
        active_brokers = get_active_brokers()
        broker_info = get_broker_display_info()
        
        if not active_brokers:
            # Return empty plot with message
            fig = px.scatter(title="No brokers selected")
            fig.add_annotation(
                text="Please select at least one broker",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # Fetch data only for available brokers
        available_brokers = [b for b in active_brokers 
                           if broker_info[b]["available"]]
        
        if not available_brokers:
            # Show "coming soon" message
            fig = px.scatter(title=chart_title)
            fig.add_annotation(
                text="Selected brokers are not yet available",
                xref="paper", yref="paper", 
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # Fetch and display actual data
        try:
            data = data_fetcher_func(available_brokers)
            
            # Create broker-aware visualization
            if isinstance(data, pd.DataFrame) and not data.empty:
                # Add broker colors to the plot
                color_map = {broker_info[b]["label"]: broker_info[b]["color"] 
                           for b in available_brokers}
                
                fig = px.bar(
                    data, 
                    title=chart_title,
                    color_discrete_map=color_map
                )
                return fig
            else:
                fig = px.scatter(title=chart_title)
                fig.add_annotation(
                    text="No data available for selected brokers",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return fig
                
        except Exception as e:
            # Error handling with user feedback
            fig = px.scatter(title="Error Loading Data")
            fig.add_annotation(
                text=f"Error: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
    
    return broker_status_display, filtered_chart

# Data Filtering Helper Functions

def filter_portfolio_data_by_broker(data: pd.DataFrame, selected_brokers: List[str]) -> pd.DataFrame:
    """
    Filter portfolio data by selected brokers
    
    Learning Note: Pandas filtering patterns for financial data
    Always handle edge cases (empty data, missing columns)
    """
    if data.empty or not selected_brokers:
        return pd.DataFrame()
    
    if 'broker' in data.columns:
        return data[data['broker'].isin(selected_brokers)]
    
    # Handle case where broker column might be named differently
    broker_columns = [col for col in data.columns if 'broker' in col.lower()]
    if broker_columns:
        return data[data[broker_columns[0]].isin(selected_brokers)]
    
    return data  # Return all data if no broker column found

def get_broker_aware_api_endpoints(selected_brokers: List[str]) -> Dict[str, str]:
    """
    Generate API endpoints based on selected brokers
    
    Learning Point: Dynamic API routing based on user selection
    """
    endpoints = {}
    
    for broker in selected_brokers:
        if broker == "coinbase" and BROKER_CONFIG[broker]["status"] == BrokerStatus.ACTIVE:
            endpoints["coinbase"] = "/unrealized_gains/by_broker/coinbase"
        elif broker == "schwab" and BROKER_CONFIG[broker]["status"] == BrokerStatus.ACTIVE:
            endpoints["schwab"] = "/unrealized_gains/by_broker/schwab"
    
    return endpoints

