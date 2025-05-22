import requests
from decimal import Decimal, InvalidOperation
import pandas as pd
import faicons as fa
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

# API base URL
API_BASE = "http://127.0.0.1:8001/"

# Server logic
def server(input, output: Outputs, session):

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

    @render.text
    def unrealized_gain():
        data = fetch_json("unrealized_gains")
        raw = data.get("unrealized_gain") if data else None
        try:
            gain = Decimal(raw or 0)
        except (InvalidOperation, TypeError):
            gain = Decimal(0)
        return f"${gain:,.2f}"

    @render.text
    def realized_gain():
        data = fetch_json("realized_gains")
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
        return make_table("active_positions")

    @render.data_frame
    def realized_table():
        return make_table("closed_positions")

    @render.data_frame
    def transactions_table():
        return make_table("transactions/15")

    @reactive.event(input.sync)
    def _perform_sync():
        if not acct:
            session.show_notification("⚠️ Enter an account ID before syncing.", type="warning")
            return
        try:
            resp = requests.post(
                f"{API_BASE}/transactions/update", json={"account_id": acct}
            )
            resp.raise_for_status()
            session.show_notification("✅ Sync succeeded", type="message")
        except Exception as e:
            session.show_notification(f"❌ Sync failed: {e}", type="error")

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
