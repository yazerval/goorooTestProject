import mido

# Affiche les ports d'entrée MIDI disponibles
print("Ports d'entrée MIDI disponibles :")
for port in mido.get_input_names():
    print(port)

# Affiche les ports de sortie MIDI disponibles
print("\nPorts de sortie MIDI disponibles :")
for port in mido.get_output_names():
    print(port)


