# views/calories.py
# =============================================================================
# Calories view — food intake logging and calorie balance dashboard.
#
# Responsibilities:
#   - Log new food entries (name, kcal, meal type)
#   - Display today's food log as a scrollable list with delete actions
#   - Show 4 KPI metrics: consumed, burned, net balance, daily goal
#   - Render a CalorieDonutChart (consumed vs remaining vs over-budget)
#   - Allow the user to update their daily calorie goal inline
#
# The net calorie balance is always derived (consumed - burned) and
# never stored — consistent with BR-13 and the 3NF schema design.
# =============================================================================

import customtkinter as ctk

from components.widgets import (
    SectionCard, MetricCard, MetricRow, FoodRow, ScrollableList,
)
from utils.charts import CalorieDonutChart
from models.food_entry import (
    create_food_entry, get_todays_food,
    get_total_consumed_today, get_daily_summary, delete_food_entry,
)
from models.exercise import get_total_calories_burned_today
from models.user     import get_user, update_calorie_goal

_ACCENT     = "#1D9E75"
_WARN       = "#BA7517"
_DANGER     = "#A32D2D"
_TEXT_PRI   = "#EBEBEA"
_TEXT_SEC   = "#888880"
_CARD       = "#222220"
_BORDER     = "#2E2E2C"

_MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snack"]


