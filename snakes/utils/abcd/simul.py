import math, operator, collections
import Tkinter as tk
import tkMessageBox as popup
try :
    import Tkinter.scrolledtext as ScrolledText
except ImportError :
    import ScrolledText

class Action (object) :
    def __init__ (self, trans, mode, shift) :
        self.trans = trans
        self.mode = mode
        self.net = trans.net
        self.pre = self.net.get_marking()
        self.post = None
        srow, scol, erow, ecol = trans.label("srcloc")
        self.start = "%s.%s" % (srow, scol + shift)
        self.stop = "%s.%s" % (erow, ecol + shift)
        self.line = srow
    def fire (self) :
        self.trans.fire(self.mode)
        self.post = self.net.get_marking()
    def __eq__ (self, other) :
        try :
            return (self.trans == other.trans and self.mode == other.mode
                    and self.net == other.net)
        except AttributeError :
            return False

class Trace (object) :
    def __init__ (self, net) :
        self.net = net
        self.actions = []
    def add (self, action) :
        self.actions.append(action)
    def back (self) :
        self.net.set_marking(self.actions[-1].pre)
        self.actions.pop()
    def empty (self) :
        return not self.actions
    def __getitem__ (self, idx) :
        return self.actions[idx]
    def __len__ (self) :
        return len(self.actions)

