import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import mido
import tkinter as tk
from tkinter import ttk
from threading import Thread
import threading
import time
import random
import statistics
from tkinter import Toplevel

def list_midi_ports():
    return mido.get_input_names(), mido.get_output_names()

class MidiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TEST GOOROO MIDI TOOL")
        self.message_counter = 1  # Initialise le compteur d'ID de message
        self.delays = []  # Liste pour stocker les délais
        self.note = 1
        self.sent_messages = []  # Liste des messages envoyés avec leurs timestamps
        self.receive_messages = []  # Liste des messages reçus avec leurs timestamps
        self.active_pair = 0
        self.compteurReceive = 0
        self.compteurSend = 0
        self.compteurErreur = 0
        self.message_counts = {}  # Compteurs pour les messages envoyés et reçus
        self.event = threading.Event()
        self.num_entrees = 0
        
        self.in_ports, self.out_ports = list_midi_ports()
        self.in_ports_selected = []
        self.out_ports_selected = []
        self.send_time = None
        self.running = False
        self.threads = []
        self.port_status = {}  # Stocke l'état activé/désactivé de chaque paire

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

        
        
        self.send_button = ttk.Button(root, text="Envoyer Notes Aléatoires", command=self.send_random_notes)
        self.send_button.grid(row=6, column=0, columnspan=2)

        # Label pour afficher le délai
        self.delay_label = ttk.Label(root, text="Délai : N/A")
        self.delay_label.grid(row=8, column=0, columnspan=2)

        # Boutons Start/Stop pour l'envoi continu de notes
        self.start_button = ttk.Button(root, text="Start", command=self.start_sending)
        self.start_button.grid(row=9, column=0, columnspan=1)
        
        self.stop_button = ttk.Button(root, text="Stop", command=self.stop_sending)
        self.stop_button.grid(row=9, column=1, columnspan=1)

        # Sélecteur de type de message
        ttk.Label(root, text="Type de message MIDI :").grid(row=7, column=0)
        self.message_type_var = tk.StringVar(value="MIDI")
        #self.message_type_menu = ttk.Combobox(root, textvariable=self.message_type_var, values=["MIDI", "SysEx"])
        self.radio_midi = ttk.Radiobutton(root, text="MIDI", variable=self.message_type_var, value="MIDI")
        self.radio_sysex = ttk.Radiobutton(root, text="SysEx", variable=self.message_type_var, value="SysEx")
        self.radio_midi.grid(row=7, column=1)
        self.radio_sysex.grid(row=7, column=2)
        self.message_type_var.trace_add("write", lambda *args: self.update_entry_label())
        #self.message_type_menu.grid(row=7, column=1)
        #self.message_type_menu.bind("<<ComboboxSelected>>", lambda _: self.update_entry_label())
        self.update_entry_label()

    def update_entry_label(self):
        """Met à jour l'interface selon le type de message sélectionné."""
        # Supprimer l'ancien label et champ d'entrée s'ils existent
        if hasattr(self, "entry_label"):
            self.entry_label.destroy()
        if hasattr(self, "num_notes_entry"):
            self.num_notes_entry.destroy()
        if hasattr(self, "num_payload_entry"):
            self.num_payload_entry.destroy()

        # Création du bon label et champ d'entrée
        if self.message_type_var.get() == "MIDI":
            self.entry_label = ttk.Label(self.root, text="Nombre de notes à envoyer :")
            #print("MIDI\n")
            self.send_button.config(text="Envoyer Notes Aléatoires")
        else:
            self.entry_label = ttk.Label(self.root, text="Nombre notes / Longueur du payload SysEx :")
            self.send_button.config(text="Envoyer SysEx")
            #print("SysEx\n")
            # Création du champ d'entrée correspondant
            self.num_notes_var = tk.StringVar()
            self.num_payload_entry = ttk.Entry(self.root, textvariable=self.num_notes_var)
            self.num_payload_entry.grid(row=5, column=2)

        # Création du champ d'entrée correspondant
        self.num_notes_var = tk.StringVar()
        self.num_notes_entry = ttk.Entry(self.root, textvariable=self.num_notes_var)
        self.num_notes_entry.grid(row=5, column=1)

        self.entry_label.grid(row=5, column=0)
    
    def open_ports(self):
        #self.close_ports()
        self.running = True

        selected_in_indices = self.in_ports_listbox.curselection()
        selected_out_indices = self.out_ports_listbox.curselection()

        if not selected_in_indices or not selected_out_indices:
            self.text_area.insert(tk.END, "⚠️ Sélectionnez au moins un port IN et un port OUT\n")
            return

        for in_index, out_index in zip(selected_in_indices, selected_out_indices):
            in_port_name = self.in_ports[in_index]
            out_port_name = self.out_ports[out_index]
            print(f"Ouverture des ports : {in_port_name} <-> {out_port_name}")
            #print(f"Tout les ports OUT : {self.out_ports_selected}")
            if out_port_name in self.out_ports_selected:
                self.text_area.insert(tk.END, f"⚠️ Le port {out_port_name} est déjà ouvert\n")
                continue

            in_port = mido.open_input(in_port_name)
            out_port = mido.open_output(out_port_name)

            self.out_ports_selected.append(out_port)  # ✅ Ajout du port OUT
            #print(f"Tout les ports OUT APRES : {self.out_ports_selected}")
            var = tk.BooleanVar(value=True)  # Par défaut activé
            self.port_status[(in_port, out_port)] = var

            # Initialiser les compteurs pour cette paire de ports
            self.message_counts[(in_port, out_port)] = {"sent": 0, "received": 0}
            """print(f"Compteur : {self.message_counts[(in_port, out_port)]}")
            print(f"In port : {in_port}")
            print(f"Out port : {out_port}")"""

            # Création du Checkbutton
            chk = ttk.Checkbutton(
            self.root,
            text=f"Actif: {in_port_name} <-> {out_port_name}",
            variable=var,
            command=lambda: self.toggle_port(in_port, out_port, var)  # Passer les arguments avec lambda
            )
            chk.grid()

            self.text_area.insert(tk.END, f"Ports ouverts : {in_port_name} <-> {out_port_name}\n")
            # Lancer un thread pour écouter les messages du port MIDI IN
            listen_thread = Thread(target=self.listen_midi, args=(in_port,), daemon=True)
            listen_thread.start()

    def toggle_port(self, in_port, out_port, var):
        print(f"Port {in_port.name} <-> {out_port.name} : {var.get()}")
        """Activer ou désactiver le port MIDI en fonction de l'état de la case à cocher."""
        if var.get():  # Si la case est cochée
            # Réactiver l'écoute du port
            self.text_area.insert(tk.END, f"Port réactivé : {in_port.name} <-> {out_port.name}\n")
            self.active_pair = 1
        else:  # Si la case est décochée
            # Arrêter l'écoute du port
            self.text_area.insert(tk.END, f"Port désactivé : {in_port.name} <-> {out_port.name}\n")
            self.active_pair = 0
            # Ici, tu pourrais ajouter un mécanisme pour arrêter proprement l'écoute ou gérer la désactivation
            


    def listen_midi(self, port):
        self.last_note = 0
        # Utilisation de (in_port, stored_out_port) comme clé
        while self.running:
            for msg in port.iter_pending():
                receive_time = time.perf_counter()
                print(f"Message reçu : {msg.type}")
                # Si le message est un message de type "note_on" ou "note_off"
                if msg.type in ['note_on', 'note_off']:
                    self.receive_messages.append({'note': msg.note, 'receive_time': receive_time})
                    note = msg.note
                    self.compteurReceive += 1
                    
                    if self.compteurReceive == self.num_entrees:
                        self.event.set()
                    
                    print(f"note {note} != {self.last_note}")
                    if note != self.last_note:
                        print(f"Erreur de note : {note} != {self.last_note}")
                        print(f"Message : {msg}")
                        raise ValueError("Erreur de note reçue")
                    
                    # Mise à jour de la dernière note reçue
                    if self.last_note == 127:
                        self.last_note = 0
                    else:
                        self.last_note += 1
                    
                # Si le message est un message SysEx
                elif msg.type == 'sysex':
                    # Pour les messages SysEx, tu peux traiter les données contenues dans msg.data
                    self.receive_messages.append({'sysex_data': msg.data, 'receive_time': receive_time})
                    self.compteurReceive += 1

                    if self.compteurReceive == self.num_entrees:
                        self.event.set()
                    
                    print(f"Message SysEx reçu : {msg}")
                
                #time.sleep(0.001)  # Petite pause pour éviter la saturation du CPU


    """def display_message(self, message, delay):
        #self.text_area.insert(tk.END, f"Reçu : {message}\n")
        if delay is not None:
            self.delay_label.config(text=f"Délai : {delay:.6f} s")
        self.text_area.see(tk.END)
    """
    def send_random_notes(self):
        #for port in self.out_ports_selected:
        #    print(f"Paire: {self.message_counts[(port, port)]}")
        try:
            self.delays = []  # Liste pour stocker les délais
            self.sent_messages = []  # Liste des messages envoyés avec leurs timestamps
            self.receive_messages = []  # Liste des messages reçus avec leurs timestamps
            self.compteurReceive = 0
            self.compteurSend = 0
            self.note = 0
            self.last_note = 0
            self.event.clear()
            #self.stat_button = ttk.Button(root, text="Ouvrir Stat", command=self.self.afficher_statistiques)
            #self.stat_button.grid(row=6, column=2, columnspan=2)
            num_notes = int(self.num_notes_var.get())
            self.num_entrees = num_notes
            if num_notes < 0:
                raise ValueError("Le nombre de notes doit être positif.")

            # Créer un thread pour chaque port de sortie MIDI et envoyer des notes en parallèle
            for port in self.out_ports_selected:
                for (in_port, stored_out_port), var in self.port_status.items():
                    if stored_out_port == port and var.get():  # Vérifie si la paire est activée
                        print(f"Compteur : {self.message_counts[(in_port, stored_out_port)]}")
                        thread = Thread(target=self.send_random_notes_threaded, args=(port, num_notes), daemon=True)
                        self.threads.append(thread)
                        thread.start()
                    else :
                        self.text_area.insert(tk.END, f"⚠️ La paire {in_port.name} <-> {stored_out_port.name} est désactivée\n")

        except Exception as e:
            self.root.after(0, self.text_area.insert, tk.END, f"\nErreur envoi MIDI : {e}\n")
        self.root.after(0, self.text_area.see, tk.END)
    
    def send_random_notes_threaded(self, port, num_notes=None):
        try:
            # Si num_notes est passé en argument, l'utiliser, sinon prendre la valeur du champ texte
            if num_notes < 0:
                raise ValueError("Le nombre de notes doit être positif.")
            
            if hasattr(self, "stat_button"):
                self.stat_button.destroy()

            for (in_port, stored_out_port), var in self.message_counts.items():
                            # Incrémenter le compteur des messages envoyés pour cette paire
                self.message_counts[(in_port, stored_out_port)]["sent"] = 0

            if self.message_type_var.get() == "MIDI":
                if num_notes > 0 :
                    self.root.after(0, self.text_area.insert, tk.END, f"Envoi des {num_notes} messages...\n")
                    for _ in range(num_notes):
                        msg = mido.Message('note_on', note=self.note, velocity=64, time=self.message_counter)
                        self.send_time = time.perf_counter()  # Timestamp de l'envoi
                        # Enregistrer la note et son timestamp
                        self.sent_messages.append({'note': msg.note, 'send_time': self.send_time})
                        #print(f"Envoi : {msg}")
                        port.send(msg)
                        
                        for (in_port, stored_out_port), var in self.message_counts.items():
                            # Incrémenter le compteur des messages envoyés pour cette paire
                            self.message_counts[(in_port, stored_out_port)]["sent"] += 1


                        self.message_counter += 1
                        if self.note == 127:
                            self.note = 0
                        else:
                            self.note += 1
                        
                        #self.root.after(0, self.text_area.insert, tk.END, f"Envoyé : {msg}\n")
                        #time.sleep(0.001)  # Délai entre les envois de notes
                    self.root.after(0, self.text_area.insert, tk.END, f"Fin d'envoi des messages !\n")
                elif num_notes == 0:
                    while self.running:
                        note = random.randint(0, 127)
                        msg = mido.Message('note_on', note=note, velocity=64, time=self.message_counter)
                        self.send_time = time.time()  # Timestamp de l'envoi
                        port.send(msg)
                        # Incrémenter le compteur des messages envoyés pour cette paire
                        for (in_port, stored_out_port), var in self.message_counts.items():
                            # Incrémenter le compteur des messages envoyés pour cette paire
                            self.message_counts[(in_port, stored_out_port)]["sent"] += 1
                        self.message_counter += 1
                        if self.note == 127:
                            self.note = 0
                        else:
                            self.note += 1
                        self.root.after(0, self.text_area.insert, tk.END, f"Envoyé : {msg}\n")
            elif self.message_type_var.get() == "SysEx":
                num_packs = int(self.num_payload_entry.get())
                for _ in range(num_notes):
                    #incrémenter le sysex comme le midi 
                    msg = mido.Message('sysex', data=[random.randint(0, 127) for _ in range(num_packs)])
                    self.send_time = time.time()  # Timestamp de l'envoi
                    port.send(msg)
                    for (in_port, stored_out_port), var in self.message_counts.items():
                            # Incrémenter le compteur des messages envoyés pour cette paire
                            self.message_counts[(in_port, stored_out_port)]["sent"] += 1

        except Exception as e:
            self.root.after(0, self.text_area.insert, tk.END, f"\nErreur envoi MIDI : {e}\n")

        for (in_port, stored_out_port), var in self.message_counts.items():
            self.compteurSend = self.message_counts[(in_port, stored_out_port)]["sent"]
        self.event.wait()
        self.root.after(100, self.afficher_statistiques)
        self.root.after(0, self.text_area.see, tk.END)
        self.root.after(0, self.text_area.insert, tk.END, f"Fin de reception ! Il y a eu {self.compteurSend} messages envoyés et {self.compteurReceive} messages reçus !\n")
        
        #print(f"Compteur de messages recus : {self.compteurReceive}")
        #self.stat_button = ttk.Button(self.root, text="Statistiques", command=self.afficher_statistiques)
        #self.stat_button.grid(row=10, column=1)

    
    def start_sending(self):
        """Démarre l'envoi continu de notes."""
        self.running = True

    def stop_sending(self):
        """Arrête l'envoi continu de notes."""
        self.running = False

    
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

    def afficher_statistiques(self):
        """Affiche les statistiques des délais MIDI."""
        #if not self.delays:
        #   return
        #affichage du premier tableau 
        
        print("Sent messages")
        print(self.sent_messages)
        #affichage du deuxième tableau
        print("Received messages")  
        print(self.receive_messages)
        
        
       # delais = self.delays
       #calcul de délai avec les deux tableaux 
        for i in range(len(self.sent_messages)):
            if i < len(self.receive_messages):
                delay = self.receive_messages[i]['receive_time'] - self.sent_messages[i]['send_time']
                self.delays.append(delay)
            else:
                self.delays.append(None)
        delais = self.delays

        # Calcul des statistiques
        moyenne = np.mean(delais)
        mediane = np.median(delais)
        minimum = np.min(delais)
        maximum = np.max(delais)
        
        # Création de la fenêtre
        fenetre = tk.Tk()
        fenetre.title("Statistiques des délais MIDI")
        fenetre.geometry("600x500")
        
        # Création d'un cadre pour les statistiques
        cadre_stats = ttk.Frame(fenetre)
        cadre_stats.pack(pady=10)
        
        ttk.Label(cadre_stats, text=f"Moyenne: {moyenne:.3f} ms").pack()
        ttk.Label(cadre_stats, text=f"Médiane: {mediane:.3f} ms").pack()
        ttk.Label(cadre_stats, text=f"Minimum: {minimum:.3f} ms").pack()
        ttk.Label(cadre_stats, text=f"Maximum: {maximum:.3f} ms").pack()
        
        # Création du graphique
        fig, ax = plt.subplots()
        ax.plot(delais, marker='o', linestyle='-', color='b', label="Délais")
        ax.axhline(y=moyenne, color='r', linestyle='--', label="Moyenne")
        ax.set_title("Évolution des délais MIDI")
        ax.set_xlabel("Message #")
        ax.set_ylabel("Délai (ms)")
        ax.legend()
        
        # Intégration du graphique dans Tkinter
        canvas = FigureCanvasTkAgg(fig, master=fenetre)
        canvas.draw()
        canvas.get_tk_widget().pack()
        
        # Bouton de fermeture
        ttk.Button(fenetre, text="Fermer", command=fenetre.destroy).pack(pady=10)
        
        fenetre.mainloop()
    


if __name__ == "__main__":
    root = tk.Tk()
    app = MidiApp(root)
    root.mainloop()
