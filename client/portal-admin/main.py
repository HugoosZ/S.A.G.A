"""
SAGA - Portal Administrativo Desktop
Sistema de Apoyo y Gestión Académica
Universidad Diego Portales - Facultad de Ingeniería y Ciencias
"""

# Configurar apariencia ANTES de crear cualquier widget (crítico en macOS)
import customtkinter as ctk
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

import theme as t
from data import db
from components.sidebar import Sidebar
from views.dashboard_view import DashboardView
from views.documentos_view import DocumentosView


class SAGAApp(ctk.CTk):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()

        self.title("SAGA · Portal Administrativo · Universidad Diego Portales")
        self.geometry("1400x860")
        self.minsize(1180, 720)
        self.configure(fg_color=t.BG)

        db.init_db()

        # Layout con pack (más estable en macOS que grid mixto)
        self.sidebar = Sidebar(self, on_navigate=self._navigate)
        self.sidebar.pack(side="left", fill="y")

        self.content_container = ctk.CTkFrame(self, fg_color=t.BG, corner_radius=0)
        self.content_container.pack(side="left", fill="both", expand=True)

        self.views = {}
        self.current_view_name = None

        # Forzar layout y diferir la creación de la vista inicial
        # para que la ventana esté completamente lista en macOS
        self.update_idletasks()
        self.after(120, lambda: self._navigate("dashboard"))

    def _navigate(self, view_name: str):
        if view_name == self.current_view_name:
            return

        previous_view_name = self.current_view_name
        if previous_view_name and previous_view_name in self.views:
            self.views[previous_view_name].pack_forget()

        try:
            if view_name not in self.views:
                if view_name == "dashboard":
                    self.views[view_name] = DashboardView(self.content_container)
                elif view_name == "documentos":
                    self.views[view_name] = DocumentosView(self.content_container)

            self.views[view_name].pack(
                fill="both", expand=True,
                padx=t.PADDING_LG, pady=0,
            )
        except Exception:
            # Restore previous view so the screen does not go blank
            if previous_view_name and previous_view_name in self.views:
                self.views[previous_view_name].pack(
                    fill="both", expand=True,
                    padx=t.PADDING_LG, pady=0,
                )
            raise

        self.current_view_name = view_name

        if view_name == "documentos":
            self.views[view_name]._refresh_table()

        self.update_idletasks()


def main():
    app = SAGAApp()
    app.mainloop()


if __name__ == "__main__":
    main()
