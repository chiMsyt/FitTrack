# views/calories.py
import customtkinter as ctk

from components.widgets import SectionCard, MetricRow, FoodRow, ScrollableList
from utils.charts       import CalorieDonutChart
from models.food_entry  import (create_food_entry, get_todays_food,
                                 get_total_consumed_today, delete_food_entry)
from models.exercise    import get_total_calories_burned_today
from models.user        import get_user, update_calorie_goal, update_calorie_mode

_ACCENT   = "#1D9E75"
_WARN     = "#BA7517"
_DANGER   = "#A32D2D"
_TEXT_PRI = "#EBEBEA"
_TEXT_SEC = "#888880"
_CARD     = "#222220"
_BORDER   = "#2E2E2C"
_MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snack"]


class CaloriesView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, **kwargs):
        kwargs.setdefault("fg_color", "#1A1A1A")
        super().__init__(parent, **kwargs)
        self._user_id      = user_id
        self._toast        = toast
        self._calorie_goal = 2000
        self._mode         = "deficit"
        self._surplus_goal = None
        self._build_layout()

    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        # Header + mode toggle
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Calorie Tracker",
                     font=ctk.CTkFont("Arial", size=20, weight="bold"),
                     text_color=_TEXT_PRI, anchor="w").pack(side="left")

        # Mode toggle
        toggle_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        toggle_frame.pack(side="right")

        ctk.CTkLabel(toggle_frame, text="Mode:",
                     font=ctk.CTkFont("Arial", size=12), text_color=_TEXT_SEC).pack(side="left", padx=(0,6))
        self._mode_var = ctk.StringVar(value="deficit")
        ctk.CTkSegmentedButton(
            toggle_frame, values=["deficit", "surplus"],
            variable=self._mode_var,
            width=180, height=30,
            fg_color="#2A2A28", selected_color=_ACCENT, unselected_color="#2A2A28",
            text_color=_TEXT_PRI,
            command=self._handle_mode_change,
        ).pack(side="left", padx=(0, 10))

        # Goal editor
        ctk.CTkLabel(toggle_frame, text="Goal:", font=ctk.CTkFont("Arial", size=12),
                     text_color=_TEXT_SEC).pack(side="left", padx=(0, 4))
        self._goal_entry = ctk.CTkEntry(
            toggle_frame, width=70, height=30, corner_radius=6,
            fg_color="#282826", border_color=_BORDER, text_color=_TEXT_PRI)
        self._goal_entry.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(toggle_frame, text="kcal", font=ctk.CTkFont("Arial", size=12),
                     text_color=_TEXT_SEC).pack(side="left", padx=(0, 8))
        ctk.CTkButton(toggle_frame, text="Update", width=70, height=30, corner_radius=6,
                      fg_color="#2A2A28", hover_color="#3A3A38",
                      font=ctk.CTkFont("Arial", size=11), text_color=_TEXT_SEC,
                      command=self._handle_update_goal).pack(side="left")

        # Surplus goal (shown only in surplus mode)
        self._surplus_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self._surplus_frame, text="Surplus target:",
                     font=ctk.CTkFont("Arial", size=12), text_color=_TEXT_SEC).pack(side="left", padx=(0,6))
        self._surplus_entry = ctk.CTkEntry(
            self._surplus_frame, width=80, height=30, corner_radius=6,
            placeholder_text="e.g. 500", fg_color="#282826",
            border_color=_BORDER, text_color=_TEXT_PRI)
        self._surplus_entry.pack(side="left", padx=(0,4))
        ctk.CTkLabel(self._surplus_frame, text="kcal above maintenance",
                     font=ctk.CTkFont("Arial", size=12), text_color=_TEXT_SEC).pack(side="left", padx=(0,8))
        ctk.CTkButton(self._surplus_frame, text="Set", width=50, height=30, corner_radius=6,
                      fg_color="#2A2A28", hover_color="#3A3A38",
                      font=ctk.CTkFont("Arial", size=11), text_color=_TEXT_SEC,
                      command=self._handle_update_surplus).pack(side="left")

        # KPI metrics
        self._metrics = MetricRow(self, metrics=[
            {"label": "Consumed",  "value": "0",    "subtitle": "kcal today",          "value_color": _WARN},
            {"label": "Burned",    "value": "0",    "subtitle": "from exercises",       "value_color": _ACCENT},
            {"label": "Net",       "value": "0",    "subtitle": "consumed − burned",    "value_color": _TEXT_PRI},
            {"label": "Goal",      "value": "2000", "subtitle": "daily target",         "value_color": _TEXT_PRI},
        ])
        self._metrics.pack(fill="x", padx=24, pady=(14, 0))

        # Two-column: form+donut | food log
        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=24, pady=(12, 20))
        cols.columnconfigure(0, weight=2)
        cols.columnconfigure(1, weight=3)

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
            donut_card.body, text="", font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC)
        self._balance_label.pack(pady=(0, 8))

        log_card = SectionCard(cols, title="Today's food log")
        log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._food_list = ScrollableList(log_card.body, height=440)
        self._food_list.pack(fill="both", expand=True)

    def _build_log_form(self, parent) -> None:
        ctk.CTkLabel(parent, text="Food name", font=ctk.CTkFont("Arial", size=11),
                     text_color=_TEXT_SEC, anchor="w").pack(fill="x")
        self._f_name = ctk.CTkEntry(parent, height=32, corner_radius=6,
                                     placeholder_text="e.g. Scrambled eggs",
                                     fg_color="#282826", border_color=_BORDER,
                                     text_color=_TEXT_PRI)
        self._f_name.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))
        cal_f = ctk.CTkFrame(row, fg_color="transparent")
        cal_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(cal_f, text="Calories (kcal)", font=ctk.CTkFont("Arial", size=11),
                     text_color=_TEXT_SEC, anchor="w").pack(fill="x")
        self._f_cal = ctk.CTkEntry(cal_f, height=32, corner_radius=6,
                                    placeholder_text="200", fg_color="#282826",
                                    border_color=_BORDER, text_color=_TEXT_PRI)
        self._f_cal.pack(fill="x")

        meal_f = ctk.CTkFrame(row, fg_color="transparent")
        meal_f.pack(side="left")
        ctk.CTkLabel(meal_f, text="Meal type", font=ctk.CTkFont("Arial", size=11),
                     text_color=_TEXT_SEC, anchor="w").pack(fill="x")
        self._f_meal = ctk.CTkOptionMenu(
            meal_f, values=_MEAL_TYPES, width=110, height=32, corner_radius=6,
            fg_color="#282826", button_color="#3A3A38", button_hover_color="#4A4A48",
            text_color=_TEXT_PRI, dropdown_fg_color=_CARD, dropdown_text_color=_TEXT_PRI,
            dropdown_hover_color="#2A2A28")
        self._f_meal.pack()

        ctk.CTkButton(parent, text="+ Log entry", height=34, corner_radius=7,
                      fg_color=_ACCENT, hover_color="#158A62",
                      font=ctk.CTkFont("Arial", size=13), text_color="#FFFFFF",
                      command=self._handle_add).pack(fill="x")

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        user = get_user(self._user_id)
        if user:
            self._calorie_goal = user["calorie_goal"]
            self._mode         = user.get("calorie_mode", "deficit")
            self._surplus_goal = user.get("surplus_goal")
            self._goal_entry.delete(0, "end")
            self._goal_entry.insert(0, str(self._calorie_goal))
            self._mode_var.set(self._mode)
            self._update_surplus_visibility()
        self._refresh()

    def _update_surplus_visibility(self) -> None:
        if self._mode == "surplus":
            self._surplus_frame.pack(fill="x", padx=24, pady=(4, 0))
            if self._surplus_goal:
                self._surplus_entry.delete(0, "end")
                self._surplus_entry.insert(0, str(self._surplus_goal))
        else:
            self._surplus_frame.pack_forget()

    def _refresh(self) -> None:
        consumed  = get_total_consumed_today(self._user_id)
        burned    = get_total_calories_burned_today(self._user_id)
        net       = consumed - burned
        remaining = max(0, self._calorie_goal - consumed)
        over      = max(0, consumed - self._calorie_goal)

        self._metrics.cards[0].update(str(consumed))
        self._metrics.cards[1].update(str(burned))
        net_color = _ACCENT if net <= 0 else _WARN
        self._metrics.cards[2].update(str(net), value_color=net_color)
        self._metrics.cards[3].update(str(self._calorie_goal))

        self._donut.refresh(consumed, self._calorie_goal,
                            mode=self._mode, surplus_goal=self._surplus_goal)

        if self._mode == "deficit":
            if over > 0:
                self._balance_label.configure(
                    text=f"{over} kcal over goal", text_color=_DANGER)
            else:
                self._balance_label.configure(
                    text=f"{remaining} kcal remaining of {self._calorie_goal}",
                    text_color=_TEXT_SEC)
        else:
            surplus_hit = max(0, consumed - self._calorie_goal)
            self._balance_label.configure(
                text=f"{consumed} kcal consumed · +{surplus_hit} surplus",
                text_color=_ACCENT if surplus_hit > 0 else _TEXT_SEC)

        foods = get_todays_food(self._user_id)
        self._food_list.clear()
        if not foods:
            ctk.CTkLabel(self._food_list,
                         text="No food logged today.\nUse the form to add your first meal.",
                         font=ctk.CTkFont("Arial", size=12),
                         text_color=_TEXT_SEC).pack(pady=40)
            return
        for food in foods:
            FoodRow(self._food_list, entry=food, on_delete=self._handle_delete).pack(fill="x", pady=2)

    # ------------------------------------------------------------------
    def _handle_add(self) -> None:
        name = self._f_name.get().strip()
        cal  = self._f_cal.get().strip()
        if not name:
            self._toast.show("Please enter a food name.", kind="warning"); return
        try:
            cal = int(cal)
            if cal < 0: raise ValueError
        except ValueError:
            self._toast.show("Calories must be a non-negative integer.", kind="warning"); return
        create_food_entry(self._user_id, name, cal, self._f_meal.get())
        self._f_name.delete(0, "end")
        self._f_cal.delete(0, "end")
        self._toast.show(f"{name} logged ({cal} kcal).", kind="success")
        self._refresh()

    def _handle_delete(self, entry_id: int) -> None:
        if delete_food_entry(entry_id, self._user_id):
            self._toast.show("Food entry removed.", kind="info")
            self._refresh()

    def _handle_update_goal(self) -> None:
        try:
            goal = int(self._goal_entry.get())
            if goal <= 0: raise ValueError
        except ValueError:
            self._toast.show("Goal must be a positive integer.", kind="warning"); return
        if update_calorie_goal(self._user_id, goal):
            self._calorie_goal = goal
            self._toast.show(f"Daily goal updated to {goal} kcal.", kind="success")
            self._refresh()

    def _handle_mode_change(self, mode: str) -> None:
        self._mode = mode
        update_calorie_mode(self._user_id, mode, self._surplus_goal)
        self._update_surplus_visibility()
        self._refresh()

    def _handle_update_surplus(self) -> None:
        try:
            s = int(self._surplus_entry.get())
            if s <= 0: raise ValueError
        except ValueError:
            self._toast.show("Surplus target must be a positive integer.", kind="warning"); return
        self._surplus_goal = s
        update_calorie_mode(self._user_id, "surplus", s)
        self._toast.show(f"Surplus target set to +{s} kcal.", kind="success")
        self._refresh()
