import socket
import threading


def send_fen(client_socket):
    while True:
        fen = input("Wpisz notację FEN (lub 'exit' aby wyjść): ")
        if fen.lower() == 'exit':
            break
        client_socket.send(fen.encode())
        print("Notacja FEN wysłana.")


def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024)
            if not message:
                print("Połączenie z serwerem zostało przerwane.")
                break
            print(f"Otrzymano: {message.decode()}")  # Wyświetlanie otrzymanej wiadomości
        except Exception as e:
            print(f"Błąd podczas odbierania wiadomości: {e}")
            break


def main():
    # Tutaj wpisz IP serwera i port, na którym nasłuchuje serwer.
    host = '127.0.0.1'  # Przykładowy adres IP serwera
    port = 65432  # Przykładowy port serwera

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host, port))
        print("Połączono z serwerem.")
        print("Wykonaj ruch lub wyslij wiadomosc:")
        # Uruchomienie wątku nasłuchującego
        receiver_thread = threading.Thread(target=receive_messages, args=(client,))
        receiver_thread.daemon = True
        receiver_thread.start()

        send_fen(client)
    except Exception as e:
        print(f"Nie można połączyć z serwerem: {e}")
    finally:
        client.close()
        print("Połączenie z serwerem zostało zamknięte.")


if __name__ == "__main__":
    main()
