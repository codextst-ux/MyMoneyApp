import tkinter as tk
import os
import tempfile
import threading
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk

from models.categoria import Categoria
from models.movimiento import Movimiento
from models.persona import Persona
from money import dinero, sumar
from services.categoria_service import CategoriaService
from services.movimiento_service import MovimientoService
from services.persona_service import PersonaService
from services.nota_service import NotaService
from services.interprete_nota import interpretar
from services.audio_service import guardar_audio, transcribir


def error(parent, value):
    messagebox.showerror("No se pudo completar", str(value), parent=parent)


def limpiar(tabla):
    for item in tabla.get_children(): tabla.delete(item)


def tabla(parent, cols, headings):
    tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
    for col in cols:
        tree.heading(col, text=headings[col]); tree.column(col, width=130, anchor="w")
    return tree


class MoneyApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Mi App de Dinero"); self.geometry("1050x700"); self.minsize(900, 600)
        self.movimientos, self.personas, self.categorias, self.notas = MovimientoService(), PersonaService(), CategoriaService(), NotaService()
        self._estilos(); self._ui(); self.actualizar_inicio()

    def _estilos(self):
        self.configure(bg="#f5f7fb"); s=ttk.Style(self); s.theme_use("clam")
        s.configure("TFrame", background="#f5f7fb"); s.configure("Card.TFrame", background="#ffffff")
        s.configure("Title.TLabel", background="#f5f7fb", font=("Arial",22,"bold")); s.configure("Subtitle.TLabel", background="#f5f7fb", foreground="#64748b")
        s.configure("CardTitle.TLabel", background="#ffffff", foreground="#64748b", font=("Arial",10,"bold")); s.configure("CardValue.TLabel", background="#ffffff", foreground="#0f172a", font=("Arial",20,"bold"))
        s.configure("Treeview", rowheight=30, font=("Arial",10)); s.configure("Treeview.Heading", font=("Arial",10,"bold"))

    def _ui(self):
        root=ttk.Frame(self,padding=24); root.pack(fill="both",expand=True); top=ttk.Frame(root); top.pack(fill="x")
        ttk.Label(top,text="Mi App de Dinero",style="Title.TLabel").pack(side="left")
        for text, command in [("Saldos",self.abrir_saldos),("Personas",self.abrir_personas),("Categorías",self.abrir_categorias),("Movimientos",self.abrir_movimientos),("Revisar notas",self.abrir_notas),("+ Nota",self.abrir_nota),("↻ Actualizar",self.actualizar_inicio)]: ttk.Button(top,text=text,command=command).pack(side="right",padx=(8,0))
        ttk.Label(root,text="Resumen de tu dinero y movimientos recientes",style="Subtitle.TLabel").pack(anchor="w",pady=(2,20))
        cards=ttk.Frame(root); cards.pack(fill="x"); self.cards=[]
        for pos, title in enumerate(("BALANCE GENERAL","SALDO VIRTUAL (QR)","EFECTIVO EN MANO","POR COBRAR","POR PAGAR")):
            card=ttk.Frame(cards,style="Card.TFrame",padding=16); card.grid(row=0,column=pos,sticky="nsew",padx=(0,12 if pos<4 else 0)); cards.columnconfigure(pos,weight=1)
            ttk.Label(card,text=title,style="CardTitle.TLabel").pack(anchor="w"); value=ttk.Label(card,text="0.00 Bs",style="CardValue.TLabel"); value.pack(anchor="w",pady=(8,0)); self.cards.append(value)
        self.gastos_mes=ttk.Label(root,text="Gastos personales este mes: 0.00 Bs",style="Subtitle.TLabel")
        self.gastos_mes.pack(anchor="w",pady=(12,0))
        actions=ttk.Frame(root); actions.pack(fill="x",pady=22); ttk.Label(actions,text="REGISTRAR RÁPIDO",style="Subtitle.TLabel").pack(anchor="w",pady=(0,8))
        for text, kind in [("+ Ingreso","ingreso"),("+ Gasto","gasto"),("+ Préstamo","prestamo"),("+ Deuda","deuda"),("+ Pago","pago")]: ttk.Button(actions,text=text,command=lambda t=kind:self.abrir_formulario(t)).pack(side="left",padx=(0,8))
        box=ttk.Frame(root,style="Card.TFrame",padding=16); box.pack(fill="both",expand=True); ttk.Label(box,text="ÚLTIMOS MOVIMIENTOS",style="CardTitle.TLabel").pack(anchor="w",pady=(0,10))
        self.recientes=tabla(box,("fecha","tipo","descripcion","categoria","medio","monto"),{"fecha":"Fecha","tipo":"Tipo","descripcion":"Descripción","categoria":"Categoría","medio":"Medio","monto":"Monto"}); self.recientes.column("descripcion",width=340); self.recientes.pack(fill="both",expand=True)

    def actualizar_inicio(self):
        resumen=self.movimientos.obtener_resumen_financiero()
        for label,key in zip(self.cards,("balance_general","virtual","efectivo","por_cobrar","por_pagar")): label.configure(text=f"{resumen[key]:.2f} Bs")
        cats={c.id:c.nombre for c in self.categorias.obtener_todas()}; limpiar(self.recientes)
        for m in self.movimientos.obtener_todos()[:12]: self.recientes.insert("","end",values=(m.fecha,m.tipo.title(),m.descripcion,cats.get(m.categoria_id,"—"),"Efectivo" if m.medio_pago=="efectivo" else "QR / Virtual",f"{self.signo(m)}{m.monto:.2f} Bs"))
        hoy=date.today()
        yo=next((p for p in self.personas.obtener_todas() if p.nombre=="Yo"),None)
        gastos_mes=self.movimientos.obtener_filtrados(
            fecha_desde=hoy.replace(day=1).isoformat(), fecha_hasta=hoy.isoformat(), tipo="gasto"
        )
        total=sumar(self.parte_personal(m, yo.id) for m in gastos_mes if yo)
        self.gastos_mes.configure(text=f"Gastos personales este mes: {total:.2f} Bs")

    @staticmethod
    def parte_personal(movimiento, yo_id):
        if movimiento.participaciones:
            return next(
                (parte["monto"] for parte in movimiento.participaciones if parte["persona_id"] == yo_id),
                dinero(0)
            )
        return movimiento.monto if movimiento.pagado_por_id == yo_id else dinero(0)

    def signo(self,m):
        if m.tipo in {"ingreso","deuda"}: return "+"
        if m.tipo=="pago":
            origen=self.movimientos.obtener_por_id(m.movimiento_origen_id)
            return "+" if origen and origen.tipo=="prestamo" else "-"
        return "-"

    def abrir_formulario(self,tipo,movimiento=None):
        if tipo=="pago" and movimiento is None and not self.movimientos.obtener_pendientes_para_pago(): return messagebox.showinfo("Sin pagos pendientes","No existen préstamos ni deudas pendientes por pagar.",parent=self)
        FormMovimiento(self,tipo,movimiento)
    def abrir_personas(self): PersonasWindow(self)
    def abrir_saldos(self): SaldosWindow(self)
    def abrir_categorias(self): CategoriasWindow(self)
    def abrir_movimientos(self): MovimientosWindow(self)
    def abrir_notas(self): NotasWindow(self)
    def abrir_nota(self): NuevaNotaWindow(self)


class PersonasWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.title("Personas"); self.geometry("480x420"); box=ttk.Frame(self,padding=20); box.pack(fill="both",expand=True)
        self.tree=tabla(box,("id","nombre"),{"id":"ID","nombre":"Nombre"}); self.tree.column("id",width=70); self.tree.pack(fill="both",expand=True); buttons=ttk.Frame(box); buttons.pack(fill="x",pady=(12,0))
        for text,cmd in [("Agregar",self.agregar),("Editar",self.editar),("Eliminar",self.eliminar),("Ver saldos",self.saldos)]: ttk.Button(buttons,text=text,command=cmd).pack(side="left",padx=(0,8))
        self.cargar()
    def cargar(self):
        limpiar(self.tree)
        for p in self.app.personas.obtener_todas(): self.tree.insert("","end",iid=str(p.id),values=(p.id,p.nombre))
    def actual(self):
        if not self.tree.selection(): raise ValueError("Selecciona una persona.")
        return self.app.personas.obtener_por_id(int(self.tree.selection()[0]))
    def agregar(self):
        nombre=simpledialog.askstring("Nueva persona","Nombre:",parent=self)
        if nombre:
            try: self.app.personas.crear(Persona(nombre)); self.cargar()
            except Exception as exc: error(self,exc)
    def editar(self):
        try:
            p=self.actual()
            if p.nombre=="Yo": raise ValueError("La persona 'Yo' no puede renombrarse.")
            nombre=simpledialog.askstring("Editar persona","Nombre:",initialvalue=p.nombre,parent=self)
            if nombre: p.nombre=nombre; self.app.personas.actualizar(p); self.cargar()
        except Exception as exc: error(self,exc)
    def eliminar(self):
        try:
            p=self.actual()
            if p.nombre=="Yo": raise ValueError("La persona 'Yo' no puede eliminarse.")
            if messagebox.askyesno("Eliminar",f"¿Eliminar a {p.nombre}?",parent=self): self.app.personas.eliminar(p.id); self.cargar()
        except Exception as exc: error(self,exc)
    def saldos(self):
        SaldosWindow(self.app)


class SaldosWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app); self.title("Saldos por persona"); self.geometry("620x420"); self.transient(app)
        box=ttk.Frame(self,padding=20); box.pack(fill="both",expand=True)
        ttk.Label(box,text="PRÉSTAMOS Y DEUDAS PENDIENTES",style="Subtitle.TLabel").pack(anchor="w",pady=(0,10))
        tree=tabla(box,("nombre","a_favor","debo","neto"),{"nombre":"Persona","a_favor":"Te debe","debo":"Le debes","neto":"Saldo neto"}); tree.pack(fill="both",expand=True)
        for saldo in app.movimientos.obtener_saldos_por_persona():
            neto=saldo["a_favor"]-saldo["debo"]
            tree.insert("","end",values=(saldo["nombre"],f"{saldo['a_favor']:.2f} Bs",f"{saldo['debo']:.2f} Bs",f"{neto:.2f} Bs"))


class CategoriasWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.title("Categorías"); self.geometry("440x400"); box=ttk.Frame(self,padding=20); box.pack(fill="both",expand=True)
        self.tree=tabla(box,("id","nombre"),{"id":"ID","nombre":"Nombre"}); self.tree.pack(fill="both",expand=True); ttk.Button(box,text="Agregar categoría",command=self.agregar).pack(anchor="w",pady=(12,0)); self.cargar()
    def cargar(self):
        limpiar(self.tree)
        for c in self.app.categorias.obtener_todas(): self.tree.insert("","end",values=(c.id,c.nombre))
    def agregar(self):
        name=simpledialog.askstring("Nueva categoría","Nombre:",parent=self)
        if name:
            try: self.app.categorias.crear(Categoria(name)); self.cargar()
            except Exception as exc: error(self,exc)


class MovimientosWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.title("Movimientos"); self.geometry("1080x620"); box=ttk.Frame(self,padding=20); box.pack(fill="both",expand=True)
        filters=ttk.Frame(box); filters.pack(fill="x",pady=(0,12)); self.desde=tk.StringVar(); self.hasta=tk.StringVar(); self.cat=tk.StringVar(value="Todas"); self.persona=tk.StringVar(value="Todas"); self.tipo=tk.StringVar(value="Todos"); self.estado=tk.StringVar(value="Todos"); self.solo_mio=tk.BooleanVar(value=False)
        for label,var in [("Desde",self.desde),("Hasta",self.hasta)]: ttk.Label(filters,text=f"{label} (AAAA-MM-DD)").pack(side="left"); ttk.Entry(filters,textvariable=var,width=13).pack(side="left",padx=(4,12))
        ttk.Combobox(filters,textvariable=self.cat,values=["Todas"]+[c.nombre for c in app.categorias.obtener_todas()],state="readonly",width=18).pack(side="left",padx=(0,12))
        ttk.Label(filters,text="Persona").pack(side="left"); ttk.Combobox(filters,textvariable=self.persona,values=["Todas"]+[p.nombre for p in app.personas.obtener_todas()],state="readonly",width=15).pack(side="left",padx=(4,8))
        ttk.Label(filters,text="Tipo").pack(side="left"); ttk.Combobox(filters,textvariable=self.tipo,values=["Todos","Ingreso","Gasto","Préstamo","Deuda","Pago"],state="readonly",width=12).pack(side="left",padx=(4,8))
        ttk.Label(filters,text="Estado").pack(side="left"); ttk.Combobox(filters,textvariable=self.estado,values=["Todos","Pendientes","Completados"],state="readonly",width=13).pack(side="left",padx=(4,8)); ttk.Checkbutton(filters,text="Solo mi parte",variable=self.solo_mio,command=self.cargar).pack(side="left",padx=(0,8)); ttk.Button(filters,text="Filtrar",command=self.cargar).pack(side="left")
        self.resumen_persona=ttk.Label(box,text="",foreground="#475569"); self.resumen_persona.pack(anchor="w",pady=(0,8))
        self.total_gastos=ttk.Label(box,text="",foreground="#475569"); self.total_gastos.pack(anchor="w",pady=(0,8))
        heads={"id":"ID","fecha":"Fecha","tipo":"Tipo","descripcion":"Descripción","persona":"Persona","categoria":"Categoría","medio":"Medio","monto":"Monto","estado":"Estado"}; self.tree=tabla(box,tuple(heads),heads); self.tree.column("descripcion",width=220); self.tree.pack(fill="both",expand=True)
        buttons=ttk.Frame(box); buttons.pack(fill="x",pady=(12,0)); ttk.Button(buttons,text="Ver distribución",command=self.detalle).pack(side="left"); ttk.Button(buttons,text="Editar",command=self.editar).pack(side="left",padx=8); ttk.Button(buttons,text="Eliminar",command=self.eliminar).pack(side="left",padx=8); ttk.Button(buttons,text="Actualizar",command=self.actualizar).pack(side="right"); self.cargar()
    def actualizar(self):
        self.cargar(); self.app.actualizar_inicio()
    def cargar(self):
        try:
            cats={c.nombre:c.id for c in self.app.categorias.obtener_todas()}; personas_lista=self.app.personas.obtener_todas(); persona_id=next((p.id for p in personas_lista if p.nombre==self.persona.get()),None); tipos={"Ingreso":"ingreso","Gasto":"gasto","Préstamo":"prestamo","Deuda":"deuda","Pago":"pago"}; moves=self.app.movimientos.obtener_filtrados(cats.get(self.cat.get()),self.desde.get().strip() or None,self.hasta.get().strip() or None,persona_id,tipos.get(self.tipo.get())); people={p.id:p.nombre for p in personas_lista}; categories={c.id:c.nombre for c in self.app.categorias.obtener_todas()}; limpiar(self.tree)
            if persona_id:
                saldos=self.app.movimientos.obtener_saldos_por_persona(persona_id); saldo=saldos[0] if saldos else {"a_favor":dinero(0),"debo":dinero(0)}
                self.resumen_persona.configure(text=f"Saldo de {self.persona.get()}: te debe {saldo['a_favor']:.2f} Bs | le debes {saldo['debo']:.2f} Bs")
            else: self.resumen_persona.configure(text="")
            yo=next((p for p in personas_lista if p.nombre=="Yo"),None)
            if self.solo_mio.get():
                if not yo: raise ValueError("No existe la persona 'Yo'.")
                moves=[m for m in moves if m.tipo=="gasto" and self.app.parte_personal(m,yo.id)>0]
            estados={}
            if self.estado.get()!="Todos":
                filtrados=[]
                esperado="pendiente" if self.estado.get()=="Pendientes" else "completado"
                for m in moves:
                    state,saldo=self.app.movimientos.obtener_estado(m); estados[m.id]=(state,saldo)
                    if m.tipo in {"prestamo","deuda"} and state==esperado:
                        filtrados.append(m)
                moves=filtrados
            total_gastos=sumar(self.app.parte_personal(m,yo.id) if self.solo_mio.get() and yo else m.monto for m in moves if m.tipo=="gasto")
            self.total_gastos.configure(text=("Total de mi parte: " if self.solo_mio.get() else "Total de gastos mostrados: ")+f"{total_gastos:.2f} Bs")
            for m in moves:
                state,saldo=estados.get(m.id) or self.app.movimientos.obtener_estado(m); state=self.texto_estado(m,state,saldo); person=people.get(m.persona_id or m.pagado_por_id,"—")
                medio="Efectivo" if m.medio_pago=="efectivo" else "QR / Virtual"
                monto=self.app.parte_personal(m,yo.id) if self.solo_mio.get() and yo and m.tipo=="gasto" else m.monto
                self.tree.insert("","end",iid=str(m.id),values=(m.id,m.fecha,m.tipo.title(),m.descripcion,person,categories.get(m.categoria_id,"—"),medio,f"{self.app.signo(m)}{monto:.2f}",state))
        except Exception as exc: error(self,exc)
    @staticmethod
    def texto_estado(movimiento,state,saldo):
        if movimiento.tipo not in {"prestamo","deuda"}:
            return "—"
        if state=="pendiente":
            return f"Pendiente ({saldo:.2f})"
        return "Completado"
    def actual(self):
        if not self.tree.selection(): raise ValueError("Selecciona un movimiento.")
        return self.app.movimientos.obtener_por_id(int(self.tree.selection()[0]))
    def editar(self):
        try:
            m=self.actual()
            if m.gasto_origen_id: raise ValueError("Este movimiento nació de un gasto compartido. Edita el gasto original.")
            self.app.abrir_formulario(m.tipo,m)
        except Exception as exc: error(self,exc)
    def detalle(self):
        try:
            m=self.actual()
            if m.tipo != "gasto": raise ValueError("La distribución aplica solamente a gastos.")
            DetalleGastoWindow(self.app,m)
        except Exception as exc: error(self,exc)
    def eliminar(self):
        try:
            m=self.actual()
            if messagebox.askyesno("Eliminar",f"¿Eliminar '{m.descripcion}'?",parent=self): self.app.movimientos.eliminar(m.id); self.cargar(); self.app.actualizar_inicio()
        except Exception as exc: error(self,exc)


