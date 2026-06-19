"""
Mixin para CTkScrollableFrame que arregla el scroll con trackpad de macOS.

Contexto: Tcl 9 (que viene con Python 3.13+) emite `event.delta` fraccionario
en gestos de dos dedos del trackpad. El binding por defecto de CTkScrollableFrame
hace `yview('scroll', -event.delta, 'units')` — pero `scroll units` requiere
un entero, así que cualquier delta entre -1 y 1 se descarta y el contenido
no se mueve. Acumulamos los fragmentos hasta llegar a una unidad completa.
"""


class TrackpadScrollMixin:
    def _mouse_wheel_all(self, event):  # override de CTkScrollableFrame
        canvas = getattr(self, "_parent_canvas", None)
        if canvas is None:
            return
        if not self.check_if_master_is_canvas(event.widget):
            return

        accum = getattr(self, "_scroll_accum", 0.0) + float(event.delta)
        units = int(accum)
        self._scroll_accum = accum - units
        if units and canvas.yview() != (0.0, 1.0):
            canvas.yview_scroll(-units, "units")
