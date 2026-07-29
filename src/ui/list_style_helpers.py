"""
Shared styling helpers for compact list/table views.
"""

import customtkinter as ctk


def make_badge(parent, text: str, bg_color: str, text_color: str, width: int, height: int = 22):
    badge = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8, width=width, height=height)
    badge.pack_propagate(False)
    ctk.CTkLabel(badge, text=text, text_color=text_color, font=("Segoe UI", 12, "bold")).pack(expand=True)
    return badge
