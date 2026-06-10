"""Componente KPI Card - tarjeta de métrica destacada."""

import customtkinter as ctk
import theme as t


class KPICard(ctk.CTkFrame):
    """Tarjeta de KPI con label, valor grande y subtítulo opcional."""

    def __init__(
        self,
        parent,
        label: str,
        valor: str,
        sub: str = "",
        trend: str = "",
        trend_up: bool = True,
        accent: bool = False,
        progress: float = None,
    ):
        bg = t.UDP_RED if accent else t.SURFACE
        text_color = "white" if accent else t.INK
        label_color = "#FFE4E5" if accent else t.MUTED
        sub_color = "#FFD3D6" if accent else t.INK_2

        super().__init__(
            parent,
            fg_color=bg,
            corner_radius=t.CORNER_RADIUS,
            border_width=0 if accent else 1,
            border_color=t.BORDER,
        )
        self.accent = accent

        # ── Label superior ──────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text=label,
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=label_color,
            anchor="w",
        ).pack(fill="x", padx=22, pady=(20, 8))

        # ── Valor (número grande) ───────────────────────────────────────
        ctk.CTkLabel(
            self,
            text=valor,
            font=(t.FONT_DISPLAY, t.SIZE_KPI, "bold"),
            text_color=text_color,
            anchor="w",
        ).pack(fill="x", padx=22, pady=(0, 4))

        # ── Subtítulo ───────────────────────────────────────────────────
        if sub:
            ctk.CTkLabel(
                self,
                text=sub,
                font=(t.FONT_FAMILY, t.SIZE_SMALL),
                text_color=sub_color,
                anchor="w",
            ).pack(fill="x", padx=22, pady=(0, 8))

        # ── Barra de progreso opcional ──────────────────────────────────
        if progress is not None:
            bar_frame = ctk.CTkFrame(self, fg_color="transparent", height=8)
            bar_frame.pack(fill="x", padx=22, pady=(4, 8))
            bar = ctk.CTkProgressBar(
                bar_frame,
                height=6,
                corner_radius=3,
                fg_color=t.BORDER_SOFT if not accent else "#A82329",
                progress_color=t.UDP_RED if not accent else "white",
            )
            bar.pack(fill="x")
            bar.set(progress / 100)

        # ── Trend opcional (con separador) ──────────────────────────────
        if trend:
            sep_color = "#A82329" if accent else t.BORDER_SOFT
            sep = ctk.CTkFrame(self, height=1, fg_color=sep_color)
            sep.pack(fill="x", padx=22, pady=(8, 0))

            trend_color = "#B6F0C4" if accent else (t.SUCCESS if trend_up else t.MUTED)
            arrow = "▲" if trend_up else "▼"
            ctk.CTkLabel(
                self,
                text=f"{arrow}  {trend}",
                font=(t.FONT_FAMILY, t.SIZE_TINY),
                text_color=trend_color,
                anchor="w",
            ).pack(fill="x", padx=22, pady=(8, 18))
        else:
            # padding inferior si no hay trend
            ctk.CTkFrame(self, height=10, fg_color="transparent").pack()
