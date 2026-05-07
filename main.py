# main.py
# =============================================================================
# FitTrack — Application Entry Point
# Python 3.14.4 | CustomTkinter | MySQL 9.7.0 LTS
#
# Responsibilities:
#   - Initialise the CustomTkinter root window
#   - Connect to the database (fail gracefully with a readable error dialog)
#   - Load the active user from .env (APP_USER_ID)
#   - Instantiate all views and the sidebar
#   - Handle navigation: show/hide view frames on sidebar clicks
#   - Start and stop the reminder scheduler lifecycle
#   - Clean up resources on window close
#
# Architecture note:
#   main.py is the only file that imports from ALL layers simultaneously.
#   Every other file only imports from layers below it:
#     views      → models, components, utils
#     components → (nothing from project)
#     models     → config
#     utils      → (nothing from project)
#   This one-way dependency graph prevents circular imports.
# =============================================================================

import os
import sys
import tkinter as tk

import customtkinter as ctk
from dotenv import load_dotenv

load_dotenv()  # must run before any config.db import

from config.db import db, DBError
from models.user import get_user

from components.sidebar  import Sidebar
from components.widgets  import ToastManager

from views.dashboard import DashboardView
from views.exercises import ExercisesView
from views.calories  import CaloriesView
from views.weekly    import WeeklyView
from views.progress  import ProgressView


# =============================================================================
# Theme + appearance
# =============================================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")   # base theme; overridden by our colours

_WIN_TITLE  = "FitTrack — Daily Home Exercise Routine System"
_WIN_WIDTH  = 1100
_WIN_HEIGHT = 700
_WIN_MIN_W  = 900
_WIN_MIN_H  = 600


# =============================================================================
# App class
# =============================================================================

class App(ctk.CTk):

    def __init__(self, user_id: int):
        super().__init__()
        self._user_id    = user_id
        self._active_key = "dashboard"

        self._configure_window()
        self._build_ui()
        self._show_page("dashboard", first_load=True)

        # Handle window close cleanly
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _configure_window(self) -> None:
        self.title(_WIN_TITLE)
        self.geometry(f"{_WIN_WIDTH}x{_WIN_HEIGHT}")
        self.minsize(_WIN_MIN_W, _WIN_MIN_H)
        self.configure(fg_color="#1A1A1A")

        # Centre on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - _WIN_WIDTH)  // 2
        y  = (sh - _WIN_HEIGHT) // 2
        self.geometry(f"{_WIN_WIDTH}x{_WIN_HEIGHT}+{x}+{y}")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Fetch user for sidebar display
        user = get_user(self._user_id)
        username     = user["username"]     if user else "User"
        calorie_goal = user["calorie_goal"] if user else 2000

        # ── Root layout: sidebar (left) + content area (right) ────────
        self._sidebar = Sidebar(
            self,
            on_navigate=self._show_page,
            username=username,
            calorie_goal=calorie_goal,
        )
        self._sidebar.pack(side="left", fill="y")

        # Thin separator line
        ctk.CTkFrame(self, width=1, fg_color="#2C2C2A").pack(side="left", fill="y")

        # Content area — all views are stacked here, only one visible at a time
        self._content = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        # ── Toast manager (overlay, not in layout flow) ────────────────
        self._toast = ToastManager(self, duration_ms=2800)

        # ── Instantiate all views ──────────────────────────────────────
        # Views are created once and re-used; on_show() refreshes data.
        self._views: dict[str, ctk.CTkFrame] = {
            "dashboard": DashboardView(
                self._content,
                user_id=self._user_id,
                toast=self._toast,
            ),
            "exercises": ExercisesView(
                self._content,
                user_id=self._user_id,
                toast=self._toast,
            ),
            "calories": CaloriesView(
                self._content,
                user_id=self._user_id,
                toast=self._toast,
            ),
            "weekly": WeeklyView(
                self._content,
                user_id=self._user_id,
                toast=self._toast,
                on_navigate=self._show_page,
            ),
            "progress": ProgressView(
                self._content,
                user_id=self._user_id,
                toast=self._toast,
            ),
        }

        # Place all views in the same grid cell — only one is visible
        for view in self._views.values():
            view.place(relx=0, rely=0, relwidth=1, relheight=1)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_page(self, key: str, first_load: bool = False) -> None:
        """
        Raise the requested view to the top and call its on_show() method.
        The sidebar is updated to reflect the active page.
        """
        if key not in self._views:
            return

        self._active_key = key
        view = self._views[key]
        view.lift()   # bring to front of the stacking order

        # Call on_show() to refresh data
        if key == "dashboard":
            view.on_show(tk_root=self)
            if first_load:
                view.start_reminder_scheduler(tk_root=self)
        else:
            view.on_show()

        # Sync sidebar highlight
        self._sidebar.set_active(key)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        """Gracefully stop background threads and DB connection on exit."""
        # Stop the reminder scheduler thread
        dashboard = self._views.get("dashboard")
        if dashboard:
            dashboard.stop_reminder_scheduler()

        # Close DB connection
        db.disconnect()

        self.destroy()


# =============================================================================
# DB connection check — shown before App starts
# =============================================================================

def _check_db_or_exit() -> None:
    """
    Attempt a DB connection before launching the UI.
    If it fails, show a readable error dialog and exit.
    This prevents a confusing crash inside the running app.
    """
    try:
        db.connect()
        if not db.ping():
            raise DBError("Ping failed after connection.")
    except DBError as e:
        # Show a minimal tkinter error window (CTk not initialised yet)
        root = tk.Tk()
        root.withdraw()
        import tkinter.messagebox as mb
        mb.showerror(
            "FitTrack — Database Error",
            f"Could not connect to MySQL.\n\n{e}\n\n"
            "Steps to fix:\n"
            "1. Make sure MySQL 9.7 is running.\n"
            "2. Check your .env file credentials.\n"
            "3. Run: mysql -u root -p < database/schema.sql"
        )
        root.destroy()
        sys.exit(1)


# =============================================================================
# Entry point
# =============================================================================

def main() -> None:
    _check_db_or_exit()

    user_id = int(os.getenv("APP_USER_ID", "1"))

    # Verify user exists in DB
    user = get_user(user_id)
    if user is None:
        import tkinter.messagebox as mb
        root = tk.Tk()
        root.withdraw()
        mb.showerror(
            "FitTrack — User Not Found",
            f"No user found with APP_USER_ID={user_id}.\n\n"
            "Make sure you ran the seed data in schema.sql:\n"
            "  mysql -u root -p fittrack_db < database/schema.sql"
        )
        root.destroy()
        sys.exit(1)

    app = App(user_id=user_id)
    app.mainloop()


if __name__ == "__main__":
    main()
