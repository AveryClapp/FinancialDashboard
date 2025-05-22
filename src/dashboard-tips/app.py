import requests
from decimal import Decimal, InvalidOperation
import pandas as pd
import faicons as fa
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

# API base URL
API_BASE = "http://127.0.0.1:8001/"

# Server logic
def server(input, output: Outputs, session):
    

    def build_broker_params(selected_brokers):
        """
        Build query parameters for broker filtering.
        Returns empty string if both brokers selected (no filtering needed).
        """
        if not selected_brokers or len(selected_brokers) == 2:
            return ""
        
        params = "&".join([f"brokers={broker}" for broker in selected_brokers])
        return f"?{params}"

    def fetch_json(endpoint: str):
        """
        Helper to fetch JSON from `${API_BASE}/{endpoint}/{account_id}`.
        Returns None on error or missing account ID.
        """
        try:
            url = API_BASE + endpoint
            resp = requests.get(url)
            print(resp)
            return resp.json()
        except Exception as e:
            print(e)
            return None

    @render.ui
    def val():
        active_brokers = input.Exchanges()
        broker_count = len(active_brokers)
        if broker_count == 0:
            return ui.p("No exchanges selected, showing all results", style="color: orange;")
        elif broker_count == 2:
            return ui.p("Showing all exchanges", style="color: green;")
        else:
            broker_name = active_brokers[0].title()
            return ui.p(f"Filtering by: {broker_name}", style="color: blue;")

    @render.text
    @reactive.calc
    def unrealized_gain():
        selected_brokers = input.Exchanges()
        broker_params = build_broker_params(selected_brokers)
        data = fetch_json("unrealized_gains" + broker_params)
        raw = data.get("unrealized_gain") if data else None
        try:
            gain = Decimal(raw or 0)
        except (InvalidOperation, TypeError):
            gain = Decimal(0)
        return f"${gain:,.2f}"

    @render.text
    def realized_gain():
        selected_brokers = input.Exchanges()
        broker_params = build_broker_params(selected_brokers)
        data = fetch_json("realized_gains" + broker_params)
        raw = data.get("realized_gain") if data else None
        try:
            gain = Decimal(raw or 0)
        except (InvalidOperation, TypeError):
            gain = Decimal(0)
        return f"${gain:,.2f}"

    def make_table(endpoint: str):
        data = fetch_json(endpoint)
        return pd.DataFrame(data or [])

    @render.data_frame
    def unrealized_table():
        selected_brokers = input.Exchanges()
        broker_params = build_broker_params(selected_brokers)
        endpoint = "active_positions" + broker_params
        return make_table(endpoint)

    @render.data_frame
    def realized_table():
        selected_brokers = input.Exchanges()
        broker_params = build_broker_params(selected_brokers)
        endpoint = "closed_positions" + broker_params
        return make_table(endpoint)

    @render.data_frame
    def transactions_table():
        selected_brokers = input.Exchanges()
        broker_params = build_broker_params(selected_brokers)
        endpoint = "transactions" + broker_params
        return make_table(endpoint)



    @reactive.effect
    def perform_sync():
        try:
            resp = requests.post(f"{API_BASE}transactions/cb_update")
            resp.raise_for_status()
            ui.notification_show("✅ Sync succeeded")
        except Exception as e:
            ui.notification_show(f"❌ Sync failed: {e}", type="error")

# Define UI using Shiny Core
app_ui = ui.page_sidebar(
    # ---- Positional args (your UI components) go first ----
    ui.sidebar(
        ui.input_checkbox_group(
            "Exchanges",
            "Choose Exchange(s):",
            {
                "coinbase": ui.span("Coinbase"),
                "schwab": ui.span("Schwab"),
            },
            selected=["coinbase", "schwab"],
        ),
        ui.output_ui("val"),
    ),

    # Top row: value boxes
    ui.layout_columns(
        ui.value_box(
            "Unrealized Gain",
            ui.output_text("unrealized_gain"),
            showcase=fa.icon_svg("wallet"),
        ),
        ui.value_box(
            "Realized Gain",
            ui.output_text("realized_gain"),
            showcase=fa.icon_svg("dollar-sign"),
        ),
        fill=False,
    ),

    # Middle row: two cards side by side
    ui.layout_columns(
        ui.column(
            6,
            ui.card(
                ui.card_header("Active Positions"),
                ui.output_data_frame("unrealized_table"),
                full_screen=True,
            ),
        ),
        ui.column(
            6,
            ui.card(
                ui.card_header("Closed Positions"),
                ui.output_data_frame("realized_table"),
                full_screen=True,
            ),
        ),
    ),

    # Bottom row: all transactions
    ui.layout_columns(
        ui.column(
            12,
            ui.card(
                ui.card_header("All Transactions"),
                ui.output_data_frame("transactions_table"),
                full_screen=True,
            ),
        ),
    ),

    title="Portfolio Dashboard",
    fillable=True,
)




# Create and run the Shiny app
app = App(app_ui, server)
