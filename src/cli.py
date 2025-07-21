import sys

def main():
    if len(sys.argv) < 2:
        print("Kullanım: kairos <komut>")
        return
    komut = sys.argv[1]
    if komut == "start":
        print("Kairos daemon başlatılıyor...")
    elif komut == "status":
        print("Kairos durumu: Çalışıyor")
    else:
        print(f"Bilinmeyen komut: {komut}")

if __name__ == "__main__":
    main() 