class Simulator (object) :
    def __init__ (self, snk, src, net, trace=None, errline=None) :
        self.snk = snk
        self.src = src
        self.net = net
        self.srclength = len(src.splitlines())
        self.width = int(math.ceil(math.log10(self.srclength)))
        self.shift = self.width + 2
        self.modes = []
        self.trans2modes = collections.defaultdict(set)
        self.trace = Trace(self.net)
        self.build_gui(errline)
        if trace is not None :
            for trans, mode in trace :
                trans = self.net.transition(trans.name)
                action = Action(trans, mode, self.shift)
                action.fire()
                self.extend_trace(action)
                self.trace.add(action)
        self.update()
        if trace :
            self._back.configure(state=tk.NORMAL)
    def update (self) :
        self.update_modes()
        self.update_state()
    def build_gui (self, errline) :
        self._win = tk.Tk()
        self._win.title("ABCD simulator")
        self._win.bind("<Return>", self.fire)
        self._win.bind("<BackSpace>", self.back)
        self._win.bind("<Escape>", self.quit)
        # paned windows and frames
        self._pan_main = tk.PanedWindow(self._win, orient=tk.HORIZONTAL)
        self._pan_main.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self.__pan_left = tk.PanedWindow(self._pan_main, orient=tk.VERTICAL)
        self._pan_main.add(self.__pan_left)
        self._pan_right = tk.PanedWindow(self._pan_main, orient=tk.VERTICAL)
        self._pan_main.add(self._pan_right)
        self._modes_frame = tk.Frame(self.__pan_left)
        self.__pan_left.add(self._modes_frame)
        self._trace_frame = tk.Frame(self.__pan_left)
        self.__pan_left.add(self._trace_frame)
        self._state_frame = tk.Frame(self._pan_right)
        self._pan_right.add(self._state_frame)
        # modes
        self._modes_x = tk.Scrollbar (self._modes_frame,
                                      orient=tk.HORIZONTAL)
        self._modes_x.grid(row=1, column=0, sticky=tk.W+tk.E)
        self._modes_y = tk.Scrollbar (self._modes_frame, orient=tk.VERTICAL)
        self._modes_y.grid(row=0, column=1, sticky=tk.N+tk.S)
        self._modes = tk.Listbox(self._modes_frame,
                                 xscrollcommand=self._modes_x.set,
                                 yscrollcommand=self._modes_y.set,
                                 width=50,
                                 font="monospace",
                                 activestyle="none",
                                 selectbackground="green",
                                 selectborderwidth=0,
                                 highlightthickness=0,
                                 selectmode=tk.SINGLE,
                                 disabledforeground="black")
        self._modes.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self._modes_x["command"] = self._modes.xview
        self._modes_y["command"] = self._modes.yview
        self._modes.bind("<Button-1>", self.select_mode)
        self._modes.bind("<Double-Button-1>", self.select_mode_fire)
        # fire button
        self._fire = tk.Button(self._modes_frame,
                               text="Fire",
                               command=self.fire,
                               state=tk.DISABLED)
        self._fire.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E)
        # back button
        self._back = tk.Button(self._modes_frame,
                               text="Undo last action",
                               command=self.back,
                               state=tk.DISABLED)
        self._back.grid(row=3, column=0, columnspan=2, sticky=tk.W+tk.E)
        # resume button
        self._resume = tk.Button(self._modes_frame,
                                 text="Resume simulation",
                                 command=self.resume,
                                 state=tk.DISABLED)
        self._resume.grid(row=4, column=0, columnspan=2, sticky=tk.W+tk.E)
        # traces
        self._trace_x = tk.Scrollbar (self._trace_frame,
                                      orient=tk.HORIZONTAL)
        self._trace_x.grid(row=1, column=0, sticky=tk.W+tk.E)
        self._trace_y = tk.Scrollbar (self._trace_frame, orient=tk.VERTICAL)
        self._trace_y.grid(row=0, column=1, sticky=tk.N+tk.S)
        self._trace = tk.Listbox(self._trace_frame,
                                 font="monospace",
                                 width=50,
                                 activestyle="none",
                                 selectbackground="blue",
                                 xscrollcommand=self._trace_x.set,
                                 yscrollcommand=self._trace_y.set,
                                 disabledforeground="black")
        self._trace.grid(row=0, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
        self._trace_x["command"] = self._trace.xview
        self._trace_y["command"] = self._trace.yview
        self._trace.bind("<Button-1>", self.select_trace)
        self._trace.insert(tk.END, "<init>")
        # save trace button
        # self._save = tk.Button(self._trace_frame,
        #                        text="Save trace",
        #                        command=self.save)
        # self._save.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E)
        # source
        self._source = ScrolledText.ScrolledText(self._pan_right,
                                                 font="monospace",
                                                 width=70,
                                                 height=min([self.srclength,
                                                             25]))
        self._pan_right.add(self._source)
        self._source.tag_config("linenum",
                                background="#eee",
                                foreground="#222")
        for num, line in enumerate(self.src.splitlines()) :
            if num :
                self._source.insert(tk.END, "\n")
            self._source.insert(tk.END, "%s: %s"
                                % (str(num+1).rjust(self.width), line))
            self._source.tag_add("linenum",
                                 "%s.0" % (num+1),
                                 "%s.%s" % (num+1, self.width+1))
        self._source.configure(state=tk.DISABLED)
        if errline is not None :
            self._source.tag_add("error",
                                "%s.%s" % (errline, self.shift),
                                "%s.end" % errline)
            self._source.tag_config("error", background="red")
        # states
        self._state = ScrolledText.ScrolledText(self._pan_right,
                                                font="monospace",
                                                width=70,
                                                state=tk.DISABLED,
                                                height=10)
        self._pan_right.add(self._state)
        # setup cells expansion
        for widget in (self._win.winfo_toplevel(), self._win,
                       self._modes_frame, self._trace_frame) :
            widget.rowconfigure(0, weight=1)
            widget.columnconfigure(0, weight=1)
        # tag places and transitions
        for place in self.net.place() :
            if place.status not in (self.snk.entry, self.snk.internal,
                                    self.snk.exit) :
                srow, scol, erow, ecol = place.label("srcloc")
                self._source.tag_add(place.name,
                                     "%s.%s" % (srow, scol + self.shift),
                                     "%s.%s" % (erow, ecol + self.shift))
                self.buffer_bind(self._source, place.name)
        for trans in self.net.transition() :
            srow, scol, erow, ecol = trans.label("srcloc")
            self._source.tag_add(trans.name,
                                 "%s.%s" % (srow, scol + self.shift),
                                 "%s.%s" % (erow, ecol + self.shift))
            self.trans_bind(trans.name)
    def trans_bind (self, tag) :
        def trans_enter (evt) :
            self.trans_enter(tag)
        self._source.tag_bind(tag, "<Enter>", trans_enter)
        def trans_leave (evt) :
            self.trans_leave(tag)
        self._source.tag_bind(tag, "<Leave>", trans_leave)
    def buffer_bind (self, widget, tag) :
        def buffer_enter (evt) :
            self.buffer_enter(tag)
        widget.tag_bind(tag, "<Enter>", buffer_enter)
        def buffer_leave (evt) :
            self.buffer_leave(tag)
        widget.tag_bind(tag, "<Leave>", buffer_leave)
    def run (self) :
        self._win.mainloop()
    def update_modes (self) :
        self._modes.delete(0, tk.END)
        self.modes = []
        self.selected_mode = None
        self.trans2modes = collections.defaultdict(set)
        for trans in self.net.transition() :
            self._source.tag_config(trans.name, background="white")
            for mode in trans.modes() :
                self.modes.append(Action(trans, mode, self.shift))
        self.modes.sort(key=operator.attrgetter("line"))
        for idx, action in enumerate(self.modes) :
            self.trans2modes[action.trans.name].add(idx)
            self._modes.insert(tk.END, "%s @ %s"
                               % (action.mode, action.trans.name))
            self._source.tag_config(action.trans.name, background="yellow")
            self._source.tag_raise(action.trans.name)
        if not self.modes :
            self._fire.configure(state=tk.DISABLED)
    def fire (self, evt=None) :
        if evt is not None :
            self._fire.flash()
        action = self.modes[self.selected_mode]
        action.fire()
        self.trace.add(action)
        self.extend_trace(action)
        self.update()
        self._fire.configure(state=tk.DISABLED)
        self._back.configure(state=tk.NORMAL)
    def extend_trace (self, action) :
        self._trace.insert(tk.END, "%s @ %s"
                           % (action.mode, action.trans.name))
        self._trace.see(self._trace.size()-1)
    def trans_enter (self, trans) :
        if trans in self.trans2modes :
            state = self._modes["state"]
            self._modes.configure(state=tk.NORMAL)
            for idx in self.trans2modes[trans] :
                self._modes.itemconfig(idx,
                                       background="orange",
                                       selectbackground="orange")
                self._modes.see(idx)
            self._source.tag_config(trans, background="orange")
            self._modes.configure(state=state)
    def trans_leave (self, trans) :
        if trans in self.trans2modes :
            state = self._modes["state"]
            self._modes.configure(state=tk.NORMAL)
            for idx in self.trans2modes[trans] :
                self._modes.itemconfig(idx,
                                       background="white",
                                       selectbackground="green")
            if self.selected_mode in self.trans2modes[trans] :
                self._source.tag_config(trans, background="green")
            else :
                self._source.tag_config(trans, background="yellow")
            self._modes.configure(state=state)
    def select_mode (self, evt) :
        if not self.modes or self._modes["state"] == "disabled" :
            return
        if isinstance(evt, int) :
            idx = evt
        else :
            idx = self._modes.nearest(evt.y)
        for num in range(len(self.modes)) :
            self._source.tag_config(self.modes[num].trans.name,
                                    background="yellow")
        self._source.tag_config(self.modes[idx].trans.name,
                                background="green")
        self.selected_mode = idx
        self._fire.configure(state=tk.NORMAL)
    def select_mode_fire (self, evt) :
        if self.modes  or self._modes["state"] == "disabled" :
            self.select_mode(evt)
            self.fire(evt)
    def back (self, evt=None) :
        if evt is not None :
            self._back.flash()
        self.trace.back()
        self._trace.delete(self._trace.size()-1)
        if self._trace.curselection() :
            last = self._trace.size() - 1
            self._trace.selection_clear(0, last)
            self._trace.see(last)
        self.update()
        if self.trace.empty() :
            self._back.configure(state=tk.DISABLED)
    def save (self, evt=None) :
        if evt is not None :
            self._save.flash()
    def update_state (self) :
        self._state.configure(state=tk.NORMAL)
        self._state.delete("1.0", tk.END)
        pos = 1
        for place in self.net.place() :
            if place.status not in (self.snk.entry, self.snk.internal,
                                    self.snk.exit) :
                self._state.insert(tk.END, "%s = %s\n"
                                   % (place.name, place.tokens))
                self._state.tag_add(place.name,
                                    "%s.0" % pos, "%s.end" % pos)
                pos += 1
                self.buffer_bind(self._state, place.name)
        self._state.configure(state=tk.DISABLED)
    def buffer_enter (self, tag) :
        self._state.tag_configure(tag, background="#cff")
        self._source.tag_configure(tag, background="#cff")
    def buffer_leave (self, tag) :
        self._state.tag_configure(tag, background="white")
        self._source.tag_configure(tag, background="white")
    def quit (self, evt=None) :
        if popup.askokcancel("Really quit?", "Are you sure you want to"
                             " quit the simulator?") :
            self._win.quit()
    def select_trace (self, evt) :
        idx = self._trace.nearest(evt.y)
        if idx == 0 :
            self.net.set_marking(self.trace[0].pre)
        else :
            self.net.set_marking(self.trace[idx-1].post)
        self._modes.configure(state=tk.NORMAL)
        self.update()
        if idx < len(self.trace) :
            self._modes.selection_set(self.modes.index(self.trace[idx]))
            self.select_mode(idx)
        self._fire.configure(state=tk.DISABLED)
        self._modes.configure(state=tk.DISABLED)
        self._resume.configure(state=tk.NORMAL)
    def resume (self) :
        if self._trace.curselection() :
            last = self._trace.size() - 1
            self._trace.selection_clear(0, last)
            self._trace.see(last)
            self.net.set_marking(self.trace[-1].post)
            self.update_state()
        self._resume.configure(state=tk.DISABLED)
        self._modes.configure(state=tk.NORMAL)
