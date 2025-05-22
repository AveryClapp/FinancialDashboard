# crypto_dashboard.py - Complete Dashboard with Broker Multi-Select

import faicons as fa
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from decimal import Decimal
from typing import List, Dict, Optional, Any

from shiny import reactive, render
from shiny.express import input, ui
from shinywidgets import render_plotly

# Import our broker selector component
from broker_selector import (
    create_broker_selector, 
    get_active_brokers, 
    get_broker_display_info,
    get_broker_aware_api_endpoints,
    BROKER_CONFIG
)

API_BASE_URL = "http://127.0.0.1:8001"

ui.page_opts(title="Crypto Portfolio Dashboard", fillable=True)

with ui.sidebar(open="desktop"):
    ui.h4("Portfolio Filters")

    create_broker_selector(
        input_id="selected_brokers",
        label="Brokers",
        show_status=True
    )
    
    ui.hr()
    
    ui.input_date_range(
        "date_range",
        "Date Range",
        start="2024-01-01",
        end="2024-12-31"
    )
    
    ui.input_action_button(
        "refresh_data", 
        "Refresh Data",
        class_="btn-primary w-100 mt-3"
    )

ICONS = {
    "chart-line": fa.icon_svg("chart-line"),
    "coins": fa.icon_svg("coins"), 
    "wallet": fa.icon_svg("wallet"),
    "trending-up": fa.icon_svg("trending-up"),
    "refresh": fa.icon_svg("refresh")
}

with ui.layout_columns(fill=False):
    
    with ui.value_box(showcase=ICONS["wallet"]):
        "Total Portfolio Value"
        
        @render.express
        def total_portfolio_value():
            brokers = get_active_brokers()
            data = fetch_unrealized_gains_data(brokers)
            
            if data:
                total = sum(item.get("market_value", 0) for item in data)
                f"${total:,.2f}"
            else:
                "Loading..."
    
    with ui.value_box(showcase=ICONS["trending-up"]):
        "Unrealized Gains"
        
        @render.express  
        def total_unrealized_gains():
            brokers = get_active_brokers()
            data = fetch_unrealized_gains_data(brokers)
            
            if data:
                total_gains = sum(item.get("unrealized_gain", 0) for item in data)
                color = "text-success" if total_gains >= 0 else "text-danger"
                ui.span(f"${total_gains:,.2f}", class_=color)
            else:
                "Loading..."
    
    with ui.value_box(showcase=ICONS["coins"]):
        "Active Brokers"
        
        @render.express
        def active_broker_count():
            brokers = get_active_brokers()
            broker_info = get_broker_display_info()
            
            available_count = sum(1 for b in brokers if broker_info.get(b, {}).get("available", False))
            total_selected = len(brokers)
            
            f"{available_count}/{total_selected}"

