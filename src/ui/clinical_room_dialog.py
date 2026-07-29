"""
Clinical Room Dialog
Dialog for creating and editing clinical rooms
"""

import customtkinter as ctk
import logging
from typing import Optional
from src.models.models import ClinicalRoom
from src.ui.voice_typing_mixin import VoiceTypingMixin

logger = logging.getLogger(__name__)


class ClinicalRoomDialog(VoiceTypingMixin, ctk.CTkToplevel):
    """Dialog for creating or editing a clinical room"""

    def __init__(
        self,
        parent,
        room: Optional[ClinicalRoom] = None,
        on_save: Optional[callable] = None,
        on_delete: Optional[callable] = None,
    ):
        super().__init__(parent)
        self.title("Add Clinical Room" if not room else "Edit Clinical Room")
        self.geometry("520x520")
        self.minsize(520, 520)
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.room = room
        self.on_save = on_save
        self.on_delete = on_delete
        self.fields = {}
        self._initialize_voice_typing()

        self._setup_ui()
        if room:
            self._load_room(room)

    def _setup_ui(self):
        outer_frame = ctk.CTkFrame(self)
        outer_frame.pack(fill="both", expand=True, padx=16, pady=16)

        title_text = "Create a new clinical room" if not self.room else f"Edit room: {self.room.room_name}"
        ctk.CTkLabel(outer_frame, text=title_text, font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 12))

        form_frame = ctk.CTkScrollableFrame(outer_frame)
        form_frame.pack(fill="both", expand=True)

        self.fields["room_name"] = self._create_field(form_frame, "Room Name *")
        self.fields["room_type"] = self._create_field(form_frame, "Room Type")
        self.fields["floor"] = self._create_field(form_frame, "Floor")
        self.fields["location_description"] = self._create_field(form_frame, "Location Description", multiline=True)

        self.status_label = ctk.CTkLabel(outer_frame, text="", font=("Arial", 10), text_color="red")
        self.status_label.pack(anchor="w", pady=(8, 6))

        button_frame = ctk.CTkFrame(outer_frame)
        button_frame.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(button_frame, text="Save Room", width=130, command=self._save_room).pack(side="left", padx=5)
        if self.room and self.room.id:
            ctk.CTkButton(
                button_frame,
                text="Delete Room",
                width=130,
                fg_color="red",
                command=self._delete_room,
            ).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", width=130, fg_color="gray", command=self._close).pack(side="left", padx=5)

    def _close(self):
        self.destroy()

    def _create_field(self, parent, label, multiline=False):
        return self._create_voice_field(parent, label, multiline=multiline, width=340)

    def _load_room(self, room: ClinicalRoom):
        self.fields["room_name"].insert(0, room.room_name)
        self.fields["room_type"].insert(0, room.room_type or "")
        self.fields["floor"].insert(0, str(room.floor) if room.floor is not None else "")
        if room.location_description:
            self.fields["location_description"].insert("1.0", room.location_description)

    def _save_room(self):
        room_name = self.fields["room_name"].get().strip()
        if not room_name:
            self._set_status("Room name is required", success=False)
            return

        room_type = self.fields["room_type"].get().strip() or None
        floor_value = self.fields["floor"].get().strip()
        floor = int(floor_value) if floor_value.isdigit() else None
        location_description = self.fields["location_description"].get("1.0", "end").strip() or None

        if self.room:
            self.room.room_name = room_name
            self.room.room_type = room_type
            self.room.floor = floor
            self.room.location_description = location_description
            room_data = self.room
        else:
            room_data = ClinicalRoom(
                room_name=room_name,
                room_type=room_type,
                floor=floor,
                location_description=location_description,
            )

        self.room = room_data
        if self.on_save:
            self.on_save(self.room)
        self._close()

    def _delete_room(self):
        if not self.room or not self.room.id:
            self._set_status("Room cannot be deleted before it is created.", success=False)
            return
        if self.on_delete:
            self.on_delete(self.room)
        self._close()

    def _set_status(self, message: str, success: bool = True):
        color = "green" if success else "red"
        self.status_label.configure(text=message, text_color=color)
        logger.info(message)
