import time
from threading import Thread

# Fonction qui simule une tâche
def task(name, delay):
    print(f"Thread {name} démarré !")
    time.sleep(delay)  # Simule une tâche en dormant un peu
    print(f"Thread {name} terminé après {delay} secondes")

# Création de plusieurs threads
def main():
    threads = []  # Liste pour stocker nos threads
    
    # Créer 3 threads avec des délais différents
    for i in range(1, 4):
        thread = Thread(target=task, args=(f"Tâche {i}", i))
        threads.append(thread)  # Ajouter le thread à la liste
        thread.start()  # Démarrer le thread
    
    # Attendre que tous les threads finissent leur travail
    for thread in threads:
        thread.join()

    print("Tous les threads sont terminés !")

# Lancer le programme principal
if __name__ == "__main__":
    main()
