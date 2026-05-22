"""Vista del dashboard: KPIs, gráficos y actividad reciente."""

import customtkinter as ctk
import theme as t
from data import db
from components.kpi_card import KPICard
from components.charts import LineChartCard, DonutChartCard


# Mapa de colores por categoría (para los tags)
CATEGORY_COLORS = {
    "TRAMITE":        ("#F4ECE1", "#8B5A14"),
    "PLAZO":          ("#E6EEF7", "#1F5C8F"),
    "REGLAMENTO":     (t.UDP_RED_SOFT, t.UDP_RED),
    "MALLA":          ("#EAF0E4", "#4A6730"),
    "CONVALIDACION":  ("#F0E9EE", "#6B3A5A"),
    "OTRO":           (t.SURFACE_2, t.MUTED),
}


class DashboardView(ctk.CTkScrollableFrame):
    """Scrollable view del dashboard completo."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=t.BG,
            corner_radius=1,   # 0 causa bug de renderizado en macOS
            scrollbar_button_color=t.BORDER,
            scrollbar_button_hover_color=t.MUTED,
        )

        self._build_header()
        self._build_kpis()
        self._build_charts()
        self._build_activity()

    # ── Page header ─────────────────────────────────────────────────────
    def _build_header(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", pady=(28, 24))

        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left, text="RESUMEN GENERAL",
            font=(t.FONT_FAMILY, 10, "bold"),
            text_color=t.UDP_RED, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            left, text="Métricas del sistema",
            font=(t.FONT_DISPLAY, t.SIZE_DISPLAY, "bold"),
            text_color=t.INK, anchor="w",
        ).pack(anchor="w", pady=(4, 4))
        ctk.CTkLabel(
            left,
            text="Estado del procesamiento automatizado de correos en los últimos 7 días.",
            font=(t.FONT_FAMILY, t.SIZE_BODY),
            text_color=t.MUTED, anchor="w",
        ).pack(anchor="w")

        # Badge "Sistema operativo"
        badge = ctk.CTkFrame(
            head, fg_color=t.SUCCESS_BG, corner_radius=20, height=34,
        )
        badge.pack(side="right", anchor="ne")
        badge.pack_propagate(False)

        dot = ctk.CTkFrame(badge, width=8, height=8, fg_color=t.SUCCESS, corner_radius=4)
        dot.pack(side="left", padx=(14, 6), pady=12)
        dot.pack_propagate(False)
        ctk.CTkLabel(
            badge, text="Sistema operativo",
            font=(t.FONT_FAMILY, t.SIZE_SMALL, "bold"),
            text_color=t.SUCCESS,
        ).pack(side="left", padx=(0, 16))

        # Separador
        ctk.CTkFrame(self, height=1, fg_color=t.BORDER).pack(fill="x", pady=(0, 28))

    # ── KPI Cards ───────────────────────────────────────────────────────
    def _build_kpis(self):
        r = db.get_metricas_resumen()

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 24))

        for i in range(4):
            grid.grid_columnconfigure(i, weight=1, uniform="kpi")

        KPICard(
            grid,
            label="Correos procesados",
            valor=str(r["total_7d"]),
            sub="Últimos 7 días",
            trend="+18.4% vs. semana anterior",
            trend_up=True,
            accent=True,
        ).grid(row=0, column=0, sticky="nsew", padx=(0, 9))

        KPICard(
            grid,
            label="Respondidos automáticamente",
            valor=str(r["respondidos_auto_7d"]),
            sub=f"{r['tasa_automatizacion']}% de automatización",
            progress=r["tasa_automatizacion"],
        ).grid(row=0, column=1, sticky="nsew", padx=9)

        KPICard(
            grid,
            label="Derivados a Secretaría",
            valor=str(r["derivados_7d"]),
            sub="Requieren atención manual",
            trend="Prioridad media-baja",
            trend_up=False,
        ).grid(row=0, column=2, sticky="nsew", padx=9)

        KPICard(
            grid,
            label="Tiempo medio de respuesta",
            valor=f"{r['tiempo_promedio_s']}s",
            sub="Por correo automatizado",
            trend="-0.6s vs. mes anterior",
            trend_up=True,
        ).grid(row=0, column=3, sticky="nsew", padx=(9, 0))

    # ── Charts ─────────────────────────────────────────────────────────
    def _build_charts(self):
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 24))
        grid.grid_columnconfigure(0, weight=2, uniform="chart")
        grid.grid_columnconfigure(1, weight=1, uniform="chart")

        LineChartCard(
            grid,
            title="Volumen de correos · Últimos 30 días",
            subtitle="Diferenciado por respuesta automática y derivación manual.",
            datos=db.get_serie_historica(),
        ).grid(row=0, column=0, sticky="nsew", padx=(0, 9))

        DonutChartCard(
            grid,
            title="Distribución por categoría",
            subtitle="Total acumulado del mes.",
            datos=db.get_clasificaciones(),
        ).grid(row=0, column=1, sticky="nsew", padx=(9, 0))

    # ── Actividad reciente ─────────────────────────────────────────────
    def _build_activity(self):
        card = ctk.CTkFrame(
            self, fg_color=t.SURFACE, corner_radius=t.CORNER_RADIUS,
            border_width=1, border_color=t.BORDER,
        )
        card.pack(fill="x", pady=(0, 28))

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 12))
        ctk.CTkLabel(
            header, text="Actividad reciente",
            font=(t.FONT_DISPLAY, t.SIZE_TITLE, "bold"),
            text_color=t.INK, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Últimos correos procesados por SAGA.",
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED, anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(card, height=1, fg_color=t.BORDER_SOFT).pack(fill="x")

        # ── Tabla manual ────────────────────────────────────────────────
        # Cabecera
        cols = [
            ("ASUNTO",     0.35),
            ("REMITENTE",  0.20),
            ("CATEGORÍA",  0.15),
            ("CONFIANZA",  0.12),
            ("ESTADO",     0.13),
            ("HORA",       0.05),
        ]

        head_row = ctk.CTkFrame(card, fg_color=t.SURFACE_2, height=34)
        head_row.pack(fill="x")
        head_row.pack_propagate(False)
        for col, w in cols:
            ctk.CTkLabel(
                head_row, text=col,
                font=(t.FONT_FAMILY, 10, "bold"),
                text_color=t.MUTED, anchor="w",
            ).place(relx=self._col_x(cols, col), rely=0.5, anchor="w")

        ctk.CTkFrame(card, height=1, fg_color=t.BORDER).pack(fill="x")

        # Filas
        correos = db.get_correos_recientes(8)
        for i, c in enumerate(correos):
            self._build_correo_row(card, c, alt=(i % 2 == 1))

        # Padding inferior
        ctk.CTkFrame(card, height=14, fg_color="transparent").pack(fill="x")

    @staticmethod
    def _col_x(cols, target):
        """Devuelve la posición relativa X de cada columna."""
        x = 0.02
        for name, w in cols:
            if name == target:
                return x
            x += w
        return x

    def _build_correo_row(self, parent, correo, alt=False):
        bg = t.SURFACE_2 if alt else t.SURFACE
        cols = [(0.35, "asunto"), (0.20, "remitente"),
                (0.15, "categoria"), (0.12, "confianza"),
                (0.13, "estado"), (0.05, "hora")]

        row = ctk.CTkFrame(parent, fg_color=bg, height=52)
        row.pack(fill="x")
        row.pack_propagate(False)

        # Asunto
        ctk.CTkLabel(
            row, text=correo["asunto"],
            font=(t.FONT_FAMILY, t.SIZE_BODY, "bold"),
            text_color=t.INK, anchor="w",
        ).place(relx=0.02, rely=0.5, anchor="w")

        # Remitente
        ctk.CTkLabel(
            row, text=correo["remitente"],
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED, anchor="w",
        ).place(relx=0.37, rely=0.5, anchor="w")

        # Categoría (tag)
        bg_tag, fg_tag = CATEGORY_COLORS.get(correo["clasificacion"], (t.SURFACE_2, t.MUTED))
        tag = ctk.CTkFrame(row, fg_color=bg_tag, corner_radius=4, height=22)
        tag.place(relx=0.57, rely=0.5, anchor="w")
        ctk.CTkLabel(
            tag, text=correo["clasificacion"],
            font=(t.FONT_FAMILY, 10, "bold"),
            text_color=fg_tag,
        ).pack(padx=8, pady=2)

        # Confianza (barra)
        conf_wrap = ctk.CTkFrame(row, fg_color="transparent")
        conf_wrap.place(relx=0.72, rely=0.5, anchor="w")
        bar_bg = ctk.CTkFrame(conf_wrap, width=60, height=4,
                              fg_color=t.BORDER_SOFT, corner_radius=2)
        bar_bg.pack(side="left", pady=2)
        bar_bg.pack_propagate(False)
        fill_w = int(60 * correo["confianza"])
        ctk.CTkFrame(bar_bg, width=fill_w, height=4,
                     fg_color=t.UDP_RED, corner_radius=2).place(x=0, y=0)
        ctk.CTkLabel(
            conf_wrap, text=f" {int(correo['confianza']*100)}%",
            font=(t.FONT_FAMILY, t.SIZE_TINY),
            text_color=t.MUTED,
        ).pack(side="left", padx=(6, 0))

        # Estado
        if correo["estado"] == "respondido_auto":
            estado_bg, estado_fg, estado_txt = t.SUCCESS_BG, t.SUCCESS, "Respondido"
        else:
            estado_bg, estado_fg, estado_txt = t.WARNING_BG, t.WARNING, "Derivado"

        est_wrap = ctk.CTkFrame(row, fg_color=estado_bg, corner_radius=12, height=24)
        est_wrap.place(relx=0.84, rely=0.5, anchor="w")
        dot = ctk.CTkFrame(est_wrap, width=6, height=6, fg_color=estado_fg, corner_radius=3)
        dot.pack(side="left", padx=(10, 5), pady=9)
        dot.pack_propagate(False)
        ctk.CTkLabel(
            est_wrap, text=estado_txt,
            font=(t.FONT_FAMILY, t.SIZE_TINY, "bold"),
            text_color=estado_fg,
        ).pack(side="left", padx=(0, 12))

        # Hora
        ctk.CTkLabel(
            row, text=correo["fecha"].strftime("%H:%M"),
            font=(t.FONT_FAMILY, t.SIZE_SMALL),
            text_color=t.MUTED, anchor="e",
        ).place(relx=0.98, rely=0.5, anchor="e")

        # Separador inferior
        sep = ctk.CTkFrame(parent, height=1, fg_color=t.BORDER_SOFT)
        sep.pack(fill="x")
