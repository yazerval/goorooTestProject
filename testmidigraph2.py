import mido
import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
import random
import statistics
from tkinter import Toplevel
import matplotlib.pyplot as plt

def list_midi_ports():
    return mido.get_input_names(), mido.get_output_names()

class MidiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TEST GOOROO MIDI TOOL")
        self.message_counter = 1  # Initialise le compteur d'ID de message
        self.delays = []  # Liste pour stocker les délais
        
        self.in_ports, self.out_ports = list_midi_ports()
        self.in_ports_selected = []
        self.out_ports_selected = []
        self.send_time = None
        self.running = False
        self.threads = []

        # Sélection des ports MIDI IN
        ttk.Label(root, text="Ports MIDI IN:").grid(row=0, column=0)
        self.in_ports_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=5, exportselection=0)
        for port in self.in_ports:
            self.in_ports_listbox.insert(tk.END, port)
        self.in_ports_listbox.grid(row=0, column=1)

        # Sélection des ports MIDI OUT
        ttk.Label(root, text="Ports MIDI OUT:").grid(row=1, column=0)
        self.out_ports_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=5, exportselection=0)
        for port in self.out_ports:
            self.out_ports_listbox.insert(tk.END, port)
        self.out_ports_listbox.grid(row=1, column=1)
        
        # Bouton pour ouvrir les ports
        self.open_button = ttk.Button(root, text="Ouvrir Ports", command=self.open_ports)
        self.open_button.grid(row=2, column=0, columnspan=2)
        
        # Zone d'affichage des messages reçus
        self.text_area = tk.Text(root, height=10, width=50)
        self.text_area.grid(row=3, column=0, columnspan=2)
        
        # Nombre de notes à envoyer
        ttk.Label(root, text="Nombre de notes à envoyer :").grid(row=4, column=0)
        self.num_notes_var = tk.StringVar()
        self.num_notes_entry = ttk.Entry(root, textvariable=self.num_notes_var)
        self.num_notes_entry.grid(row=4, column=1)
        
        self.send_button = ttk.Button(root, text="Envoyer Notes Aléatoires", command=self.send_random_notes)
        self.send_button.grid(row=5, column=0, columnspan=2)

        # Label pour afficher le délai
        self.delay_label = ttk.Label(root, text="Délai : N/A")
        self.delay_label.grid(row=6, column=0, columnspan=2)
    
    def open_ports(self):
        self.close_ports()
        self.running = True
        
        selected_in_indices = self.in_ports_listbox.curselection()
        selected_out_indices = self.out_ports_listbox.curselection()

        self.in_ports_selected = [mido.open_input(self.in_ports[i]) for i in selected_in_indices]
        self.out_ports_selected = [mido.open_output(self.out_ports[i]) for i in selected_out_indices]
        
        self.text_area.insert(tk.END, "\nPorts MIDI ouverts !\n")

        # Démarrer un thread pour chaque port MIDI IN
        for port in self.in_ports_selected:
            thread = Thread(target=self.listen_midi, args=(port,), daemon=True)
            self.threads.append(thread)
            thread.start()

    def listen_midi(self, port):
        while self.running:
            for msg in port.iter_pending():
                receive_time = time.time()
                delay = receive_time - self.send_time if self.send_time else None
                self.delays.append(delay)  # Ajout du délai à la liste
                self.root.after(0, self.display_message, msg, delay)
            time.sleep(0.01)

    def display_message(self, message, delay):
        self.text_area.insert(tk.END, f"Reçu : {message}\n")
        if delay is not None:
            self.delay_label.config(text=f"Délai : {delay:.6f} s")
        self.text_area.see(tk.END)
    
    def send_random_notes(self):
        try:
            num_notes = int(self.num_notes_var.get())
            if num_notes <= 0:
                raise ValueError("Le nombre de notes doit être positif.")
            self.send_time = time.time()
            
            # Créer un thread pour chaque port de sortie MIDI et envoyer des notes en parallèle
            for port in self.out_ports_selected:
                thread = Thread(target=self.send_random_notes_threaded, args=(port, num_notes), daemon=True)
                self.threads.append(thread)
                thread.start()

        except Exception as e:
            self.root.after(0, self.text_area.insert, tk.END, f"\nErreur envoi MIDI : {e}\n")
        self.root.after(0, self.text_area.see, tk.END)
    
    def send_random_notes_threaded(self, port, num_notes=None):
        try:
            # Si num_notes est passé en argument, l'utiliser, sinon prendre la valeur du champ texte
            if num_notes is None:
                num_notes = int(self.num_notes_var.get())
            if num_notes <= 0:
                raise ValueError("Le nombre de notes doit être positif.")
            
            for _ in range(num_notes):
                note = random.randint(0, 127)  # Générer une note aléatoire
                msg = mido.Message('note_on', note=note, velocity=64, time=self.message_counter)
                port.send(msg)
                self.message_counter += 1
                self.root.after(0, self.text_area.insert, tk.END, f"Envoyé : {msg}\n")
                time.sleep(0.1)  # Délai entre les envois de notes
        except Exception as e:
            self.root.after(0, self.text_area.insert, tk.END, f"\nErreur envoi MIDI : {e}\n")
        self.root.after(0, self.text_area.see, tk.END)
    
    def close_ports(self):
        self.running = False
        for thread in self.threads:
            thread.join()
        self.threads.clear()
        
        for port in self.in_ports_selected:
            port.close()
        for port in self.out_ports_selected:
            port.close()
        
        self.in_ports_selected.clear()
        self.out_ports_selected.clear()
    
    def __del__(self):
        self.close_ports()

    def calculate_statistics(self):
        if not self.delays:
            return None  # Pas de délais reçus

        mean_delay = statistics.mean(self.delays)
        median_delay = statistics.median(self.delays)
        min_delay = min(self.delays)
        max_delay = max(self.delays)

        return mean_delay, median_delay, min_delay, max_delay
    


if __name__ == "__main__":
    root = tk.Tk()
    app = MidiApp(root)
    root.mainloop()
