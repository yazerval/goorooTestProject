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
        self.message_counter = 1  # Compteur global pour le timecode/message
        self.delays = []          # Liste pour stocker les délais (pour statistiques)
        self.note = 0             # Compteur pour les messages, démarre à 0 et s'incrémente de 1
        self.num_entrees = 0      # Nombre total de messages (pour le batch)
        self.running = True       # Flag global de l'application

        # Récupération des ports MIDI
        self.in_ports, self.out_ports = list_midi_ports()
        # Chaque paire est stockée sous forme d'un dictionnaire avec ses ports et ses listes propres
        self.pairs = []

        self.threads = []  # Liste des threads lancés

        self.create_widgets()

    def create_widgets(self):
        # Liste des ports MIDI IN
        ttk.Label(self.root, text="Ports MIDI IN:").grid(row=0, column=0, sticky="w")
        self.in_ports_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, height=5, exportselection=0)
        for port in self.in_ports:
            self.in_ports_listbox.insert(tk.END, port)
        self.in_ports_listbox.grid(row=0, column=1, sticky="w")

        # Liste des ports MIDI OUT
        ttk.Label(self.root, text="Ports MIDI OUT:").grid(row=1, column=0, sticky="w")
        self.out_ports_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, height=5, exportselection=0)
        for port in self.out_ports:
            self.out_ports_listbox.insert(tk.END, port)
        self.out_ports_listbox.grid(row=1, column=1, sticky="w")
        
        # Bouton d'ouverture des ports et création des paires
        self.open_button = ttk.Button(self.root, text="Ouvrir Ports", command=self.open_ports)
        self.open_button.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Zone d'affichage des logs
        self.text_area = tk.Text(self.root, height=10, width=70)
        self.text_area.grid(row=3, column=0, columnspan=3, pady=5)
        
        # Champ pour saisir le nombre de messages à envoyer
        self.num_notes_var = tk.StringVar()
        self.entry_label = ttk.Label(self.root, text="Nombre de messages à envoyer :")
        self.entry_label.grid(row=4, column=0, sticky="w")
        self.num_notes_entry = ttk.Entry(self.root, textvariable=self.num_notes_var)
        self.num_notes_entry.grid(row=4, column=1, sticky="w")
        
        # En mode SysEx, un champ supplémentaire sera créé dans update_entry_label()
        
        # Bouton pour lancer l'envoi (batch)
        self.send_button = ttk.Button(self.root, text="Envoyer Notes Aléatoires", command=self.send_random_notes)
        self.send_button.grid(row=5, column=0, columnspan=2, pady=5)

        # Label pour informations supplémentaires
        self.delay_label = ttk.Label(self.root, text="Délai : N/A")
        self.delay_label.grid(row=6, column=0, columnspan=2, pady=5)

        # Boutons Start/Stop pour l'envoi continu
        self.start_button = ttk.Button(self.root, text="Start", command=self.start_sending)
        self.start_button.grid(row=7, column=0, pady=5)
        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop_sending)
        self.stop_button.grid(row=7, column=1, pady=5)
        # Bouton pour effacer le contenu de la fenêtre de texte (sans emoji)
        self.clear_button = ttk.Button(self.root, text="Effacer les messages", command=self.clear_text_area)
        self.clear_button.grid(row=2, column=2, columnspan=2, pady=5)

        # Sélecteur du type de message MIDI (MIDI ou SysEx)
        ttk.Label(self.root, text="Type de message MIDI :").grid(row=8, column=0, sticky="w")
        self.message_type_var = tk.StringVar(value="MIDI")
        self.radio_midi = ttk.Radiobutton(self.root, text="MIDI", variable=self.message_type_var, value="MIDI", command=self.update_entry_label)
        self.radio_sysex = ttk.Radiobutton(self.root, text="SysEx", variable=self.message_type_var, value="SysEx", command=self.update_entry_label)
        self.radio_midi.grid(row=8, column=1, sticky="w")
        self.radio_sysex.grid(row=8, column=2, sticky="w")
        self.update_entry_label()
    
    def clear_text_area(self):
        """Efface tout le contenu de la fenêtre de texte."""
        self.text_area.delete('1.0', tk.END)

    def update_entry_label(self):
        """Mise à jour des champs d'entrée en fonction du mode (MIDI ou SysEx)."""
        if hasattr(self, "entry_label"):
            self.entry_label.destroy()
        if hasattr(self, "num_notes_entry"):
            self.num_notes_entry.destroy()
        if hasattr(self, "num_payload_entry"):
            self.num_payload_entry.destroy()

        if self.message_type_var.get() == "MIDI":
            self.entry_label = ttk.Label(self.root, text="Nombre de messages à envoyer :")
            self.send_button.config(text="Envoyer Notes Aléatoires")
        else:
            self.entry_label = ttk.Label(self.root, text="Nombre de messages / Longueur du payload SysEx :")
            self.send_button.config(text="Envoyer SysEx")
            self.num_payload_entry = ttk.Entry(self.root, textvariable=tk.StringVar())
            self.num_payload_entry.grid(row=4, column=2, sticky="w")

        self.num_notes_var = tk.StringVar()
        self.num_notes_entry = ttk.Entry(self.root, textvariable=self.num_notes_var)
        self.num_notes_entry.grid(row=4, column=1, sticky="w")
        self.entry_label.grid(row=4, column=0, sticky="w")
    
    def open_ports(self):
        selected_in_indices = self.in_ports_listbox.curselection()
        selected_out_indices = self.out_ports_listbox.curselection()

        if not selected_in_indices or not selected_out_indices:
            self.text_area.insert(tk.END, "Veuillez sélectionner au moins un port d'entrée et un port de sortie.\n")
            return

        # Pour chaque paire, associer le ième port IN avec le ième port OUT
        for in_index, out_index in zip(selected_in_indices, selected_out_indices):
            in_port_name = self.in_ports[in_index]
            out_port_name = self.out_ports[out_index]
            pair_key = f"{in_port_name} <-> {out_port_name}"

            if any(pair['out_port'].name == out_port_name for pair in self.pairs):
                self.text_area.insert(tk.END, f"Attention : le port {out_port_name} est déjà ouvert.\n")
                continue

            in_port = mido.open_input(in_port_name)
            out_port = mido.open_output(out_port_name)

            active_var = tk.BooleanVar(value=True)
            pair = {
                'in_port': in_port,
                'out_port': out_port,
                'active': active_var,
                'send_flag': False,
                'continuous': False,
                'key': pair_key,
                'sent_messages': [],
                'received_messages': []
            }
            self.pairs.append(pair)

            # Créer un cadre pour regrouper la checkbox et le bouton de statistiques
            pair_frame = ttk.Frame(self.root)
            pair_frame.grid(sticky="w", padx=5, pady=2)
            chk = ttk.Checkbutton(pair_frame,
                                  text=f"Actif : {pair_key}",
                                  variable=active_var,
                                  command=lambda p=pair: self.toggle_port(p))
            chk.grid(row=0, column=0, sticky="w")
            btn_stats = ttk.Button(pair_frame, text="Statistiques", command=lambda p=pair: self.show_pair_statistics(p))
            btn_stats.grid(row=0, column=1, padx=5)
            pair['frame'] = pair_frame

            self.text_area.insert(tk.END, f"Les ports ont été ouverts : {pair_key}\n")

            # Lancer les threads d'écoute et d'envoi pour cette paire
            listen_thread = Thread(target=self.listen_midi, args=(pair,), daemon=True)
            listen_thread.start()
            self.threads.append(listen_thread)

            send_thread = Thread(target=self.send_random_notes_threaded, args=(pair,), daemon=True)
            send_thread.start()
            self.threads.append(send_thread)
    
    def toggle_port(self, pair):
        if pair['active'].get():
            self.text_area.insert(tk.END, f"La paire {pair['key']} a été réactivée.\n")
        else:
            self.text_area.insert(tk.END, f"La paire {pair['key']} a été désactivée.\n")
            pair['send_flag'] = False
            pair['continuous'] = False

    def listen_midi(self, pair):
        in_port = pair['in_port']
        last_expected = 0
        while self.running:
            for msg in in_port.iter_pending():
                receive_time = time.perf_counter()
                if msg.type in ['note_on', 'note_off']:
                    pair['received_messages'].append({'note': msg.note, 'receive_time': receive_time})
                    if msg.note != last_expected:
                        print(f"[{pair['key']}] Note reçue {msg.note} (attendue {last_expected})")
                    last_expected += 1
                elif msg.type == 'sysex':
                    pair['received_messages'].append({'sysex_data': msg.data, 'receive_time': receive_time})
            # Petite pause pour éviter une surcharge de la boucle
            time.sleep(0.005)

    def send_random_notes(self):
        """Bouton d'envoi batch : réinitialise les compteurs et listes,
           récupère le nombre de messages (et longueur du payload en mode SysEx)
           et déclenche l'envoi sur toutes les paires actives."""
        try:
            # Réinitialisation des compteurs et des listes pour chaque envoi
            self.note = 0
            self.message_counter = 1
            for pair in self.pairs:
                pair['sent_messages'] = []
                pair['received_messages'] = []

            num_notes_str = self.num_notes_var.get().strip()
            if num_notes_str == "":
                num_notes = 0
            else:
                try:
                    num_notes = int(num_notes_str)
                except Exception as e:
                    print(f"Erreur conversion nombre de messages: {e}")
                    return

            if num_notes < 0:
                raise ValueError("Le nombre de messages doit être positif.")
            self.num_entrees = num_notes

            for pair in self.pairs:
                if pair['active'].get():
                    pair['send_flag'] = True

            self.text_area.insert(tk.END, f"Début de l'envoi de {num_notes} messages sur les paires actives.\n")
        except Exception as e:
            self.text_area.insert(tk.END, f"Erreur envoi MIDI : {e}\n")
        self.text_area.see(tk.END)
    
    def send_random_notes_threaded(self, pair):
        out_port = pair['out_port']
        while self.running:
            if pair['active'].get() and (pair.get('send_flag') or pair.get('continuous')):
                if self.message_type_var.get() == "MIDI":
                    num_notes_str = self.num_notes_var.get().strip()
                    if num_notes_str == "":
                        num_notes = 0
                    else:
                        try:
                            num_notes = int(num_notes_str)
                        except Exception as e:
                            print(f"Erreur conversion: {e}")
                            num_notes = 0
                    if num_notes > 0:
                        # Envoi batch
                        for _ in range(num_notes):
                            msg = mido.Message('note_on', note=self.note, velocity=64, time=self.message_counter)
                            send_time = time.perf_counter()
                            pair['sent_messages'].append({'note': msg.note, 'send_time': send_time})
                            out_port.send(msg)
                            self.message_counter += 1
                            if self.note == 127:
                                self.note = 0
                            else:
                                self.note += 1
                        self.root.after(0, self.text_area.insert, tk.END, f"Envoi terminé sur {pair['key']}.\n")
                        time.sleep(0.2)
                        self.root.after(0, self.text_area.insert, tk.END, f"Statistiques pour {pair['key']} : Envoyé {len(pair['sent_messages'])} / Reçu {len(pair['received_messages'])}.\n")
                    else:
                        # Envoi continu
                        msg = mido.Message('note_on', note=self.note, velocity=64, time=self.message_counter)
                        send_time = time.perf_counter()
                        pair['sent_messages'].append({'note': msg.note, 'send_time': send_time})
                        out_port.send(msg)
                        self.message_counter += 1
                        if self.note == 127:
                            self.note = 0
                        else:
                            self.note += 1
                        self.root.after(0, self.text_area.insert, tk.END,
                                         f"Message envoyé sur {pair['key']} : {msg}\n")
                    if not pair.get('continuous'):
                        pair['send_flag'] = False
                    time.sleep(0.1)
                elif self.message_type_var.get() == "SysEx":
                    num_notes_str = self.num_notes_var.get().strip()
                    if num_notes_str == "":
                        num_notes = 0
                    else:
                        try:
                            num_notes = int(num_notes_str)
                        except Exception as e:
                            print(f"Erreur conversion: {e}")
                            num_notes = 0
                    num_packs_str = self.num_payload_entry.get().strip() if hasattr(self, 'num_payload_entry') else "0"
                    if num_packs_str == "":
                        num_packs = 0
                    else:
                        try:
                            num_packs = int(num_packs_str)
                        except Exception as e:
                            print(f"Erreur conversion: {e}")
                            num_packs = 0
                    self.root.after(0, self.text_area.insert, tk.END,
                                    f"Début de l'envoi de {num_notes} messages (payload de {num_packs} octets) sur {pair['key']}...\n")
                    for _ in range(num_notes):
                        msg_data = [self.note + i for i in range(num_packs)]
                        msg = mido.Message('sysex', data=msg_data)
                        send_time = time.perf_counter()
                        pair['sent_messages'].append({'sysex_data': msg.data, 'send_time': send_time})
                        out_port.send(msg)
                        self.note += 1
                        time.sleep(0.001)
                    self.root.after(0, self.text_area.insert, tk.END,
                                    f"Envoi terminé sur {pair['key']}.\n")
                    time.sleep(0.2)
                    self.root.after(0, self.text_area.insert, tk.END,
                                    f"Statistiques pour {pair['key']} : Envoyé {len(pair['sent_messages'])} / Reçu {len(pair['received_messages'])}.\n")
                    if not pair.get('continuous'):
                        pair['send_flag'] = False
                    time.sleep(0.1)
            else:
                time.sleep(0.01)

    def start_sending(self):
        for pair in self.pairs:
            if pair['active'].get():
                pair['continuous'] = True
        self.text_area.insert(tk.END, "L'envoi continu a commencé sur les paires actives.\n")

    def stop_sending(self):
        for pair in self.pairs:
            pair['continuous'] = False
        self.text_area.insert(tk.END, "L'envoi continu a été arrêté.\n")
    
    def close_ports(self):
        self.running = False
        for thread in self.threads:
            thread.join(timeout=0.1)
        self.threads.clear()
        for pair in self.pairs:
            pair['in_port'].close()
            pair['out_port'].close()
        self.pairs.clear()
    
    def __del__(self):
        self.close_ports()

    def show_pair_statistics(self, pair):
        """Ouvre une fenêtre affichant les statistiques concernant les paquets envoyés et reçus pour la paire."""
        if self.message_type_var.get() == "MIDI":
            sent_ids = [msg["note"] for msg in pair["sent_messages"] if "note" in msg]
            received_ids = [msg["note"] for msg in pair["received_messages"] if "note" in msg]
        else:
            sent_ids = [msg["sysex_data"][0] for msg in pair["sent_messages"] if "sysex_data" in msg and len(msg["sysex_data"]) > 0]
            received_ids = [msg["sysex_data"][0] for msg in pair["received_messages"] if "sysex_data" in msg and len(msg["sysex_data"]) > 0]

        missing = sorted(set(sent_ids) - set(received_ids))
        total_sent = len(sent_ids)
        total_received = len(received_ids)
        missing_count = len(missing)

        stats_win = tk.Toplevel(self.root)
        stats_win.title(f"Statistiques - {pair['key']}")
        stats_win.geometry("500x400")

        frame = ttk.Frame(stats_win)
        frame.pack(pady=10, padx=10)

        ttk.Label(frame, text=f"Messages envoyés : {total_sent}").pack(anchor="w")
        ttk.Label(frame, text=f"Messages reçus : {total_received}").pack(anchor="w")
        ttk.Label(frame, text=f"Paquets manquants : {missing_count}").pack(anchor="w")
        ttk.Label(frame, text="Liste des paquets manquants :").pack(anchor="w", pady=(10,0))
        
        text_missing = tk.Text(frame, height=10, width=50)
        text_missing.pack()
        if missing_count > 0:
            for m in missing:
                text_missing.insert(tk.END, f"{m}\n")
        else:
            text_missing.insert(tk.END, "Aucun paquet manquant.")
        
        ttk.Button(stats_win, text="Fermer", command=stats_win.destroy).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = MidiApp(root)
    root.mainloop()