class CaloriesView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, **kwargs):
        kwargs.setdefault("fg_color", "#1A1A1A")
        super().__init__(parent, **kwargs)
        self._user_id     = user_id
        self._toast       = toast
        self._calorie_goal = 2000
        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(
            hdr, text="Calorie Tracker",
            font=ctk.CTkFont("Arial", size=20, weight="bold"),
            text_color=_TEXT_PRI, anchor="w",
        ).pack(side="left")

        # Goal editor inline
        goal_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        goal_frame.pack(side="right")

        ctk.CTkLabel(
            goal_frame, text="Daily goal:",
            font=ctk.CTkFont("Arial", size=12),
            text_color=_TEXT_SEC,
        ).pack(side="left", padx=(0, 6))

        self._goal_entry = ctk.CTkEntry(
            goal_frame, width=70, height=30, corner_radius=6,
            fg_color="#282826", border_color=_BORDER,
            text_color=_TEXT_PRI,
        )
        self._goal_entry.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            goal_frame, text="kcal",
            font=ctk.CTkFont("Arial", size=12), text_color=_TEXT_SEC,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            goal_frame, text="Update",
            width=70, height=30, corner_radius=6,
            fg_color="#2A2A28", hover_color="#3A3A38",
            font=ctk.CTkFont("Arial", size=11), text_color=_TEXT_SEC,
            command=self._handle_update_goal,
        ).pack(side="left")

        # Metric row
        self._metrics = MetricRow(self, metrics=[
            {"label": "Consumed",  "value": "0",    "subtitle": "kcal today",         "value_color": _WARN},
            {"label": "Burned",    "value": "0",    "subtitle": "kcal from exercises", "value_color": _ACCENT},
            {"label": "Net",       "value": "0",    "subtitle": "consumed − burned",   "value_color": _TEXT_PRI},
            {"label": "Remaining", "value": "2000", "subtitle": "kcal to daily goal",  "value_color": _ACCENT},
        ])
        self._metrics.pack(fill="x", padx=24, pady=(14, 0))

        # Two-column layout
        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=24, pady=(14, 20))
        cols.columnconfigure(0, weight=2)
        cols.columnconfigure(1, weight=3)

        # Left: log form + donut
        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        form_card = SectionCard(left, title="Log a meal")
        form_card.pack(fill="x", pady=(0, 10))
        self._build_log_form(form_card.body)

        donut_card = SectionCard(left, title="Today's balance")
        donut_card.pack(fill="both", expand=True)

        self._donut = CalorieDonutChart(donut_card.body, consumed=0, goal=2000)
        self._donut.pack(fill="both", expand=True)

        self._balance_label = ctk.CTkLabel(
            donut_card.body, text="",
            font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC,
        )
        self._balance_label.pack(pady=(0, 8))

        # Right: food log
        log_card = SectionCard(cols, title="Today's food log")
        log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._food_list = ScrollableList(log_card.body, height=440)
        self._food_list.pack(fill="both", expand=True)

    def _build_log_form(self, parent) -> None:
        ctk.CTkLabel(
            parent, text="Food name",
            font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC, anchor="w",
        ).pack(fill="x")
        self._f_name = ctk.CTkEntry(
            parent, height=32, corner_radius=6,
            placeholder_text="e.g. Scrambled eggs",
            fg_color="#282826", border_color=_BORDER, text_color=_TEXT_PRI,
        )
        self._f_name.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))

        cal_f = ctk.CTkFrame(row, fg_color="transparent")
        cal_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(
            cal_f, text="Calories (kcal)",
            font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC, anchor="w",
        ).pack(fill="x")
        self._f_cal = ctk.CTkEntry(
            cal_f, height=32, corner_radius=6,
            placeholder_text="200",
            fg_color="#282826", border_color=_BORDER, text_color=_TEXT_PRI,
        )
        self._f_cal.pack(fill="x")

        meal_f = ctk.CTkFrame(row, fg_color="transparent")
        meal_f.pack(side="left")
        ctk.CTkLabel(
            meal_f, text="Meal type",
            font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC, anchor="w",
        ).pack(fill="x")
        self._f_meal = ctk.CTkOptionMenu(
            meal_f, values=_MEAL_TYPES,
            width=110, height=32, corner_radius=6,
            fg_color="#282826", button_color="#3A3A38",
            button_hover_color="#4A4A48", text_color=_TEXT_PRI,
            dropdown_fg_color=_CARD, dropdown_text_color=_TEXT_PRI,
            dropdown_hover_color="#2A2A28",
        )
        self._f_meal.pack()

        ctk.CTkButton(
            parent, text="+ Log entry",
            height=34, corner_radius=7,
            fg_color=_ACCENT, hover_color="#158A62",
            font=ctk.CTkFont("Arial", size=13), text_color="#FFFFFF",
            command=self._handle_add,
        ).pack(fill="x")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def on_show(self) -> None:
        user = get_user(self._user_id)
        if user:
            self._calorie_goal = user["calorie_goal"]
            self._goal_entry.delete(0, "end")
            self._goal_entry.insert(0, str(self._calorie_goal))
        self._refresh()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        consumed = get_total_consumed_today(self._user_id)
        burned   = get_total_calories_burned_today(self._user_id)
        net      = consumed - burned
        remaining = max(0, self._calorie_goal - consumed)
        over      = max(0, consumed - self._calorie_goal)

        # Metrics
        self._metrics.cards[0].update(str(consumed))
        self._metrics.cards[1].update(str(burned))
        net_color = _ACCENT if net <= 0 else _WARN
        self._metrics.cards[2].update(str(net), value_color=net_color)
        rem_color = _ACCENT if over == 0 else _DANGER
        self._metrics.cards[3].update(
            str(remaining if over == 0 else f"-{over}"),
            value_color=rem_color,
        )

        # Donut
        self._donut.refresh(consumed, self._calorie_goal)
        if over > 0:
            self._balance_label.configure(
                text=f"{over} kcal over daily goal",
                text_color=_DANGER,
            )
        else:
            self._balance_label.configure(
                text=f"{consumed} of {self._calorie_goal} kcal consumed",
                text_color=_TEXT_SEC,
            )

        # Food log list
        foods = get_todays_food(self._user_id)
        self._food_list.clear()

        if not foods:
            ctk.CTkLabel(
                self._food_list,
                text="No food logged today.\nUse the form to add your first meal.",
                font=ctk.CTkFont("Arial", size=12),
                text_color=_TEXT_SEC,
            ).pack(pady=40)
            return

        for food in foods:
            row = FoodRow(
                self._food_list, entry=food,
                on_delete=self._handle_delete,
            )
            row.pack(fill="x", pady=2)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _handle_add(self) -> None:
        name = self._f_name.get().strip()
        cal  = self._f_cal.get().strip()
        meal = self._f_meal.get()

        if not name:
            self._toast.show("Please enter a food name.", kind="warning")
            return
        try:
            cal = int(cal)
            if cal < 0:
                raise ValueError
        except ValueError:
            self._toast.show("Calories must be a non-negative integer.", kind="warning")
            return

        create_food_entry(self._user_id, name, cal, meal)
        self._f_name.delete(0, "end")
        self._f_cal.delete(0, "end")
        self._toast.show(f"{name} logged ({cal} kcal).", kind="success")
        self._refresh()

    def _handle_delete(self, entry_id: int) -> None:
        ok = delete_food_entry(entry_id, self._user_id)
        if ok:
            self._toast.show("Food entry removed.", kind="info")
            self._refresh()
        else:
            self._toast.show("Could not remove entry.", kind="error")

    def _handle_update_goal(self) -> None:
        try:
            goal = int(self._goal_entry.get())
            if goal <= 0:
                raise ValueError
        except ValueError:
            self._toast.show("Goal must be a positive integer.", kind="warning")
            return
        ok = update_calorie_goal(self._user_id, goal)
        if ok:
            self._calorie_goal = goal
            self._toast.show(f"Daily goal updated to {goal} kcal.", kind="success")
            self._refresh()
        else:
            self._toast.show("Could not update goal.", kind="error")