class DetalleGastoWindow(tk.Toplevel):
    def __init__(self, app, gasto):
        super().__init__(app); self.title("Distribución del gasto"); self.geometry("540x390"); self.transient(app)
        box=ttk.Frame(self,padding=20); box.pack(fill="both",expand=True)
        pagador=app.personas.obtener_por_id(gasto.pagado_por_id)
        ttk.Label(box,text=gasto.descripcion,font=("Arial",15,"bold")).pack(anchor="w")
        ttk.Label(box,text=f"Total: {gasto.monto:.2f} Bs | Pagó: {pagador.nombre if pagador else '—'}",foreground="#475569").pack(anchor="w",pady=(2,14))
        if not gasto.participaciones:
            ttk.Label(box,text="Este gasto no tiene distribución compartida.").pack(anchor="w")
            return
        ttk.Label(box,text="A cada persona le corresponde:",style="Subtitle.TLabel").pack(anchor="w",pady=(0,8))
        tree=tabla(box,("persona","monto"),{"persona":"Persona","monto":"Le corresponde"}); tree.pack(fill="both",expand=True)
        personas={p.id:p.nombre for p in app.personas.obtener_todas()}
        for parte in gasto.participaciones:
            tree.insert("","end",values=(personas.get(parte["persona_id"],"—"),f"{dinero(parte['monto']):.2f} Bs"))
        total=sumar(p["monto"] for p in gasto.participaciones)
        ttk.Label(box,text=f"Total distribuido: {total:.2f} Bs",foreground="#475569").pack(anchor="e",pady=(10,0))


class NotasWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app); self.app = app; self.title("Revisar notas"); self.geometry("930x470")
        box = ttk.Frame(self, padding=20); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Notas por revisar", font=("Arial", 16, "bold")).pack(anchor="w")
        ttk.Label(box, text="No afectan tus saldos hasta que las confirmes.", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 14))
        self.tree = tabla(box, ("id", "nota", "interpretacion", "origen"), {"id":"ID", "nota":"Mensaje / transcripción", "interpretacion":"Propuesta", "origen":"Origen"})
        self.tree.column("id", width=50); self.tree.column("nota", width=360); self.tree.column("interpretacion", width=310); self.tree.pack(fill="both", expand=True)
        buttons = ttk.Frame(box); buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Revisar y confirmar", command=self.revisar).pack(side="left")
        ttk.Button(buttons, text="Descartar", command=self.descartar).pack(side="left", padx=8)
        ttk.Button(buttons, text="Actualizar", command=self.cargar).pack(side="right")
        self.cargar()

    def cargar(self):
        self.notas = self.app.notas.obtener_pendientes(); limpiar(self.tree)
        for nota in self.notas:
            d = nota["datos"]
            propuesta = f"{d['tipo'].title()} · {d['monto']} Bs · {d['descripcion']}"
            origen = "Audio" if nota["audio_path"] else "Mensaje"
            self.tree.insert("", "end", iid=str(nota["id"]), values=(nota["id"], nota["transcripcion"] or nota["texto_original"], propuesta, origen))

    def nota_actual(self):
        if not self.tree.selection(): raise ValueError("Selecciona una nota.")
        return next(n for n in self.notas if n["id"] == int(self.tree.selection()[0]))

    def revisar(self):
        try:
            nota = self.nota_actual()
            FormMovimiento(self.app, nota["datos"]["tipo"], datos=nota["datos"], nota_id=nota["id"], on_success=self.cargar)
        except Exception as exc: error(self, exc)

    def descartar(self):
        try:
            nota = self.nota_actual()
            if messagebox.askyesno("Descartar nota", "La nota no creará ningún movimiento.", parent=self):
                self.app.notas.descartar(nota["id"]); self.cargar()
        except Exception as exc: error(self, exc)


class NuevaNotaWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app); self.app = app; self.audio_path = None; self.title("Nueva nota"); self.geometry("620x390"); self.transient(app)
        box = ttk.Frame(self, padding=20); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Agregar por mensaje o audio", font=("Arial", 16, "bold")).pack(anchor="w")
        ttk.Label(box, text="Por defecto: pagaste tú, por QR/virtual y con fecha de hoy.", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 14))
        self.texto = tk.Text(box, height=8, wrap="word", font=("Arial", 11)); self.texto.pack(fill="both", expand=True)
        line = ttk.Frame(box); line.pack(fill="x", pady=(12, 0))
        ttk.Button(line, text="Adjuntar audio", command=self.adjuntar).pack(side="left")
        ttk.Button(line, text="Grabar 10 s", command=self.grabar).pack(side="left", padx=8)
        self.audio_label = ttk.Label(line, text="Sin audio seleccionado", foreground="#64748b"); self.audio_label.pack(side="left", padx=6)
        ttk.Button(box, text="Enviar a revisar", command=self.enviar).pack(anchor="e", pady=(16, 0))

    def adjuntar(self):
        ruta = filedialog.askopenfilename(parent=self, title="Selecciona un audio", filetypes=[("Audio", "*.mp3 *.m4a *.wav *.ogg *.webm *.mp4"), ("Todos", "*.*")])
        if ruta:
            self.audio_path = ruta; self.audio_label.configure(text=os.path.basename(ruta))

    def grabar(self):
        try:
            import sounddevice
            import soundfile
        except ImportError:
            return error(self, "Para grabar instala las dependencias: python3 -m pip install -r requirements.txt")
        self.audio_label.configure(text="Grabando 10 segundos…")
        def trabajo():
            try:
                descriptor, ruta = tempfile.mkstemp(prefix="mi_app_money_nota-", suffix=".wav")
                os.close(descriptor)
                datos = sounddevice.rec(160000, samplerate=16000, channels=1, dtype="float32")
                sounddevice.wait(); soundfile.write(ruta, datos, 16000)
                self.after(0, lambda: self.audio_listo(ruta))
            except Exception as exc:
                self.after(0, lambda: error(self, f"No se pudo grabar: {exc}"))
        threading.Thread(target=trabajo, daemon=True).start()

    def audio_listo(self, ruta):
        self.audio_path = ruta; self.audio_label.configure(text="Audio grabado: " + os.path.basename(ruta))

    def enviar(self):
        try:
            texto = self.texto.get("1.0", "end").strip()
            transcripcion = None
            if self.audio_path:
                self.audio_label.configure(text="Transcribiendo audio…")
                self.update_idletasks()
                transcripcion = transcribir(self.audio_path)
                if not texto: texto = transcripcion
            datos = interpretar(texto)
            audio_guardado = guardar_audio(self.audio_path) if self.audio_path else None
            self.app.notas.crear(texto, datos, transcripcion, audio_guardado)
            messagebox.showinfo("Nota enviada", "La propuesta está lista en Revisar notas. Tus saldos no cambiaron.", parent=self)
            self.destroy()
        except Exception as exc: error(self, exc)


