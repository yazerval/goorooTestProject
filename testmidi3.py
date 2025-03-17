import mido
import time
from datetime import datetime

output_port_name = "Gestionnaire IAC Bus 1"

with mido.open_output(output_port_name) as outport:
    # Obtenir l'heure actuelle au format HH:MM:SS.mmm
    send_time = time.time()
    send_time_formatted = datetime.fromtimestamp(send_time).strftime('%H:%M:%S.%f')[:-3]
    
    # Convertir l'heure en bytes pour l'envoyer en MIDI (ASCII en valeurs décimales)
    timestamp_bytes = [ord(c) for c in send_time_formatted]
    
    # Créer un message SysEx (0xF0 = début, 0xF7 = fin)
    sysex_msg = mido.Message('sysex', data=timestamp_bytes)

    print(f"Envoi du timestamp : {send_time_formatted} via SysEx")
    outport.send(sysex_msg)
