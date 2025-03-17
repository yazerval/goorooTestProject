import mido
import time
import tkinter as tk
from tkinter import ttk

class MIDILoopbackTester:
    def __init__(self, root):
        self.root = root
        self.root.title("🎹 MIDI Loopback Tester")
        
        # 🎛️ Sélection des ports MIDI
        self.port_label = ttk.Label(root, text="Sélectionne un port MIDI :")
        self.port_label.pack()

        self.midi_ports = mido.get_output_names()
        self.port_var = tk.StringVar(value=self.midi_ports[0] if self.midi_ports else "")
        self.port_menu = ttk.Combobox(root, textvariable=self.port_var, values=self.midi_ports)
        self.port_menu.pack()

        self.connect_button = ttk.Button(root, text="🔌 Connecter", command=self.connect_midi)
        self.connect_button.pack()

        # 🎵 Boutons pour envoyer des messages MIDI
        self.note_button = ttk.Button(root, text="🎹 Envoyer Note On", command=self.send_note)
        self.cc_button = ttk.Button(root, text="🎛️ Envoyer Control Change", command=self.send_cc)
        self.sysex_button = ttk.Button(root, text="📡 Envoyer SysEx", command=self.send_sysex)
        self.note_button.pack()
        self.cc_button.pack()
        self.sysex_button.pack()

        # 📡 Zone d'affichage des messages reçus
        self.log_label = ttk.Label(root, text="🎶 Messages MIDI reçus :")
        self.log_label.pack()
        self.log_text = tk.Text(root, height=10, width=50)
        self.log_text.pack()

        self.running = False
        self.inport = None
        self.outport = None

    def connect_midi(self):
        port_name = self.port_var.get()
        if not port_name:
            self.log_text.insert(tk.END, "⚠️ Aucun port MIDI sélectionné !\n")
            return

        try:
            self.outport = mido.open_output(port_name)
            self.inport = mido.open_input(port_name)
            self.log_text.insert(tk.END, f"✅ Connecté à {port_name}\n")
            self.running = True
            self.root.after(100, self.listen_midi)
        except Exception as e:
            self.log_text.insert(tk.END, f"❌ Erreur de connexion : {e}\n")

    def send_note(self):
        if self.outport:
            msg = mido.Message('note_on', note=60, velocity=100)
            self.outport.send(msg)
            self.log_text.insert(tk.END, f"🚀 Envoi: {msg}\n")

    def send_cc(self):
        if self.outport:
            msg = mido.Message('control_change', control=1, value=127)
            self.outport.send(msg)
            self.log_text.insert(tk.END, f"🚀 Envoi: {msg}\n")

    def send_sysex(self):
        if self.outport:
            msg = mido.Message('sysex', data=[0x7E, 0x00, 0x06, 0x01])
            self.outport.send(msg)
            self.log_text.insert(tk.END, f"🚀 Envoi: {msg}\n")

    def listen_midi(self):
        if self.inport:
            for msg in self.inport.iter_pending():
                self.log_text.insert(tk.END, f"✅ Reçu: {msg}\n")
                self.log_text.see(tk.END)
        
        if self.running:
            self.root.after(100, self.listen_midi)  # Vérifie toutes les 100ms

    def stop(self):
        self.running = False
        if self.inport:
            self.inport.close()
        if self.outport:
            self.outport.close()

# 🔥 Lancer l'application
root = tk.Tk()
app = MIDILoopbackTester(root)
root.protocol("WM_DELETE_WINDOW", app.stop)  # Ferme proprement les ports MIDI
root.mainloop()