class FormMovimiento(tk.Toplevel):
    TITLES={"ingreso":"Registrar ingreso","gasto":"Registrar gasto","prestamo":"Registrar préstamo","deuda":"Registrar deuda","pago":"Registrar pago"}
    def __init__(self,app,tipo,mov=None,datos=None,nota_id=None,on_success=None):
        super().__init__(app); self.app,self.tipo,self.mov=app,tipo,mov; self.datos=datos or {}; self.nota_id,self.on_success=nota_id,on_success; self.partes=list(mov.participaciones) if mov else []; self.partes_nombres=list(self.datos.get("participaciones", [])); self.val={}; self.title(("Editar: " if mov else "")+self.TITLES[tipo]); self.transient(app); self.grab_set(); self.ui()
    def ui(self):
        box=ttk.Frame(self,padding=24); box.pack(fill="both",expand=True); ttk.Label(box,text=self.title(),font=("Arial",16,"bold")).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,16)); row=1
        if self.tipo=="pago" and not self.mov:
            row=self.configurar_pago(box,row)
        self.entry(box,"Descripción:","descripcion",self.mov.descripcion if self.mov else self.datos.get("descripcion", ""),row); row+=1; self.entry(box,"Monto (Bs):","monto",f"{self.mov.monto:.2f}" if self.mov else self.datos.get("monto", ""),row); row+=1; self.entry(box,"Fecha:","fecha",self.mov.fecha if self.mov else self.datos.get("fecha", date.today().isoformat()),row); row+=1
        medio_actual="Efectivo" if (self.mov and self.mov.medio_pago=="efectivo") or self.datos.get("medio_pago")=="efectivo" else "QR / Virtual"; self.combo(box,"Medio:","medio_pago",["QR / Virtual","Efectivo"],row,medio_actual); row+=1
        if self.tipo in {"ingreso","gasto"}:
            cats=self.app.categorias.obtener_todas(); self.val["cats"]=cats; selected=next((c.nombre for c in cats if self.mov and c.id==self.mov.categoria_id),self.datos.get("categoria", cats[0].nombre if cats else "")); self.combo(box,"Categoría:","categoria",[c.nombre for c in cats],row,selected); row+=1
        if self.tipo in {"gasto","prestamo","deuda"}:
            people=self.app.personas.obtener_todas(); self.val["people"]=people; pid=self.mov.pagado_por_id if self.mov and self.tipo=="gasto" else (self.mov.persona_id if self.mov else None); selected=next((p.nombre for p in people if p.id==pid),self.datos.get("pagado_por", people[0].nombre if people else "")); self.combo(box,"Pagó:" if self.tipo=="gasto" else "Persona:","persona",[p.nombre for p in people],row,selected)
            if self.tipo in {"prestamo","deuda"}: ttk.Button(box,text="+ Nueva persona",command=self.nueva_persona).grid(row=row,column=2,padx=(8,0))
            row+=1
        if self.tipo=="gasto": self.part_label=ttk.Label(box,text=self.part_text(),foreground="#64748b"); self.part_label.grid(row=row,column=0,sticky="w"); ttk.Button(box,text="Distribuir gasto",command=self.distribuir).grid(row=row,column=1,sticky="e"); row+=1
        ttk.Button(box,text="Confirmar movimiento" if self.nota_id else "Guardar",command=self.guardar).grid(row=row,column=1,sticky="e",pady=(20,0))
    def entry(self,p,label,key,value,row):
        ttk.Label(p,text=label).grid(row=row,column=0,sticky="w",padx=(0,16),pady=6); self.val[key]=tk.StringVar(value=value); ttk.Entry(p,textvariable=self.val[key],width=38).grid(row=row,column=1,pady=6)
    def combo(self,p,label,key,values,row,selected=None):
        ttk.Label(p,text=label).grid(row=row,column=0,sticky="w",padx=(0,16),pady=6); self.val[key]=tk.StringVar(value=selected or (values[0] if values else "")); combo=ttk.Combobox(p,textvariable=self.val[key],values=values,state="readonly",width=35); combo.grid(row=row,column=1,pady=6); self.val[f"{key}_combo"]=combo
    def configurar_pago(self,box,row):
        pending=self.app.movimientos.obtener_pendientes_para_pago(); self.val["pending"]=pending
        personas={p.id:p for p in self.app.personas.obtener_todas()}
        personas_pendientes=sorted({personas[m.persona_id].nombre for m,_ in pending if m.persona_id in personas})
        self.combo(box,"Persona:","pago_persona",["Todas"]+personas_pendientes,row); self.val["pago_persona_combo"].bind("<<ComboboxSelected>>",self.actualizar_pagos); row+=1
        self.combo(box,"Pagar:","origen",[],row); self.actualizar_pagos(); return row+1
    def texto_pago(self,movimiento,saldo):
        return f"{movimiento.id} | {movimiento.tipo.title()} | {self.nombre_persona(movimiento.persona_id)} | saldo {saldo:.2f} Bs"
    def pagos_filtrados(self):
        persona=self.val["pago_persona"].get()
        return [(m,s) for m,s in self.val["pending"] if persona=="Todas" or self.nombre_persona(m.persona_id)==persona]
    def actualizar_pagos(self,event=None):
        valores=[self.texto_pago(m,s) for m,s in self.pagos_filtrados()]
        self.val["origen_combo"].configure(values=valores)
        if self.val["origen"].get() not in valores:
            self.val["origen"].set(valores[0] if valores else "")
    def person(self): return next(p for p in self.val["people"] if p.nombre==self.val["persona"].get())
    def nueva_persona(self):
        nombre=simpledialog.askstring("Nueva persona","Nombre:",parent=self)
        if not nombre: return
        try:
            persona=self.app.personas.crear(Persona(nombre))
            self.val["people"].append(persona); self.val["persona"].set(persona.nombre)
            self.ui_actualizar_personas()
        except Exception as exc: error(self,exc)
    def ui_actualizar_personas(self):
        self.val["persona_combo"].configure(values=[p.nombre for p in self.val["people"]])
    def nombre_persona(self, persona_id):
        persona=self.app.personas.obtener_por_id(persona_id)
        return persona.nombre if persona else "Sin persona"
    def category(self): return next(c for c in self.val["cats"] if c.nombre==self.val["categoria"].get())
    def part_text(self):
        if self.partes: return f"Distribuido: {sumar(p['monto'] for p in self.partes):.2f} Bs ({len(self.partes)} personas)"
        if self.partes_nombres: return "Distribución propuesta: " + ", ".join(f"{p['nombre']} {p['monto']} Bs" for p in self.partes_nombres)
        return "Sin distribución compartida."
    def distribuir(self):
        try: DistribucionWindow(self,dinero(self.val["monto"].get()))
        except Exception as exc: error(self,exc)
    def guardar(self):
        try:
            data={"id":self.mov.id if self.mov else None,"tipo":self.tipo,"descripcion":self.val["descripcion"].get(),"monto":self.val["monto"].get(),"fecha":self.val["fecha"].get(),"medio_pago":"efectivo" if self.val["medio_pago"].get()=="Efectivo" else "virtual"}
            if self.tipo=="ingreso": data.update(persona_id=next(p.id for p in self.app.personas.obtener_todas() if p.nombre=="Yo"),categoria_id=self.category().id)
            elif self.tipo=="gasto": data.update(pagado_por_id=self.person().id,categoria_id=self.category().id)
            elif self.tipo in {"prestamo","deuda"}: data["persona_id"]=self.person().id
            elif self.mov: data.update(persona_id=self.mov.persona_id,movimiento_origen_id=self.mov.movimiento_origen_id)
            else:
                if not self.val["origen"].get(): raise ValueError("No hay pagos pendientes para esa persona.")
                source=next(x for x in self.val["pending"] if x[0].id==int(self.val["origen"].get().split(" | ")[0]))[0]; data.update(persona_id=source.persona_id,movimiento_origen_id=source.id)
            m=Movimiento(**data)
            if self.partes:
                m.participaciones=self.partes
            elif self.partes_nombres:
                existentes={p.nombre.casefold():p for p in self.app.personas.obtener_todas()}
                m.participaciones=[]
                for parte in self.partes_nombres:
                    persona=existentes.get(parte["nombre"].casefold())
                    if not persona:
                        persona=self.app.personas.crear(Persona(parte["nombre"])); existentes[persona.nombre.casefold()]=persona
                    m.participaciones.append({"persona_id":persona.id,"monto":parte["monto"]})
            if self.mov: self.app.movimientos.actualizar(m)
            else: self.app.movimientos.crear(m)
            if self.nota_id: self.app.notas.confirmar(self.nota_id)
            self.app.actualizar_inicio()
            if self.on_success: self.on_success()
            self.destroy()
        except Exception as exc: error(self,exc)


