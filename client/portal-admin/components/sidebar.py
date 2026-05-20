"""Sidebar de navegación con branding UDP."""

import customtkinter as ctk
import theme as t


class Sidebar(ctk.CTkFrame):
    """Sidebar oscuro con logo, menú y user info."""

    def __init__(self, parent, on_navigate):
        super().__init__(
            parent,
            width=t.SIDEBAR_WIDTH,
            fg_color=t.SIDEBAR_BG,
            corner_radius=0,
        )
        # Evita que el sidebar se encoja al tamaño de sus hijos
        self.pack_propagate(False)
        # Tamaño mínimo absoluto para macOS (en algunos casos width no se respeta)
        self.configure(width=t.SIDEBAR_WIDTH)

        self.on_navigate = on_navigate
        self.nav_buttons = {}
        self.active_view = "dashboard"

        # ── Logo UDP ───────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self, fg_color="transparent", height=90)
        logo_frame.pack(fill="x", pady=(28, 8), padx=24)
        logo_frame.pack_propagate(False)

        # Mark cuadrado rojo "udp"
        mark = ctk.CTkFrame(
            logo_frame, width=44, height=44,
            fg_color=t.UDP_RED, corner_radius=6,
        )
        mark.pack(side="left")
        mark.pack_propagate(False)
        ctk.CTkLabel(
            mark, text="udp",
            font=(t.FONT_DISPLAY, 22, "bold"),
            text_color="white",
        ).place(relx=0.5, rely=0.55, anchor="center")

        # Texto "SAGA / Portal"
        txt = ctk.CTkFrame(logo_frame, fg_color="transparent")
        txt.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(
            txt, text="SAGA",
            font=(t.FONT_DISPLAY, 19, "bold"),
            text_color="white", anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            txt, text="PORTAL ADMIN",
            font=(t.FONT_FAMILY, 9, "bold"),
            text_color="#7A7A7A", anchor="w",
        ).pack(anchor="w", pady=(1, 0))

        # ── Separador ───────────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color="#2A2A2A").pack(
            fill="x", padx=20, pady=(16, 20)
        )

        # ── Sección "Navegación" ────────────────────────────────────────
        ctk.CTkLabel(
            self, text="NAVEGACIÓN",
            font=(t.FONT_FAMILY, 10, "bold"),
            text_color="#5A5A5A", anchor="w",
        ).pack(fill="x", padx=28, pady=(0, 10))

        # ── Items de menú ───────────────────────────────────────────────
        self._add_nav_item("dashboard", "Dashboard", "▮▮▮▮")
        self._add_nav_item("documentos", "Documentos", "📄")

        # ── Footer: información de usuario ──────────────────────────────
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Separador antes del user
        ctk.CTkFrame(self, height=1, fg_color="#2A2A2A").pack(
            fill="x", padx=20, pady=(12, 16)
        )

        user_frame = ctk.CTkFrame(self, fg_color="transparent")
        user_frame.pack(fill="x", padx=20, pady=(0, 24))

        # Avatar
        avatar = ctk.CTkFrame(
            user_frame, width=38, height=38,
            fg_color=t.UDP_RED, corner_radius=19,
        )
        avatar.pack(side="left")
        avatar.pack_propagate(False)
        ctk.CTkLabel(
            avatar, text="SE",
            font=(t.FONT_FAMILY, 12, "bold"),
            text_color="white",
        ).place(relx=0.5, rely=0.5, anchor="center")

        user_info = ctk.CTkFrame(user_frame, fg_color="transparent")
        user_info.pack(side="left", padx=(10, 0), fill="x", expand=True)
        ctk.CTkLabel(
            user_info, text="Secretaría",
            font=(t.FONT_FAMILY, 12, "bold"),
            text_color="white", anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            user_info, text="FIC · Pregrado",
            font=(t.FONT_FAMILY, 10),
            text_color="#7A7A7A", anchor="w",
        ).pack(anchor="w")

    def _add_nav_item(self, key: str, label: str, icon_text: str = ""):
        """Crea un botón de navegación que se comporta como item de menú."""
        is_active = (key == self.active_view)
        bg = t.UDP_RED if is_active else "transparent"
        fg = "white" if is_active else "#B5B5B5"

        btn = ctk.CTkButton(
            self,
            text=f"  {label}",
            anchor="w",
            font=(t.FONT_FAMILY, 13, "bold" if is_active else "normal"),
            height=42,
            corner_radius=6,
            fg_color=bg,
            hover_color=t.UDP_RED_HOVER if is_active else t.SIDEBAR_ITEM,
            text_color=fg,
            command=lambda k=key: self._handle_click(k),
        )
        btn.pack(fill="x", padx=14, pady=2)
        self.nav_buttons[key] = btn

    def _handle_click(self, key: str):
        self.set_active(key)
        self.on_navigate(key)

    def set_active(self, key: str):
        """Marca un item como activo y reordena estilos."""
        self.active_view = key
        for k, btn in self.nav_buttons.items():
            active = (k == key)
            btn.configure(
                fg_color=t.UDP_RED if active else "transparent",
                hover_color=t.UDP_RED_HOVER if active else t.SIDEBAR_ITEM,
                text_color="white" if active else "#B5B5B5",
                font=(t.FONT_FAMILY, 13, "bold" if active else "normal"),
            )