with ui.layout_columns(col_widths=[12, 6, 6]):
    
    with ui.card(full_screen=False):
        ui.card_header("Broker Status")
        
        @render.ui
        def broker_status_display():
            broker_info = get_broker_display_info()
            
            if not broker_info:
                return ui.div(
                    [ICONS["refresh"], " No brokers selected"],
                    class_="alert alert-warning text-center"
                )
            
            status_cards = []
            for broker_id, info in broker_info.items():
                
                card_class = "border-success" if info["available"] else "border-warning"
                status_badge_class = "bg-success" if info["available"] else "bg-warning"
                status_text = "Active" if info["available"] else "Coming Soon"
                
                card = ui.div([
                    ui.div([
                        ui.span(info["icon"], class_="fs-4"),
                        ui.div([
                            ui.strong(info["label"]),
                            ui.br(),
                            ui.span(status_text, class_=f"badge {status_badge_class}")
                        ], class_="ms-2")
                    ], class_="d-flex align-items-center p-2")
                ], class_=f"border rounded mb-2 {card_class}")
                
                status_cards.append(card)
            
            return ui.div(status_cards)
    
    with ui.card(full_screen=True):
        ui.card_header("Portfolio by Broker")
        
        @render_plotly
        def portfolio_by_broker_chart():
            brokers = get_active_brokers()
            broker_info = get_broker_display_info()
            
            if not brokers:
                fig = go.Figure()
                fig.add_annotation(
                    text="Select brokers to view portfolio breakdown",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16)
                )
                fig.update_layout(title="Portfolio Breakdown")
                return fig
            
            chart_data = []
            available_brokers = [b for b in brokers if broker_info.get(b, {}).get("available", False)]
            
            if not available_brokers:
                fig = go.Figure()
                fig.add_annotation(
                    text="Selected brokers are not yet available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="orange")
                )
                fig.update_layout(title="Portfolio Breakdown - Coming Soon")
                return fig
            
            for broker in available_brokers:
                try:
                    response = requests.get(f"{API_BASE_URL}/unrealized_gains/by_broker/{broker}")
                    if response.status_code == 200:
                        data = response.json()
                        chart_data.append({
                            "Broker": broker_info[broker]["label"],
                            "Market Value": data.get("market_value", 0),
                            "Unrealized Gain": data.get("unrealized_gain", 0),
                            "Total Cost": data.get("total_cost", 0)
                        })
                except Exception as e:
                    print(f"Error fetching data for {broker}: {e}")
            
            if not chart_data:
                fig = go.Figure()
                fig.add_annotation(
                    text="No data available",
                    xref="paper", yref="paper", 
                    x=0.5, y=0.5, showarrow=False
                )
                fig.update_layout(title="Portfolio Breakdown")
                return fig
            
            df = pd.DataFrame(chart_data)
            
            color_map = {broker_info[b]["label"]: broker_info[b]["color"] for b in available_brokers}
            
            fig = px.bar(
                df,
                x="Broker", 
                y="Market Value",
                color="Broker",
                color_discrete_map=color_map,
                title="Portfolio Value by Broker"
            )
            
            fig.update_layout(showlegend=False)
            return fig
    
    # Gains/Losses breakdown
    with ui.card(full_screen=True):
        ui.card_header("Gains/Losses by Broker")
        
        @render_plotly
        def gains_losses_chart():
            brokers = get_active_brokers()
            broker_info = get_broker_display_info()
            
            available_brokers = [b for b in brokers if broker_info.get(b, {}).get("available", False)]
            
            if not available_brokers:
                fig = go.Figure()
                fig.add_annotation(
                    text="No active brokers selected",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return fig
            
            chart_data = []
            for broker in available_brokers:
                try:
                    response = requests.get(f"{API_BASE_URL}/unrealized_gains/by_broker/{broker}")
                    if response.status_code == 200:
                        data = response.json()
                        unrealized_gain = data.get("unrealized_gain", 0)
                        
                        chart_data.append({
                            "Broker": broker_info[broker]["label"],
                            "Unrealized Gain": unrealized_gain,
                            "Type": "Gain" if unrealized_gain >= 0 else "Loss"
                        })
                except Exception as e:
                    print(f"Error fetching gains data for {broker}: {e}")
            
            if not chart_data:
                return go.Figure()
            
            df = pd.DataFrame(chart_data)
            
            # Color gains green and losses red
            colors = ["green" if x >= 0 else "red" for x in df["Unrealized Gain"]]
            
            fig = px.bar(
                df,
                x="Broker",
                y="Unrealized Gain", 
                color=colors,
                title="Unrealized Gains/Losses by Broker"
            )
            
            fig.update_layout(showlegend=False)
            return fig

# Data fetching functions
@reactive.calc
def fetch_unrealized_gains_data(brokers: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch unrealized gains data for selected brokers
    
    Learning Note: Reactive data fetching with error handling
    This pattern ensures data updates when broker selection changes
    """
    if not brokers:
        return []
    
    broker_info = get_broker_display_info()
    available_brokers = [b for b in brokers if broker_info.get(b, {}).get("available", False)]
    
    results = []
    for broker in available_brokers:
        try:
            response = requests.get(
                f"{API_BASE_URL}/unrealized_gains/by_broker/{broker}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                data["broker"] = broker
                results.append(data)
        except requests.RequestException as e:
            print(f"API Error for {broker}: {e}")
            # Could add user notification here
        except Exception as e:
            print(f"Unexpected error for {broker}: {e}")
    
    return results

# Reactive effects for data refresh
@reactive.effect
@reactive.event(input.refresh_data)
def refresh_portfolio_data():
    """
    Manual data refresh trigger
    
    Learning Note: Reactive events for user-triggered actions
    """
    # Force recalculation of dependent reactive elements
    brokers = get_active_brokers()
    print(f"Refreshing data for brokers: {brokers}")
    
    # You could add loading states, notifications, etc. here

# Auto-refresh functionality (optional)
@reactive.effect
def auto_refresh():
    """
    Optional: Auto-refresh data every 5 minutes
    
    Learning Note: Background data updates in reactive systems
    """
    # This would require implementing a timer in Shiny
    # For now, manual refresh via button
    pass

# Error handling and user feedback
@render.ui
def error_display():
    """Display any errors or warnings to users"""
    brokers = get_active_brokers()
    broker_info = get_broker_display_info()
    
    warnings = []
    
    # Check for selected but unavailable brokers
    unavailable = [b for b in brokers if not broker_info.get(b, {}).get("available", False)]
    if unavailable:
        broker_names = [BROKER_CONFIG[b]["label"] for b in unavailable]
        warnings.append(
            f"Selected brokers not yet available: {', '.join(broker_names)}"
        )
    
    if warnings:
        return ui.div([
            ui.div([
                fa.icon_svg("exclamation-triangle"), " ",
                warning
            ], class_="alert alert-warning")
            for warning in warnings
        ])
    
    return ui.div()  # Empty div if no warnings
