# views/exercises.py
import customtkinter as ctk
from components.widgets import SectionCard, ExerciseRow, ScrollableList, ConfirmDialog
from models.exercise    import get_all_exercises, create_exercise, update_exercise, delete_exercise
from models.weight_log  import log_weight, get_weight_history, get_weighted_exercises

_ACCENT   = "#1D9E75"
_TEXT_PRI = "#EBEBEA"
_TEXT_SEC = "#888880"
_TEXT_TER = "#555550"
_CARD     = "#222220"
_BORDER   = "#2E2E2C"
_DANGER_DIM = "#3A0D0D"
_DANGER_TXT = "#F5A0A0"

_TYPES      = ["Reps", "Duration (min)", "Weighted"]
_CATEGORIES = ["Strength", "Cardio", "Core", "Flexibility", "Full Body"]
_DAYS       = ["Daily", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ExercisesView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, **kwargs):
        kwargs.setdefault("fg_color", "#1A1A1A")
        super().__init__(parent, **kwargs)
        self._user_id = user_id
        self._toast   = toast
        self._build_layout()

    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Exercise Library",
                     font=ctk.CTkFont("Arial", size=20, weight="bold"),
                     text_color=_TEXT_PRI, anchor="w").pack(side="left")
        self._count_label = ctk.CTkLabel(hdr, text="",
                                          font=ctk.CTkFont("Arial", size=12),
                                          text_color=_TEXT_SEC, anchor="e")
        self._count_label.pack(side="right")

        # Tabview: Library | Log Weight
        self._tabs = ctk.CTkTabview(self, fg_color="#1A1A1A", segmented_button_fg_color="#222220",
                                     segmented_button_selected_color=_ACCENT,
                                     segmented_button_unselected_color="#2A2A28",
                                     text_color=_TEXT_PRI)
        self._tabs.pack(fill="both", expand=True, padx=24, pady=(10, 20))

        self._tabs.add("Library")
        self._tabs.add("Log Weight")
        self._tabs.set("Library")

        self._build_library_tab(self._tabs.tab("Library"))
        self._build_weight_tab(self._tabs.tab("Log Weight"))

    def _build_library_tab(self, parent) -> None:
        # Add form
        form_card = SectionCard(parent, title="Add new exercise")
        form_card.pack(fill="x", pady=(0, 10))
        self._build_add_form(form_card.body)

        # List
        list_card = SectionCard(parent, title="All exercises")
        list_card.pack(fill="both", expand=True)
        self._ex_list = ScrollableList(list_card.body, height=300)
        self._ex_list.pack(fill="both", expand=True)

    def _build_add_form(self, parent) -> None:
        r1 = ctk.CTkFrame(parent, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 6))

        self._f_name     = self._field(r1, "Name", width=200)
        self._f_name.pack(side="left", padx=(0, 8))
        self._f_type     = self._dropdown(r1, "Type", _TYPES, width=130)
        self._f_type.pack(side="left", padx=(0, 8))
        self._f_amount   = self._field(r1, "Amount", placeholder="10", width=70)
        self._f_amount.pack(side="left", padx=(0, 8))
        self._f_category = self._dropdown(r1, "Category", _CATEGORIES, width=130)
        self._f_category.pack(side="left", padx=(0, 8))
        self._f_cal      = self._field(r1, "Est. kcal", placeholder="50", width=80)
        self._f_cal.pack(side="left", padx=(0, 8))

        r2 = ctk.CTkFrame(parent, fg_color="transparent")
        r2.pack(fill="x")
        self._f_muscle   = self._field(r2, "Muscle group", placeholder="e.g. Chest, Core", width=200)
        self._f_muscle.pack(side="left", padx=(0, 8))
        self._f_day      = self._dropdown(r2, "Schedule", _DAYS, width=110)
        self._f_day.pack(side="left", padx=(0, 8))
        self._f_notes    = self._field(r2, "Notes (optional)", placeholder="e.g. slow descent", width=200)
        self._f_notes.pack(side="left", padx=(0, 8))

        ctk.CTkButton(r2, text="+ Add", width=90, height=34, corner_radius=7,
                      fg_color=_ACCENT, hover_color="#158A62",
                      font=ctk.CTkFont("Arial", size=13), text_color="#FFFFFF",
                      command=self._handle_add).pack(side="left", padx=(0, 6))
        ctk.CTkButton(r2, text="Clear", width=60, height=34, corner_radius=7,
                      fg_color="#2A2A28", hover_color="#3A3A38",
                      font=ctk.CTkFont("Arial", size=13), text_color=_TEXT_SEC,
                      command=self._clear_form).pack(side="left")

    def _build_weight_tab(self, parent) -> None:
        log_card = SectionCard(parent, title="Log a weight session")
        log_card.pack(fill="x", pady=(0, 10))

        body = log_card.body
        r1 = ctk.CTkFrame(body, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 6))

        # Exercise selector (weighted only)
        ctk.CTkLabel(r1, text="Exercise", font=ctk.CTkFont("Arial", size=11),
                     text_color=_TEXT_SEC, anchor="w").pack(side="left", padx=(0, 4))
        self._w_exercise_var = ctk.StringVar()
        self._w_exercise_menu = ctk.CTkOptionMenu(
            r1, variable=self._w_exercise_var,
            values=["(load exercises)"], width=200, height=32, corner_radius=6,
            fg_color="#282826", button_color="#3A3A38", button_hover_color="#4A4A48",
            text_color=_TEXT_PRI, dropdown_fg_color=_CARD,
            dropdown_text_color=_TEXT_PRI, dropdown_hover_color="#2A2A28",
        )
        self._w_exercise_menu.pack(side="left", padx=(0, 12))

        for label, attr, placeholder, width in [
            ("Weight (kg)", "_w_kg",   "40.0",  80),
            ("Reps",        "_w_reps", "8",     60),
            ("Sets",        "_w_sets", "3",     60),
        ]:
            ctk.CTkLabel(r1, text=label, font=ctk.CTkFont("Arial", size=11),
                         text_color=_TEXT_SEC).pack(side="left", padx=(0, 4))
            entry = ctk.CTkEntry(r1, width=width, height=32, corner_radius=6,
                                 placeholder_text=placeholder, fg_color="#282826",
                                 border_color=_BORDER, text_color=_TEXT_PRI)
            entry.pack(side="left", padx=(0, 8))
            setattr(self, attr, entry)

        ctk.CTkButton(r1, text="Log session", width=110, height=34, corner_radius=7,
                      fg_color=_ACCENT, hover_color="#158A62",
                      font=ctk.CTkFont("Arial", size=13), text_color="#FFFFFF",
                      command=self._handle_log_weight).pack(side="left")

        # Weight history display
        hist_card = SectionCard(parent, title="Recent weight logs")
        hist_card.pack(fill="both", expand=True)
        self._w_history_list = ScrollableList(hist_card.body, height=300)
        self._w_history_list.pack(fill="both", expand=True)

        self._w_exercise_menu.configure(command=lambda _: self._refresh_weight_history())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _field(self, parent, label, placeholder="", width=140):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Arial", size=11),
                     text_color=_TEXT_SEC, anchor="w").pack(fill="x")
        e = ctk.CTkEntry(f, width=width, height=32, placeholder_text=placeholder,
                         corner_radius=6, fg_color="#282826", border_color=_BORDER,
                         text_color=_TEXT_PRI)
        e.pack(fill="x")
        f._entry = e
        return f

    def _dropdown(self, parent, label, values, width=130):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Arial", size=11),
                     text_color=_TEXT_SEC, anchor="w").pack(fill="x")
        m = ctk.CTkOptionMenu(f, values=values, width=width, height=32, corner_radius=6,
                              fg_color="#282826", button_color="#3A3A38",
                              button_hover_color="#4A4A48", text_color=_TEXT_PRI,
                              dropdown_fg_color=_CARD, dropdown_text_color=_TEXT_PRI,
                              dropdown_hover_color="#2A2A28")
        m.pack(fill="x")
        f._menu = m
        return f

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self._refresh_list()
        self._refresh_weighted_exercises()

    def _refresh_list(self) -> None:
        exercises = get_all_exercises(self._user_id)
        self._count_label.configure(
            text=f"{len(exercises)} exercise{'s' if len(exercises) != 1 else ''} in library"
        )
        self._ex_list.clear()
        if not exercises:
            ctk.CTkLabel(self._ex_list,
                         text="No exercises yet. Add your first one above!",
                         font=ctk.CTkFont("Arial", size=12),
                         text_color=_TEXT_SEC).pack(pady=40)
            return
        for ex in exercises:
            row = ExerciseRow(self._ex_list, exercise=ex,
                              on_edit=self._open_edit_modal,
                              on_delete=self._handle_delete,
                              show_check=False)
            row.pack(fill="x", pady=2)

    def _refresh_weighted_exercises(self) -> None:
        weighted = get_weighted_exercises(self._user_id)
        names = [f"{w['name']}" for w in weighted] if weighted else ["No weighted exercises"]
        self._weighted_ids = {w['name']: w['exercise_id'] for w in weighted}
        self._w_exercise_menu.configure(values=names)
        if names:
            self._w_exercise_var.set(names[0])
            self._refresh_weight_history()

    def _refresh_weight_history(self) -> None:
        self._w_history_list.clear()
        name = self._w_exercise_var.get()
        ex_id = self._weighted_ids.get(name)
        if not ex_id:
            return
        history = get_weight_history(self._user_id, ex_id)
        if not history:
            ctk.CTkLabel(self._w_history_list,
                         text="No sessions logged yet for this exercise.",
                         font=ctk.CTkFont("Arial", size=12),
                         text_color=_TEXT_SEC).pack(pady=20)
            return
        for entry in reversed(history):  # most recent first
            r = ctk.CTkFrame(self._w_history_list, fg_color="transparent")
            r.pack(fill="x", pady=2)
            date_str = str(entry["log_date"])
            ctk.CTkLabel(r, text=date_str, font=ctk.CTkFont("Arial", size=11),
                         text_color=_TEXT_SEC, width=90, anchor="w").pack(side="left")
            detail = f"{entry['weight_kg']} kg  ×  {entry['reps']} reps  ×  {entry['sets']} sets"
            ctk.CTkLabel(r, text=detail, font=ctk.CTkFont("Arial", size=12),
                         text_color=_TEXT_PRI, anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(self._w_history_list, height=1, fg_color="#2C2C2A").pack(fill="x")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _read_form(self):
        name   = self._f_name._entry.get().strip()
        amount = self._f_amount._entry.get().strip()
        cal    = self._f_cal._entry.get().strip()
        if not name:
            self._toast.show("Exercise name is required.", kind="warning"); return None
        try:
            amount = int(amount)
            if amount <= 0: raise ValueError
        except ValueError:
            self._toast.show("Amount must be a positive whole number.", kind="warning"); return None
        try:
            cal = int(cal)
            if cal <= 0: raise ValueError
        except ValueError:
            self._toast.show("Calories must be a positive whole number.", kind="warning"); return None
        return {
            "name": name,
            "exercise_type": self._f_type._menu.get().replace(" (min)", ""),
            "amount": amount,
            "category": self._f_category._menu.get(),
            "est_calories": cal,
            "target_muscle": self._f_muscle._entry.get().strip() or None,
            "scheduled_day": self._f_day._menu.get(),
            "notes": self._f_notes._entry.get().strip() or None,
        }

    def _clear_form(self) -> None:
        for attr in ("_f_name","_f_amount","_f_cal","_f_muscle","_f_notes"):
            getattr(self, attr)._entry.delete(0, "end")

    def _handle_add(self) -> None:
        data = self._read_form()
        if not data: return
        try:
            create_exercise(self._user_id, **data)
            self._clear_form()
            self._refresh_list()
            self._refresh_weighted_exercises()
            self._toast.show(f'"{data["name"]}" added.', kind="success")
        except Exception as e:
            if "Duplicate" in str(e) or "uq_ex_name" in str(e):
                self._toast.show("An exercise with that name already exists.", kind="error")
            else:
                self._toast.show(f"Error: {e}", kind="error")

    def _handle_delete(self, exercise_id: int) -> None:
        dlg = ConfirmDialog(self, "Delete this exercise?\nLog entries will also be removed.")
        if dlg.result:
            if delete_exercise(exercise_id, self._user_id):
                self._toast.show("Exercise deleted.", kind="info")
                self._refresh_list()
                self._refresh_weighted_exercises()
            else:
                self._toast.show("Delete failed.", kind="error")

    def _handle_log_weight(self) -> None:
        name  = self._w_exercise_var.get()
        ex_id = self._weighted_ids.get(name)
        if not ex_id:
            self._toast.show("Select a weighted exercise first.", kind="warning"); return
        try:
            kg   = float(self._w_kg.get())
            reps = int(self._w_reps.get())
            sets = int(self._w_sets.get())
            if kg <= 0 or reps <= 0 or sets <= 0: raise ValueError
        except ValueError:
            self._toast.show("Enter valid weight, reps, and sets.", kind="warning"); return

        log_weight(self._user_id, ex_id, kg, reps, sets)
        self._w_kg.delete(0, "end")
        self._w_reps.delete(0, "end")
        self._w_sets.delete(0, "end")
        self._refresh_weight_history()
        self._toast.show(f"{kg} kg × {reps} reps × {sets} sets logged.", kind="success")

    def _open_edit_modal(self, exercise_id: int) -> None:
        exercises = get_all_exercises(self._user_id)
        ex = next((e for e in exercises if e["exercise_id"] == exercise_id), None)
        if not ex:
            self._toast.show("Exercise not found.", kind="error"); return
        EditModal(self, ex, self._user_id, self._toast,
                  on_save=lambda: (self._refresh_list(), self._refresh_weighted_exercises()))


# =============================================================================
class EditModal(ctk.CTkToplevel):

    def __init__(self, parent, exercise, user_id, toast, on_save):
        super().__init__(parent)
        self.title("Edit exercise")
        self.geometry("500,300".replace(",", "x"))
        self.geometry("500x340")
        self.resizable(False, False)
        self.configure(fg_color="#222220")
        self.grab_set()
        self._ex = exercise; self._user_id = user_id
        self._toast = toast; self._on_save = on_save
        self._build()

    def _build(self):
        ex = self._ex
        pad = {"padx": 20}
        ctk.CTkLabel(self, text=f"Edit: {ex['name']}",
                     font=ctk.CTkFont("Arial", size=15, weight="bold"),
                     text_color="#EBEBEA", anchor="w").pack(fill="x", **pad, pady=(16, 10))

        r1 = ctk.CTkFrame(self, fg_color="transparent")
        r1.pack(fill="x", **pad, pady=(0, 8))
        self._name   = self._e(r1, "Name",       ex["name"],          180)
        self._amount = self._e(r1, "Amount",      str(ex["amount"]),   70)
        self._cal    = self._e(r1, "Est. kcal",   str(ex["est_calories"]), 70)

        r2 = ctk.CTkFrame(self, fg_color="transparent")
        r2.pack(fill="x", **pad, pady=(0, 8))
        self._type     = self._m(r2, "Type",     _TYPES,      ex["exercise_type"], 140)
        self._category = self._m(r2, "Category", _CATEGORIES, ex.get("category","Strength"), 130)
        self._day      = self._m(r2, "Schedule", _DAYS,       ex["scheduled_day"],  110)

        r3 = ctk.CTkFrame(self, fg_color="transparent")
        r3.pack(fill="x", **pad, pady=(0, 8))
        self._muscle = self._e(r3, "Muscle group", ex.get("target_muscle") or "", 200)
        self._notes  = self._e(r3, "Notes", ex.get("notes") or "", 220)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(**pad, pady=(0, 16))
        ctk.CTkButton(btns, text="Cancel", width=100, height=34, corner_radius=7,
                      fg_color="#2A2A28", hover_color="#3A3A38",
                      text_color="#888880", command=self.destroy).pack(side="left", padx=(0,8))
        ctk.CTkButton(btns, text="Save changes", width=130, height=34, corner_radius=7,
                      fg_color="#1D9E75", hover_color="#158A62",
                      text_color="#FFFFFF", command=self._save).pack(side="left")

    def _e(self, parent, label, value, width):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Arial", size=11),
                     text_color="#888880", anchor="w").pack(fill="x")
        e = ctk.CTkEntry(f, width=width, height=32, corner_radius=6,
                         fg_color="#282826", border_color="#2E2E2C", text_color="#EBEBEA")
        e.insert(0, value)
        e.pack()
        return e

    def _m(self, parent, label, values, current, width):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Arial", size=11),
                     text_color="#888880", anchor="w").pack(fill="x")
        m = ctk.CTkOptionMenu(f, values=values, width=width, height=32, corner_radius=6,
                              fg_color="#282826", button_color="#3A3A38",
                              button_hover_color="#4A4A48", text_color="#EBEBEA",
                              dropdown_fg_color="#222220", dropdown_text_color="#EBEBEA",
                              dropdown_hover_color="#2A2A28")
        m.set(current)
        m.pack()
        return m

    def _save(self):
        name = self._name.get().strip()
        if not name:
            self._toast.show("Name cannot be empty.", kind="warning"); return
        try:
            amount = int(self._amount.get())
            cal    = int(self._cal.get())
            if amount <= 0 or cal <= 0: raise ValueError
        except ValueError:
            self._toast.show("Amount and calories must be positive integers.", kind="warning"); return

        ok = update_exercise(
            exercise_id=self._ex["exercise_id"], user_id=self._user_id,
            name=name, exercise_type=self._type.get().replace(" (min)",""),
            amount=amount, category=self._category.get(), est_calories=cal,
            target_muscle=self._muscle.get().strip() or None,
            scheduled_day=self._day.get(),
            notes=self._notes.get().strip() or None,
        )
        if ok:
            self._toast.show(f'"{name}" updated.', kind="success")
            self._on_save()
            self.destroy()
        else:
            self._toast.show("Update failed.", kind="error")
