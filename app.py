import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from importers.csv_importer import load_players
from engine.team_analyzer import TeamAnalyzer
from engine.optimizers.lineup_optimizer import LineupOptimizer
from engine.optimizers.formation_optimizer import FormationOptimizer
from engine.analyzers.team_rater import TeamRater
from engine.analyzers.formation_analyzer import FormationAnalyzer
from engine.opponents.opponent_manager import OpponentManager
from models.opponent import Opponent
from models.formations import FORMATIONS
from models.team_ratings import TeamRatings



OPPONENT_RATING_FIELDS = [
    ('Def. Izq.','left_defense',25),
    ('Def. Central','central_defense',35),
    ('Def. Der.','right_defense',24),
    ('Mediocampo','midfield',40),
    ('Ataque Izq.','left_attack',25),
    ('Ataque Central','central_attack',30),
    ('Ataque Der.','right_attack',24)
]


class HTCoachApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('HT COACH')
        self.geometry('1180x760')
        self.minsize(980, 650)
        self.players = []
        self.opponent_manager = OpponentManager(
            os.path.join(os.getcwd(), 'database', 'opponents.json')
        )
        self.csv_path = tk.StringVar(value=os.path.join(os.getcwd(), 'players.csv'))
        self.status = tk.StringVar(value='Listo')
        self.selected_opponent = tk.StringVar()
        self._build_ui()
        if os.path.exists(self.csv_path.get()):
            self.load_csv()
        self.refresh_opponents()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10); top.pack(fill='x')
        ttk.Label(top, text='HT COACH', font=('Segoe UI', 20, 'bold')).pack(side='left')
        ttk.Entry(top, textvariable=self.csv_path, width=70).pack(side='left', padx=(20, 5), fill='x', expand=True)
        ttk.Button(top, text='Buscar CSV', command=self.browse_csv).pack(side='left', padx=3)
        ttk.Button(top, text='Cargar', command=self.load_csv).pack(side='left', padx=3)

        self.tabs = ttk.Notebook(self); self.tabs.pack(fill='both', expand=True, padx=10, pady=(0,10))
        self._players_tab(); self._formation_tab(); self._opponents_tab(); self._matchup_tab(); self._model_tab()
        ttk.Label(self, textvariable=self.status, relief='sunken', anchor='w').pack(fill='x', side='bottom')

    def _text(self, parent):
        f=ttk.Frame(parent); f.pack(fill='both', expand=True, padx=8, pady=8)
        t=tk.Text(f, wrap='none', font=('Consolas', 10)); t.pack(side='left', fill='both', expand=True)
        y=ttk.Scrollbar(f, orient='vertical', command=t.yview); y.pack(side='right', fill='y'); t.configure(yscrollcommand=y.set)
        return t

    def _players_tab(self):
        tab=ttk.Frame(self.tabs); self.tabs.add(tab, text='Plantel')
        self.players_text=self._text(tab)

    def _formation_tab(self):
        tab=ttk.Frame(self.tabs); self.tabs.add(tab, text='Formaciones / Mejor XI')
        bar=ttk.Frame(tab, padding=8); bar.pack(fill='x')
        ttk.Button(bar, text='Analizar todas las formaciones', command=self.analyze_formations).pack(side='left')
        self.formation_text=self._text(tab)

    def _opponents_tab(self):
        tab=ttk.Frame(self.tabs); self.tabs.add(tab, text='Rivales')
        self.opponents_tab=tab

        main=ttk.Frame(tab, padding=8); main.pack(fill='both', expand=True)

        left=ttk.LabelFrame(main, text='Rivales guardados', padding=8)
        left.pack(side='left', fill='y', padx=(0,8))
        self.opponent_list=tk.Listbox(left, height=18, width=32)
        self.opponent_list.pack(fill='y', expand=False)
        self.opponent_list.bind('<<ListboxSelect>>',lambda event:self.load_opponent_from_list())

        right=ttk.LabelFrame(main, text='Datos del rival', padding=8)
        right.pack(side='left', fill='both', expand=True)
        ttk.Label(right,text='Nombre').grid(row=0,column=0,sticky='w',pady=(0,6))
        self.opponent_name=tk.StringVar()
        ttk.Entry(right,textvariable=self.opponent_name,width=40).grid(row=0,column=1,sticky='w',pady=(0,6))

        self.opponent_vars={}
        for i,(label,key,val) in enumerate(self._opponent_fields()):
            row=(i//2)+1
            column=(i%2)*2
            ttk.Label(right,text=label).grid(row=row,column=column,sticky='w',padx=(0,6),pady=4)
            v=tk.StringVar(value=str(val)); self.opponent_vars[key]=v
            ttk.Entry(right,textvariable=v,width=12).grid(row=row,column=column+1,sticky='w',pady=4)

        buttons=ttk.Frame(right); buttons.grid(row=5,column=0,columnspan=4,sticky='w',pady=(12,0))
        ttk.Button(buttons,text='Nuevo',command=self.new_opponent).pack(side='left',padx=(0,4))
        ttk.Button(buttons,text='Guardar',command=self.save_opponent).pack(side='left',padx=4)
        ttk.Button(buttons,text='Eliminar',command=self.delete_opponent).pack(side='left',padx=4)
        ttk.Button(buttons,text='Usar en analisis',command=self.use_opponent_in_matchup).pack(side='left',padx=4)

    def _matchup_tab(self):
        tab=ttk.Frame(self.tabs); self.tabs.add(tab, text='Análisis contra rival')
        self.matchup_tab=tab
        selector=ttk.LabelFrame(tab, text='Rival guardado', padding=8); selector.pack(fill='x', padx=8, pady=8)
        ttk.Label(selector,text='Rival').pack(side='left')
        self.matchup_opponent_combo=ttk.Combobox(selector,textvariable=self.selected_opponent,state='readonly',width=35)
        self.matchup_opponent_combo.pack(side='left', padx=6)
        self.matchup_opponent_combo.bind('<<ComboboxSelected>>',lambda event:self.load_selected_opponent())
        ttk.Button(selector,text='Usar rival',command=self.load_selected_opponent).pack(side='left', padx=3)
        ttk.Button(selector,text='Gestionar rivales',command=lambda:self.tabs.select(self.opponents_tab)).pack(side='left', padx=3)

        box=ttk.LabelFrame(tab, text='Ratings del rival', padding=8); box.pack(fill='x', padx=8, pady=8)
        fields=self._opponent_fields()
        self.opp_vars={}
        for i,(label,key,val) in enumerate(fields):
            ttk.Label(box,text=label).grid(row=0,column=i,padx=3)
            v=tk.StringVar(value=str(val)); self.opp_vars[key]=v
            ttk.Entry(box,textvariable=v,width=11).grid(row=1,column=i,padx=3)
        ttk.Button(box,text='Optimizar XI + órdenes + táctica',command=self.run_matchup).grid(row=2,column=0,columnspan=len(fields),pady=(10,0))
        self.matchup_text=self._text(tab)

    def _model_tab(self):
        tab=ttk.Frame(self.tabs); self.tabs.add(tab, text='Modelo / Diagnóstico')
        self.model_text=self._text(tab)
        self.model_text.insert('end','HT COACH usa un modelo configurable de ocasiones, conversión, tácticas y probabilidades.\n\nEjecutá run_tests.bat para validar el motor completo.\n')

    def _opponent_fields(self):
        return OPPONENT_RATING_FIELDS

    def _default_opponent_ratings(self):
        return TeamRatings(
            **{
                key: value
                for _, key, value in self._opponent_fields()
            }
        )

    def browse_csv(self):
        p=filedialog.askopenfilename(filetypes=[('CSV','*.csv'),('Todos','*.*')])
        if p: self.csv_path.set(p)

    def load_csv(self):
        try:
            self.players=load_players(self.csv_path.get())
            self.players_text.delete('1.0','end')
            self.players_text.insert('end',f'Jugadores cargados: {len(self.players)}\n\n')
            for p in sorted(self.players,key=lambda x:x.tsi,reverse=True):
                self.players_text.insert('end',f'{p.name:<35} Edad {p.age:>2}  Forma {p.form:>2}  TSI {p.tsi:>8}\n')
            self.status.set(f'{len(self.players)} jugadores cargados')
        except Exception as e: messagebox.showerror('Error al cargar CSV',str(e))

    def _need_players(self):
        if not self.players: messagebox.showwarning('HT COACH','Primero cargá un archivo CSV de jugadores.'); return False
        return True

    def refresh_opponents(self):
        opponents=self.opponent_manager.list_opponents()
        names=[opponent.name for opponent in opponents]
        if hasattr(self,'opponent_list'):
            self.opponent_list.delete(0,'end')
            for name in names:
                self.opponent_list.insert('end',name)
        if hasattr(self,'matchup_opponent_combo'):
            self.matchup_opponent_combo['values']=names
            if self.selected_opponent.get() not in names:
                self.selected_opponent.set(names[0] if names else '')

    def _read_opponent_ratings(self, vars_by_key):
        return TeamRatings(**{k:float(v.get()) for k,v in vars_by_key.items()})

    def _write_opponent_ratings(self, vars_by_key, ratings):
        for key,var in vars_by_key.items():
            var.set(str(getattr(ratings,key)))

    def new_opponent(self):
        self.opponent_name.set('')
        self._write_opponent_ratings(
            self.opponent_vars,
            self._default_opponent_ratings()
        )

    def load_opponent_from_list(self):
        selection=self.opponent_list.curselection()
        if not selection:
            return
        name=self.opponent_list.get(selection[0])
        opponent=self.opponent_manager.get(name)
        if not opponent:
            return
        self.opponent_name.set(opponent.name)
        self._write_opponent_ratings(self.opponent_vars,opponent.ratings)

    def save_opponent(self):
        try:
            opponent=Opponent(
                name=self.opponent_name.get(),
                ratings=self._read_opponent_ratings(self.opponent_vars)
            )
            saved=self.opponent_manager.save(opponent)
            self.selected_opponent.set(saved.name)
            self.refresh_opponents()
            self.status.set(f'Rival guardado: {saved.name}')
        except ValueError as e:
            messagebox.showerror('Error al guardar rival',str(e))

    def delete_opponent(self):
        name=self.opponent_name.get() or self.selected_opponent.get()
        if not name:
            messagebox.showwarning('HT COACH','Selecciona un rival para eliminar.')
            return
        if not messagebox.askyesno('Eliminar rival',f'Eliminar {name}?'):
            return
        deleted=self.opponent_manager.delete(name)
        if deleted:
            self.new_opponent()
            self.refresh_opponents()
            self.status.set(f'Rival eliminado: {name}')

    def use_opponent_in_matchup(self):
        name=self.opponent_name.get()
        if not name:
            messagebox.showwarning('HT COACH','Selecciona o guarda un rival primero.')
            return
        opponent=self.opponent_manager.get(name)
        if opponent is None:
            try:
                opponent=self.opponent_manager.save(
                    Opponent(
                        name=name,
                        ratings=self._read_opponent_ratings(self.opponent_vars)
                    )
                )
                self.refresh_opponents()
            except ValueError as e:
                messagebox.showerror('Error al usar rival',str(e))
                return
        self.selected_opponent.set(opponent.name)
        self._write_opponent_ratings(self.opp_vars,opponent.ratings)
        self.tabs.select(self.matchup_tab)
        self.status.set(f'Rival activo: {opponent.name}')

    def load_selected_opponent(self):
        opponent=self.opponent_manager.get(self.selected_opponent.get())
        if not opponent:
            return
        self._write_opponent_ratings(self.opp_vars,opponent.ratings)
        self.status.set(f'Rival activo: {opponent.name}')

    def analyze_formations(self):
        if not self._need_players(): return
        self.status.set('Analizando formaciones...'); self.update_idletasks()
        try:
            results=FormationOptimizer.optimize(self.players,FORMATIONS)
            out=['COMPARACIÓN DE FORMACIONES','='*90]
            for formation,lineup,ratings,score in results:
                out += ['',f'{formation.name}  SCORE: {score:.2f}',f'MID: {ratings.midfield:.2f} | DEF: {ratings.left_defense:.2f}/{ratings.central_defense:.2f}/{ratings.right_defense:.2f} | ATT: {ratings.left_attack:.2f}/{ratings.central_attack:.2f}/{ratings.right_attack:.2f}','MEJOR XI:']
                out += [f'  {lp.position.value:<24} {lp.player.name}' for lp in lineup.players]
            self.formation_text.delete('1.0','end'); self.formation_text.insert('end','\n'.join(out)); self.status.set('Análisis de formaciones terminado')
        except Exception as e: messagebox.showerror('Error',str(e)); self.status.set('Error')

    def run_matchup(self):
        if not self._need_players(): return
        try: opponent=self._read_opponent_ratings(self.opp_vars)
        except ValueError: messagebox.showerror('Error','Todos los ratings del rival deben ser números.'); return
        self.status.set('Optimizando contra rival... puede tardar unos minutos')
        self.matchup_text.delete('1.0','end'); self.matchup_text.insert('end','Procesando...\n')
        threading.Thread(target=self._matchup_worker,args=(opponent,),daemon=True).start()

    def _matchup_worker(self, opponent):
        try:
            results=FormationOptimizer.optimize_against(self.players,FORMATIONS,opponent)
            out=['RESULTADO CONTRA RIVAL','='*100]
            for r in results:
                out += ['',f'FORMACIÓN {r.formation.name}',f'Win {r.probabilities.win*100:.2f}% | Draw {r.probabilities.draw*100:.2f}% | Loss {r.probabilities.loss*100:.2f}%',f'Táctica: {r.tactic.value} (nivel {r.tactic_level:.2f})',f'Posesión {r.match_evaluation.possession*100:.2f}% | xG {r.match_evaluation.expected_goals:.2f} | Opp xG {r.match_evaluation.opponent_expected_goals:.2f}',f'Baseline {r.baseline_win_probability*100:.2f}% | Mejor XI normal {r.best_normal_win_probability*100:.2f}% | Órdenes {r.best_order_win_probability*100:.2f}%','XI + ÓRDENES:']
                out += [f'  {lp.position.value:<24} {getattr(lp.order,"value",str(lp.order)):<20} {lp.player.name}' for lp in r.lineup.players]
            text='\n'.join(out)
            self.after(0,lambda:(self.matchup_text.delete('1.0','end'),self.matchup_text.insert('end',text),self.status.set('Optimización terminada')))
        except Exception as e:
            self.after(0,lambda:messagebox.showerror('Error durante la optimización',str(e)))
            self.after(0,lambda:self.status.set('Error'))

if __name__=='__main__': HTCoachApp().mainloop()
