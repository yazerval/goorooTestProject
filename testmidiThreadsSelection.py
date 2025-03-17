import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import mido
import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
import random


def list_midi_ports():
    return mido.get_input_names(), mido.get_output_names()


class MidiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TEST GOOROO MIDI TOOL")
        self.message_counter = 1
        self.delays = []
        self.send_time = None
        self.running = False
        self.threads = []
        
        self.in_ports, self.out_ports = list_midi_ports()
        self.port_status = {}  # Stocke l'état activé/désactivé de chaque paire

        ttk.Label(root, text="Ports MIDI").grid(row=0, column=0, columnspan=3)
        self.port_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=5, exportselection=0)
        for in_port, out_port in zip(self.in_ports, self.out_ports):
            pair_name = f"{in_port} <-> {out_port}"
            self.port_listbox.insert(tk.END, pair_name)
        self.port_listbox.grid(row=1, column=0, columnspan=3)
        
        self.open_button = ttk.Button(root, text="Ouvrir Ports", command=self.open_ports)
        self.open_button.grid(row=2, column=0, columnspan=3)
        
        self.text_area = tk.Text(root, height=10, width=50)
        self.text_area.grid(row=3, column=0, columnspan=3)

    def open_ports(self):
        self.close_ports()
        self.running = True
        selected_pairs = self.port_listbox.curselection()
        
        for index in selected_pairs:
            in_port_name = self.in_ports[index]
            out_port_name = self.out_ports[index]
            
            in_port = mido.open_input(in_port_name)
            out_port = mido.open_output(out_port_name)
            
            var = tk.BooleanVar(value=True)  # Par défaut activé
            self.port_status[(in_port, out_port)] = var
            
            chk = ttk.Checkbutton(self.root, text=f"Actif: {in_port_name} <-> {out_port_name}", variable=var)
            chk.grid()
            
            thread = Thread(target=self.listen_midi, args=(in_port, var), daemon=True)
            self.threads.append(thread)
            thread.start()
            
            self.text_area.insert(tk.END, f"Ports ouverts : {in_port_name} <-> {out_port_name}\n")
        
    def listen_midi(self, port, var):
        while self.running:
            if var.get():  # Vérifie si la paire est activée
                for msg in port.iter_pending():
                    self.root.after(0, self.display_message, msg)
            time.sleep(0.01)

    def display_message(self, message):
        self.text_area.insert(tk.END, f"Reçu : {message}\n")
        self.text_area.see(tk.END)

    def close_ports(self):
        self.running = False
        for thread in self.threads:
            thread.join()
        self.threads.clear()
        for in_port, out_port in self.port_status.keys():
            in_port.close()
            out_port.close()
        self.port_status.clear()


if __name__ == "__main__":
    root = tk.Tk()
    app = MidiApp(root)
    root.mainloop()
