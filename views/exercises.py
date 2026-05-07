# views/exercises.py
# =============================================================================
# Exercises view — the exercise library management page.
#
# Responsibilities:
#   - Add form: input fields for all exercise attributes + validation
#   - Exercise list: scrollable, shows all exercises with edit/delete actions
#   - Edit modal: pre-populated form in a CTkToplevel for updating records
#   - Delete: confirmation dialog before any destructive action
#
# Validation is done at the view layer (empty name, amount > 0, cal > 0)
# before any model call is made. The DB constraints are a second safety net,
# not the primary guard — this follows defensive programming principles.
# =============================================================================

import customtkinter as ctk
from components.widgets import (
    SectionCard, ExerciseRow, ScrollableList, ConfirmDialog,
)
from models.exercise import (
    get_all_exercises, create_exercise, update_exercise, delete_exercise,
)

_ACCENT     = "#1D9E75"
_ACCENT_DIM = "#1A3D30"
_TEXT_PRI   = "#EBEBEA"
_TEXT_SEC   = "#888880"
_CARD       = "#222220"
_BORDER     = "#2E2E2C"
_DANGER_DIM = "#3A0D0D"
_DANGER_TXT = "#F5A0A0"

_TYPES  = ["Reps", "Duration (min)"]
_DIFFS  = ["Easy", "Medium", "Hard"]
_DAYS   = ["Daily", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ExercisesView(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, toast, **kwargs):
        kwargs.setdefault("fg_color", "#1A1A1A")
        super().__init__(parent, **kwargs)
        self._user_id = user_id
        self._toast   = toast
        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(
            hdr, text="Exercise Library",
            font=ctk.CTkFont("Arial", size=20, weight="bold"),
            text_color=_TEXT_PRI, anchor="w",
        ).pack(side="left")

        self._count_label = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont("Arial", size=12),
            text_color=_TEXT_SEC, anchor="e",
        )
        self._count_label.pack(side="right")

        # Add-exercise form card
        form_card = SectionCard(self, title="Add new exercise")
        form_card.pack(fill="x", padx=24, pady=(14, 0))
        self._build_add_form(form_card.body)

        # Exercise list card
        list_card = SectionCard(self, title="All exercises")
        list_card.pack(fill="both", expand=True, padx=24, pady=(12, 20))

        self._ex_list = ScrollableList(list_card.body, height=340)
        self._ex_list.pack(fill="both", expand=True)

    def _build_add_form(self, parent) -> None:
        """Build the add-exercise input form inside the card body."""
        # Row 1: name, type, amount, difficulty, calories
        r1 = ctk.CTkFrame(parent, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 8))

        self._f_name = self._field(r1, "Exercise name", width=200)
        self._f_name.pack(side="left", padx=(0, 10))

        self._f_type = self._dropdown(r1, "Type", _TYPES, width=140)
        self._f_type.pack(side="left", padx=(0, 10))

        self._f_amount = self._field(r1, "Amount", placeholder="10", width=80)
        self._f_amount.pack(side="left", padx=(0, 10))

        self._f_diff = self._dropdown(r1, "Difficulty", _DIFFS, width=120)
        self._f_diff.pack(side="left", padx=(0, 10))

        self._f_cal = self._field(r1, "Est. kcal", placeholder="50", width=90)
        self._f_cal.pack(side="left", padx=(0, 10))

        # Row 2: muscle, day, buttons
        r2 = ctk.CTkFrame(parent, fg_color="transparent")
        r2.pack(fill="x")

        self._f_muscle = self._field(r2, "Muscle group", placeholder="e.g. Chest, Core", width=220)
        self._f_muscle.pack(side="left", padx=(0, 10))

        self._f_day = self._dropdown(r2, "Schedule", _DAYS, width=130)
        self._f_day.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            r2, text="+ Add exercise",
            width=130, height=34, corner_radius=7,
            fg_color=_ACCENT, hover_color="#158A62",
            font=ctk.CTkFont("Arial", size=13),
            text_color="#FFFFFF",
            command=self._handle_add,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            r2, text="Clear",
            width=70, height=34, corner_radius=7,
            fg_color="#2A2A28", hover_color="#3A3A38",
            font=ctk.CTkFont("Arial", size=13),
            text_color=_TEXT_SEC,
            command=self._clear_form,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Helper: labelled entry / dropdown
    # ------------------------------------------------------------------

    def _field(self, parent, label: str, placeholder: str = "", width: int = 140) -> ctk.CTkFrame:
        """Return a labelled CTkEntry wrapped in a frame."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            frame, text=label,
            font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC, anchor="w",
        ).pack(fill="x")
        entry = ctk.CTkEntry(
            frame, width=width, height=32,
            placeholder_text=placeholder,
            corner_radius=6,
            fg_color="#282826", border_color=_BORDER,
            text_color=_TEXT_PRI,
        )
        entry.pack(fill="x")
        frame._entry = entry   # attach so caller can do frame._entry.get()
        return frame

    def _dropdown(self, parent, label: str, values: list, width: int = 130) -> ctk.CTkFrame:
        """Return a labelled CTkOptionMenu wrapped in a frame."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(
            frame, text=label,
            font=ctk.CTkFont("Arial", size=11),
            text_color=_TEXT_SEC, anchor="w",
        ).pack(fill="x")
        menu = ctk.CTkOptionMenu(
            frame, values=values, width=width, height=32,
            corner_radius=6,
            fg_color="#282826", button_color="#3A3A38",
            button_hover_color="#4A4A48",
            text_color=_TEXT_PRI,
            dropdown_fg_color=_CARD,
            dropdown_text_color=_TEXT_PRI,
            dropdown_hover_color="#2A2A28",
        )
        menu.pack(fill="x")
        frame._menu = menu
        return frame

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def on_show(self) -> None:
        self._refresh_list()

    # ------------------------------------------------------------------
    # Internal — list rendering
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        exercises = get_all_exercises(self._user_id)
        self._count_label.configure(text=f"{len(exercises)} exercise{'s' if len(exercises) != 1 else ''} in library")
        self._ex_list.clear()

        if not exercises:
            ctk.CTkLabel(
                self._ex_list,
                text="No exercises yet. Add your first one above!",
                font=ctk.CTkFont("Arial", size=12),
                text_color=_TEXT_SEC,
            ).pack(pady=40)
            return

        for ex in exercises:
            row = ExerciseRow(
                self._ex_list, exercise=ex,
                on_edit=self._open_edit_modal,
                on_delete=self._handle_delete,
                show_check=False,
            )
            row.pack(fill="x", pady=2)

    # ------------------------------------------------------------------
    # Internal — form helpers
    # ------------------------------------------------------------------

    def _read_form(self) -> dict | None:
        """Read and validate the add form. Returns dict or None on error."""
        name   = self._f_name._entry.get().strip()
        amount = self._f_amount._entry.get().strip()
        cal    = self._f_cal._entry.get().strip()
        ex_type = self._f_type._menu.get()
        diff   = self._f_diff._menu.get()
        muscle = self._f_muscle._entry.get().strip()
        day    = self._f_day._menu.get()

        if not name:
            self._toast.show("Exercise name is required.", kind="warning")
            return None
        try:
            amount = int(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self._toast.show("Amount must be a positive whole number.", kind="warning")
            return None
        try:
            cal = int(cal)
            if cal <= 0:
                raise ValueError
        except ValueError:
            self._toast.show("Calories must be a positive whole number.", kind="warning")
            return None

        return {
            "name": name, "exercise_type": ex_type, "amount": amount,
            "difficulty": diff, "est_calories": cal,
            "target_muscle": muscle or None, "scheduled_day": day,
        }

    def _clear_form(self) -> None:
        self._f_name._entry.delete(0, "end")
        self._f_amount._entry.delete(0, "end")
        self._f_cal._entry.delete(0, "end")
        self._f_muscle._entry.delete(0, "end")
        self._f_type._menu.set("Reps")
        self._f_diff._menu.set("Easy")
        self._f_day._menu.set("Daily")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _handle_add(self) -> None:
        data = self._read_form()
        if data is None:
            return
        try:
            create_exercise(self._user_id, **data)
            self._clear_form()
            self._refresh_list()
            self._toast.show(f'"{data["name"]}" added to library.', kind="success")
        except Exception as e:
            if "Duplicate" in str(e) or "uq_ex_name" in str(e):
                self._toast.show("An exercise with that name already exists.", kind="error")
            else:
                self._toast.show(f"Error: {e}", kind="error")

    def _handle_delete(self, exercise_id: int) -> None:
        dlg = ConfirmDialog(self, "Delete this exercise?\nThis will also remove its log history.")
        if dlg.result:
            ok = delete_exercise(exercise_id, self._user_id)
            if ok:
                self._toast.show("Exercise deleted.", kind="info")
                self._refresh_list()
            else:
                self._toast.show("Delete failed.", kind="error")

    def _open_edit_modal(self, exercise_id: int) -> None:
        exercises = get_all_exercises(self._user_id)
        ex = next((e for e in exercises if e["exercise_id"] == exercise_id), None)
        if not ex:
            self._toast.show("Exercise not found.", kind="error")
            return
        EditModal(self, ex, self._user_id, self._toast, on_save=self._refresh_list)


# =============================================================================
# EditModal — CTkToplevel for updating an exercise
# =============================================================================

class EditModal(ctk.CTkToplevel):

    def __init__(self, parent, exercise: dict, user_id: int, toast, on_save):
        super().__init__(parent)
        self.title("Edit exercise")
        self.geometry("460x320")
        self.resizable(False, False)
        self.configure(fg_color="#222220")
        self.grab_set()

        self._ex      = exercise
        self._user_id = user_id
        self._toast   = toast
        self._on_save = on_save

        self._build()

    def _build(self) -> None:
        ex = self._ex
        pad = {"padx": 20}

        ctk.CTkLabel(
            self, text=f"Edit: {ex['name']}",
            font=ctk.CTkFont("Arial", size=15, weight="bold"),
            text_color="#EBEBEA", anchor="w",
        ).pack(fill="x", **pad, pady=(16, 12))

        # Row 1
        r1 = ctk.CTkFrame(self, fg_color="transparent")
        r1.pack(fill="x", **pad, pady=(0, 8))

        self._name   = self._entry(r1, "Name",       ex["name"],       width=180)
        self._amount = self._entry(r1, "Amount",     str(ex["amount"]),width=80)
        self._cal    = self._entry(r1, "Est. kcal",  str(ex["est_calories"]), width=80)

        # Row 2
        r2 = ctk.CTkFrame(self, fg_color="transparent")
        r2.pack(fill="x", **pad, pady=(0, 8))

        self._type   = self._menu(r2, "Type",       _TYPES, ex["exercise_type"], width=140)
        self._diff   = self._menu(r2, "Difficulty", _DIFFS, ex["difficulty"],    width=120)
        self._day    = self._menu(r2, "Schedule",   _DAYS,  ex["scheduled_day"], width=110)

        # Row 3
        r3 = ctk.CTkFrame(self, fg_color="transparent")
        r3.pack(fill="x", **pad, pady=(0, 12))
        self._muscle = self._entry(r3, "Muscle group", ex.get("target_muscle") or "", width=360)

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(**pad, pady=(0, 16))

        ctk.CTkButton(
            btn_row, text="Cancel", width=110, height=34, corner_radius=7,
            fg_color="#2A2A28", hover_color="#3A3A38",
            text_color="#888880", command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Save changes", width=130, height=34, corner_radius=7,
            fg_color="#1D9E75", hover_color="#158A62",
            text_color="#FFFFFF", command=self._handle_save,
        ).pack(side="left")

    def _entry(self, parent, label, value, width=140):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Arial", size=11),
                     text_color="#888880", anchor="w").pack(fill="x")
        e = ctk.CTkEntry(f, width=width, height=32, corner_radius=6,
                         fg_color="#282826", border_color="#2E2E2C",
                         text_color="#EBEBEA")
        e.insert(0, value)
        e.pack()
        return e

    def _menu(self, parent, label, values, current, width=130):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Arial", size=11),
                     text_color="#888880", anchor="w").pack(fill="x")
        m = ctk.CTkOptionMenu(f, values=values, width=width, height=32,
                              corner_radius=6, fg_color="#282826",
                              button_color="#3A3A38", button_hover_color="#4A4A48",
                              text_color="#EBEBEA", dropdown_fg_color="#222220",
                              dropdown_text_color="#EBEBEA",
                              dropdown_hover_color="#2A2A28")
        m.set(current)
        m.pack()
        return m

    def _handle_save(self) -> None:
        name   = self._name.get().strip()
        muscle = self._muscle.get().strip()

        if not name:
            self._toast.show("Name cannot be empty.", kind="warning")
            return
        try:
            amount = int(self._amount.get())
            cal    = int(self._cal.get())
            if amount <= 0 or cal <= 0:
                raise ValueError
        except ValueError:
            self._toast.show("Amount and calories must be positive integers.", kind="warning")
            return

        ok = update_exercise(
            exercise_id   = self._ex["exercise_id"],
            user_id       = self._user_id,
            name          = name,
            exercise_type = self._type.get(),
            amount        = amount,
            difficulty    = self._diff.get(),
            est_calories  = cal,
            target_muscle = muscle or None,
            scheduled_day = self._day.get(),
        )
        if ok:
            self._toast.show(f'"{name}" updated.', kind="success")
            self._on_save()
            self.destroy()
        else:
            self._toast.show("Update failed.", kind="error")
