# components/sidebar.py
# =============================================================================
# Sidebar navigation component for FitTrack.
#
# Design decisions:
#   - Subclasses CTkFrame so it can be placed like any other widget.
#   - Holds a dict of nav buttons; only one can be "active" at a time.
#   - Communicates with the main window via a single `on_navigate`
#     callback — the sidebar has zero knowledge of what the views do.
#     This is the Observer pattern: sidebar emits, App handles.
#   - Active state is purely visual (color swap). No state is stored
#     in the sidebar beyond which button is currently highlighted.
#   - The username and calorie goal are passed in at construction so
#     the sidebar can display user context without querying the DB itself.
# =============================================================================

import customtkinter as ctk


# Nav item definitions: (label, page_key, unicode_icon)
# Unicode icons are used instead of image files to keep the project
# self-contained — no asset folder required.
_NAV_ITEMS = [
    ("Dashboard",     "dashboard",  "⊞"),
    ("Exercises",     "exercises",  "◈"),
    ("Calories",      "calories",   "⬡"),
    ("Weekly Plan",   "weekly",     "▦"),
    ("Progress",      "progress",   "↗"),
]

# Color tokens — kept here so a theme change only touches one file
_CLR_BG          = "#1A1A1A"
_CLR_BG_HOVER    = "#2A2A2A"
_CLR_ACTIVE_BG   = "#1D3D30"
_CLR_ACTIVE_FG   = "#1D9E75"
_CLR_INACTIVE_FG = "#888880"
_CLR_LOGO_ACCENT = "#1D9E75"
_CLR_LOGO_TEXT   = "#FFFFFF"
_CLR_DIVIDER     = "#2C2C2A"
_CLR_META_TEXT   = "#555550"
_CLR_USER_TEXT   = "#CCCCCA"


class Sidebar(ctk.CTkFrame):
    """
    Vertical navigation sidebar.

    Args:
        parent:       Parent widget (the App root window).
        on_navigate:  Callable[[str], None] — called with the page key
                      when a nav button is clicked.
        username:     Display name shown at the bottom of the sidebar.
        calorie_goal: User's daily calorie target for context display.
    """

    def __init__(
        self,
        parent,
        on_navigate,
        username: str = "User",
        calorie_goal: int = 2000,
    ):
        super().__init__(
            parent,
            width=210,
            corner_radius=0,
            fg_color=_CLR_BG,
        )
        self._on_navigate   = on_navigate
        self._active_key    = "dashboard"
        self._buttons: dict[str, ctk.CTkButton] = {}

        self._build(username, calorie_goal)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, username: str, calorie_goal: int) -> None:
        self.pack_propagate(False)  # keep fixed width=210

        # ── Logo ──────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=18, pady=(22, 0))

        ctk.CTkLabel(
            logo_frame,
            text="Fit",
            font=ctk.CTkFont("Arial", size=22, weight="bold"),
            text_color=_CLR_LOGO_ACCENT,
        ).pack(side="left")

        ctk.CTkLabel(
            logo_frame,
            text="Track",
            font=ctk.CTkFont("Arial", size=22, weight="bold"),
            text_color=_CLR_LOGO_TEXT,
        ).pack(side="left")

        # ── Divider ───────────────────────────────────────────────────
        ctk.CTkFrame(
            self, height=1, fg_color=_CLR_DIVIDER
        ).pack(fill="x", padx=0, pady=(14, 10))

        # ── Nav buttons ───────────────────────────────────────────────
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=8)

        for label, key, icon in _NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}   {label}",
                anchor="w",
                height=40,
                corner_radius=8,
                border_width=0,
                font=ctk.CTkFont("Arial", size=13),
                fg_color="transparent",
                text_color=_CLR_INACTIVE_FG,
                hover_color=_CLR_BG_HOVER,
                command=lambda k=key: self._handle_click(k),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[key] = btn

        # Activate default
        self._set_active("dashboard")

        # ── Spacer ────────────────────────────────────────────────────
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        # ── Divider ───────────────────────────────────────────────────
        ctk.CTkFrame(
            self, height=1, fg_color=_CLR_DIVIDER
        ).pack(fill="x", padx=0, pady=(0, 10))

        # ── User info strip ───────────────────────────────────────────
        user_frame = ctk.CTkFrame(self, fg_color="transparent")
        user_frame.pack(fill="x", padx=18, pady=(0, 18))

        # Avatar circle (letter avatar)
        avatar_frame = ctk.CTkFrame(
            user_frame,
            width=34, height=34,
            corner_radius=17,
            fg_color=_CLR_ACTIVE_BG,
        )
        avatar_frame.pack(side="left", padx=(0, 10))
        avatar_frame.pack_propagate(False)

        ctk.CTkLabel(
            avatar_frame,
            text=username[0].upper(),
            font=ctk.CTkFont("Arial", size=14, weight="bold"),
            text_color=_CLR_ACTIVE_FG,
        ).pack(expand=True)

        # Username + goal
        info_frame = ctk.CTkFrame(user_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info_frame,
            text=username,
            font=ctk.CTkFont("Arial", size=12, weight="bold"),
            text_color=_CLR_USER_TEXT,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            info_frame,
            text=f"Goal: {calorie_goal:,} kcal/day",
            font=ctk.CTkFont("Arial", size=11),
            text_color=_CLR_META_TEXT,
            anchor="w",
        ).pack(fill="x")

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _handle_click(self, key: str) -> None:
        """Called when a nav button is clicked. Updates visual state then delegates."""
        self._set_active(key)
        self._on_navigate(key)

    def _set_active(self, key: str) -> None:
        """Swap colours on the old and new active buttons."""
        # Deactivate previous
        if self._active_key in self._buttons:
            prev = self._buttons[self._active_key]
            prev.configure(
                fg_color="transparent",
                text_color=_CLR_INACTIVE_FG,
            )

        # Activate new
        self._active_key = key
        if key in self._buttons:
            self._buttons[key].configure(
                fg_color=_CLR_ACTIVE_BG,
                text_color=_CLR_ACTIVE_FG,
            )

    def set_active(self, key: str) -> None:
        """
        Public method — allows the App to programmatically highlight
        a nav item (e.g., on startup or after a redirect).
        """
        self._set_active(key)