class DistribucionWindow(tk.Toplevel):
    def __init__(self,form,total):
        super().__init__(form); self.form,self.total=form,total; self.title("Distribuir gasto"); self.transient(form); self.grab_set(); box=ttk.Frame(self,padding=20); box.pack(fill="both",expand=True); ttk.Label(box,text=f"Total a distribuir: {total:.2f} Bs").pack(anchor="w")
        line=ttk.Frame(box); line.pack(fill="x",pady=10); self.person=tk.StringVar(); self.amount=tk.StringVar(); self.personas_combo=ttk.Combobox(line,textvariable=self.person,values=[p.nombre for p in form.app.personas.obtener_todas()],state="readonly",width=22); self.personas_combo.pack(side="left"); ttk.Button(line,text="+ Persona",command=self.nueva_persona).pack(side="left",padx=(6,0)); ttk.Entry(line,textvariable=self.amount,width=12).pack(side="left",padx=8); ttk.Button(line,text="Agregar / cambiar",command=self.add).pack(side="left")
        self.tree=tabla(box,("name","amount"),{"name":"Persona","amount":"Monto"}); self.tree.pack(fill="both",expand=True); buttons=ttk.Frame(box); buttons.pack(fill="x",pady=(10,0)); ttk.Button(buttons,text="Quitar",command=self.remove).pack(side="left"); ttk.Button(buttons,text="Listo",command=self.done).pack(side="right"); self.load()
    def load(self):
        limpiar(self.tree); names={p.id:p.nombre for p in self.form.app.personas.obtener_todas()}
        for part in self.form.partes: self.tree.insert("","end",iid=str(part["persona_id"]),values=(names.get(part["persona_id"],"—"),f"{dinero(part['monto']):.2f}"))
    def add(self):
        try:
            p=next(p for p in self.form.app.personas.obtener_todas() if p.nombre==self.person.get()); amount=dinero(self.amount.get()); parts=[x for x in self.form.partes if x["persona_id"]!=p.id]+[{"persona_id":p.id,"monto":amount}]
            if sumar(x["monto"] for x in parts)>self.total: raise ValueError("La distribución supera el total.")
            self.form.partes=parts; self.amount.set(""); self.load()
        except Exception as exc: error(self,exc)
    def nueva_persona(self):
        nombre=simpledialog.askstring("Nueva persona","Nombre:",parent=self)
        if not nombre:
            return
        try:
            persona=self.form.app.personas.crear(Persona(nombre))
            self.personas_combo.configure(values=[p.nombre for p in self.form.app.personas.obtener_todas()])
            self.person.set(persona.nombre)
        except Exception as exc:
            error(self,exc)
    def remove(self):
        if self.tree.selection(): self.form.partes=[x for x in self.form.partes if x["persona_id"]!=int(self.tree.selection()[0])]; self.load()
    def done(self):
        if self.form.partes and sumar(x["monto"] for x in self.form.partes)!=self.total: return error(self,"La distribución debe sumar exactamente el total.")
        self.form.part_label.configure(text=self.form.part_text()); self.destroy()
