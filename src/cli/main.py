import sys
import subprocess
import time
import requests
import os
import signal
import platform
import asyncio
import json
from datetime import datetime
from pathlib import Path

def is_process_running(pid):
    """PID'ye sahip sürecin çalışıp çalışmadığını kontrol et"""
    try:
        if platform.system() == "Windows":
            # Windows için tasklist kullan
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5
            )
            return str(pid) in result.stdout
        else:
            # Linux/macOS için os.kill ile signal 0 gönder
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False
    except Exception as e:
        print(f"Process check error: {e}")
        return False

def print_banner():
    banner = """
    ██╗  ██╗ █████╗ ██╗██████╗  ██████╗ ███████╗
    ██║ ██╔╝██╔══██╗██║██╔══██╗██╔═══██╗██╔════╝
    █████╔╝ ███████║██║██████╔╝██║   ██║███████╗
    ██╔═██╗ ██╔══██║██║██╔══██╗██║   ██║╚════██║
    ██║  ██╗██║  ██║██║██║  ██║╚██████╔╝███████║
    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
    
    🌌 The Context Keeper - Autonomous Development Supervisor
    """
    print(banner)

def start_daemon():
    print("🚀 Kairos daemon başlatılıyor...")
    
    try:
        # Önce mevcut daemon kontrolü
        if os.path.exists(".kairos.pid"):
            with open(".kairos.pid", "r") as f:
                pid = int(f.read().strip())
            
            # Sürecin çalışıp çalışmadığını kontrol et
            if is_process_running(pid):
                print("⚠️ Kairos daemon zaten çalışıyor!")
                print(f"📍 PID: {pid}")
                print("🌐 Dashboard: http://localhost:8000/dashboard")
                return
            else:
                # Eski PID dosyasını temizle
                os.remove(".kairos.pid")
        
        # UTF-8 encoding zorlaması için environment ayarla
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"  # Python 3.7+ için ek UTF-8 mod
        
        # Daemon'u arka planda başlat
        process = subprocess.Popen(
            [sys.executable, "src/main.py"], 
            cwd=".",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        
        # PID'yi kaydet
        with open(".kairos.pid", "w") as f:
            f.write(str(process.pid))
            
        print(f"✅ Daemon başlatıldı (PID: {process.pid})")
        print("📍 Port: 8000")
        print("🌐 Dashboard: http://localhost:8000/dashboard")
        print("📖 API Docs: http://localhost:8000/docs")
        print("\n💡 Durdurmak için: kairos stop")
        
    except Exception as e:
        print(f"❌ Hata: {e}")

def check_status():
    # Önce PID dosyası kontrolü
    if os.path.exists(".kairos.pid"):
        with open(".kairos.pid", "r") as f:
            pid = int(f.read().strip())
        
        if is_process_running(pid):
            print(f"✅ Kairos daemon çalışıyor (PID: {pid})")
        else:
            print(f"⚠️ PID dosyası var ama süreç çalışmıyor (PID: {pid})")
            print("🧹 Eski PID dosyası temizleniyor...")
            os.remove(".kairos.pid")
            print("❌ Kairos durumu: ÇALIŞMIYOR")
            print("💡 Başlatmak için: kairos start")
            return
    else:
        print("❌ Kairos durumu: ÇALIŞMIYOR (PID dosyası bulunamadı)")
        print("💡 Başlatmak için: kairos start")
        return
    
    # API durum kontrolü
    try:
        response = requests.get("http://localhost:8000/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("🌐 API durumu: ERIŞILEBILIR")
            print(f"📊 Context Engine: {data['context_engine']}")
            print(f"🤖 Agents: {len(data['agents'])} active")
            print(f"💾 Memory Systems: {len(data['memory_systems'])} connected")
            print("🌐 Dashboard: http://localhost:8000/dashboard")
        else:
            print("⚠️ Daemon çalışıyor ama API yanıt vermiyor")
    except requests.exceptions.ConnectionError:
        print("⚠️ Daemon çalışıyor ama API'ye bağlanılamıyor")
        print("💡 Birkaç saniye bekleyip tekrar deneyin")
    except Exception as e:
        print(f"❌ API durum kontrolü hatası: {e}")

def init_code_graph(target_path=None):
    """Initialize Kairos project and build initial code graph"""
    print("🌟 Kairos kod grafı oluşturuluyor...")
    
    try:
        # Add src to Python path for imports
        import sys
        from pathlib import Path
        
        # Get the current script directory and add src to path
        current_dir = Path(__file__).parent.parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        
        # Import required modules
        from src.core.code_parser import code_parser
        from src.memory.ast_converter import ast_converter
        
        # Get project path (either provided or current directory)
        if target_path:
            project_path = os.path.abspath(target_path)
            if not os.path.exists(project_path):
                print(f"❌ Belirtilen yol bulunamadı: {project_path}")
                return
            print(f"📂 Hedef proje dizini: {project_path}")
        else:
            project_path = os.getcwd()
            print(f"📂 Mevcut proje dizini: {project_path}")
        
        # Save active project path to persistent configuration
        try:
            # Create .kairos directory in user's home if it doesn't exist
            kairos_config_dir = Path.home() / ".kairos"
            kairos_config_dir.mkdir(exist_ok=True)
            
            # Save active project configuration
            active_project_config = {
                "active_project_path": project_path,
                "project_id": f"kairos_project_{int(time.time())}",
                "last_updated": datetime.now().isoformat(),
                "project_name": os.path.basename(project_path)
            }
            
            active_project_file = kairos_config_dir / "active_project.json"
            with open(active_project_file, 'w', encoding='utf-8') as f:
                json.dump(active_project_config, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Aktif proje konfigürasyonu kaydedildi: {active_project_file}")
            print(f"🆔 Proje ID: {active_project_config['project_id']}")
            
        except Exception as config_error:
            print(f"⚠️ Aktif proje konfigürasyonu kaydedilemedi: {config_error}")
            print("📍 Sistem yine de çalışacak ancak proje izolasyonu olmayabilir")
        
        print("🔍 Kod dosyaları taranıyor...")
        
        # Parse entire project directory
        nodes, relationships = code_parser.parse_directory(project_path)
        
        print(f"✅ {len(nodes)} kod düğümü, {len(relationships)} ilişki bulundu")
        
        if nodes or relationships:
            print("📊 Neo4j'ye kod grafı yükleniyor...")
            
            try:
                # Clear existing code data first
                ast_converter.clear_all_code_data()
                
                # Sync to Neo4j
                success = ast_converter.sync_to_neo4j(nodes, relationships)
                
                if success:
                    print("✅ Kod grafı başarıyla oluşturuldu!")
                    
                    # Get statistics
                    stats = ast_converter.get_graph_statistics()
                    print("\n📈 Graf İstatistikleri:")
                    print(f"  📄 Modüller: {stats.get('modules', 0)}")
                    print(f"  🏗️ Sınıflar: {stats.get('classes', 0)}")
                    print(f"  ⚙️ Fonksiyonlar: {stats.get('functions', 0)}")
                    print(f"  📦 İmportlar: {stats.get('imports', 0)}")
                    print(f"  🔗 Toplam İlişki: {stats.get('total_relationships', 0)}")
                    
                    print("\n🎯 Kairos projesi hazır!")
                    print("💡 Şimdi 'kairos start' ile daemon'u başlatabilirsiniz")
                    
                else:
                    print("⚠️ Neo4j bağlantısı kurulamadı, kod grafı Neo4j'ye yüklenemedi")
                    print("🎯 Ancak Kairos diğer özelliklerle çalışmaya devam edebilir!")
                    print("💡 'kairos start' ile daemon'u başlatabilirsiniz")
                    
            except Exception as neo_error:
                print(f"⚠️ Neo4j hatası: {str(neo_error)[:100]}...")
                print("🎯 Neo4j olmadan da Kairos çalışabilir!")
                print("💡 'kairos start' ile daemon'u başlatabilirsiniz")
        else:
            print("⚠️ Analiz edilebilir kod dosyası bulunamadı")
            
    except ImportError as e:
        print(f"❌ Gerekli modüller yüklenemedi: {e}")
        print("💡 Neo4j ve gerekli Python paketlerinin kurulu olduğunu kontrol edin")
    except Exception as e:
        print(f"❌ Başlatma hatası: {e}")

def show_help():
    help_text = """
🌌 Kairos: The Context Keeper - Komutlar

Kullanım:
  kairos <komut> [parametreler]

Mevcut Komutlar:
  init       🌟 Proje kodlarını analiz et ve kod grafı oluştur
  start      🚀 Kairos daemon'unu başlat
  status     📊 Sistem durumunu kontrol et
  stop       🛑 Daemon'unu durdur
  restart    🔄 Daemon'unu yeniden başlat
  backup     💾 Veri yedekleme işlemi
  restore    🔄 Veri geri yükleme işlemi
  help       ❓ Bu yardım mesajını göster

Yedekleme Komutları:
  backup               Tam yedekleme oluştur
  backup --name X      X ismiyle yedekleme oluştur
  backup --list        Mevcut yedeklemeleri listele
  backup --cleanup N   Son N yedeklemeyi sakla, gerisini sil

Geri Yükleme Komutları:
  restore backup_name          Yedeklemeden geri yükle
  restore --list               Mevcut yedeklemeleri listele
  restore --validate X         X yedeklemesini doğrula
  restore backup_name --neo4j  Sadece Neo4j verilerini geri yükle

Örnekler:
  kairos start
  kairos status
  kairos backup
  kairos backup --name sprint6_backup
  kairos restore kairos_backup_20241223_143022
  kairos help

Daha fazla bilgi için:
  🌐 Dashboard: http://localhost:8000/dashboard
  📖 Docs: http://localhost:8000/docs
    """
    print(help_text)

def stop_daemon():
    print("🛑 Kairos daemon durduruluyor...")
    try:
        if not os.path.exists(".kairos.pid"):
            print("ℹ️ Çalışan daemon bulunamadı (.kairos.pid dosyası yok)")
            return
            
        with open(".kairos.pid", "r") as f:
            pid = int(f.read().strip())
            
        # Sürecin çalışıp çalışmadığını kontrol et
        if not is_process_running(pid):
            print(f"ℹ️ PID {pid} ile çalışan süreç bulunamadı")
            os.remove(".kairos.pid")
            return
            
        # İşletim sistemine göre süreci sonlandır
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
        else:
            os.kill(pid, signal.SIGTERM)
            
        # PID dosyasını sil
        os.remove(".kairos.pid")
        print(f"✅ Daemon durduruldu (PID: {pid})")
        
    except FileNotFoundError:
        print("ℹ️ PID dosyası bulunamadı, daemon zaten durmuş olabilir")
    except subprocess.CalledProcessError:
        print("❌ Süreci sonlandırma başarısız oldu")
    except Exception as e:
        print(f"❌ Durdurma hatası: {e}")

def run_backup():
    """Run backup command"""
    print("💾 Kairos yedekleme başlatılıyor...")
    
    try:
        # Get script directory
        script_dir = Path(__file__).parent.parent / "scripts"
        backup_script = script_dir / "backup.py"
        
        if not backup_script.exists():
            print(f"❌ Yedekleme scripti bulunamadı: {backup_script}")
            return
        
        # Prepare command arguments
        cmd_args = [sys.executable, str(backup_script)]
        
        # Add additional arguments if provided
        if len(sys.argv) > 2:
            cmd_args.extend(sys.argv[2:])
        
        # Run backup script
        result = subprocess.run(cmd_args, cwd=str(script_dir.parent))
        
        if result.returncode == 0:
            print("✅ Yedekleme tamamlandı!")
        else:
            print(f"❌ Yedekleme başarısız (çıkış kodu: {result.returncode})")
            
    except Exception as e:
        print(f"❌ Yedekleme hatası: {e}")

def run_restore():
    """Run restore command"""
    print("🔄 Kairos geri yükleme başlatılıyor...")
    
    try:
        # Get script directory
        script_dir = Path(__file__).parent.parent / "scripts"
        restore_script = script_dir / "restore.py"
        
        if not restore_script.exists():
            print(f"❌ Geri yükleme scripti bulunamadı: {restore_script}")
            return
        
        # Prepare command arguments
        cmd_args = [sys.executable, str(restore_script)]
        
        # Add additional arguments if provided
        if len(sys.argv) > 2:
            cmd_args.extend(sys.argv[2:])
        
        # Run restore script
        result = subprocess.run(cmd_args, cwd=str(script_dir.parent))
        
        if result.returncode == 0:
            print("✅ Geri yükleme tamamlandı!")
        else:
            print(f"❌ Geri yükleme başarısız (çıkış kodu: {result.returncode})")
            
    except Exception as e:
        print(f"❌ Geri yükleme hatası: {e}")

def init_project():
    """Initialize a new Kairos project"""
    print("🌌 Yeni Kairos projesi başlatılıyor...")
    
    try:
        # Create project structure
        project_dirs = [
            ".kiro",
            "configs",
            "logs",
            "data",
            "backups"
        ]
        
        for dir_name in project_dirs:
            Path(dir_name).mkdir(exist_ok=True)
            print(f"📁 Klasör oluşturuldu: {dir_name}")
        
        # Create initial configuration files
        kiro_config = {
            "project": {
                "name": "My Kairos Project",
                "version": "1.0.0",
                "created_at": datetime.now().isoformat()
            },
            "agents": {
                "enabled": ["ResearchAgent", "ExecutionAgent", "GuardianAgent"],
                "default_priority": "medium"
            },
            "memory": {
                "neo4j_enabled": True,
                "qdrant_enabled": True,
                "backup_enabled": True
            }
        }
        
        config_file = Path(".kiro/config.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(kiro_config, f, indent=2, ensure_ascii=False)
        print(f"⚙️ Konfigürasyon dosyası oluşturuldu: {config_file}")
        
        # Create initial steering document
        steering_content = """# Proje Yönlendirme Dokümanı

## Proje Hedefleri
- Bu alanda projenizin ana hedeflerini belirtin
- Kairos ajanlarının odaklanması gereken konuları listeleyin

## Öncelikler
1. Yüksek öncelikli görevler
2. Orta öncelikli görevler  
3. Düşük öncelikli görevler

## Kısıtlamalar ve Kurallar
- Güvenlik gereksinimleri
- Performans hedefleri
- Kod kalite standartları
"""
        
        steering_file = Path(".kiro/steering.md")
        with open(steering_file, 'w', encoding='utf-8') as f:
            f.write(steering_content)
        print(f"📋 Yönlendirme dokümanı oluşturuldu: {steering_file}")
        
        # Create specs document
        specs_content = """# Teknik Spesifikasyonlar

## Sistem Gereksinimleri
- Python 3.8+
- Neo4j veritabanı
- Qdrant vektör veritabanı

## API Spesifikasyonları
- FastAPI tabanlı REST API
- WebSocket desteği
- MCP (Model Context Protocol) entegrasyonu

## Agent Konfigürasyonları

### ResearchAgent
- Web araştırması
- Wikipedia entegrasyonu
- GitHub API kullanımı

### ExecutionAgent  
- Dosya sistemi operasyonları
- Terminal komutları
- Kod üretimi

### GuardianAgent
- Kod kalite kontrolü
- Güvenlik doğrulaması
- Output validasyonu
"""
        
        specs_file = Path(".kiro/specs.md")
        with open(specs_file, 'w', encoding='utf-8') as f:
            f.write(specs_content)
        print(f"📋 Spesifikasyon dokümanı oluşturuldu: {specs_file}")
        
        # Create .gitignore if it doesn't exist
        gitignore_content = """# Kairos specific
.kairos.pid
logs/*.log
backups/*.tar.gz
data/temp/*

# Python
__pycache__/
*.py[cod]
*.$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
env/
venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
        
        gitignore_file = Path(".gitignore")
        if not gitignore_file.exists():
            with open(gitignore_file, 'w') as f:
                f.write(gitignore_content)
            print(f"📋 .gitignore dosyası oluşturuldu: {gitignore_file}")
        
        print("\n✅ Kairos projesi başarıyla başlatıldı!")
        print("\n📋 Sonraki adımlar:")
        print("   1. .kiro/steering.md dosyasını düzenleyerek proje hedeflerinizi belirtin")
        print("   2. .kiro/specs.md dosyasını düzenleyerek teknik spesifikasyonları güncelleyin")
        print("   3. 'kairos start' komutuyla sistemi başlatın")
        print("   4. http://localhost:8000/dashboard adresinden dashboard'a erişin")
        
    except Exception as e:
        print(f"❌ Proje başlatma hatası: {e}")

def main():
    if len(sys.argv) < 2:
        print_banner()
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        print_banner()
        start_daemon()
    elif command == "status":
        print_banner()
        check_status()
    elif command == "stop":
        stop_daemon()
    elif command == "restart":
        stop_daemon()
        time.sleep(2)
        start_daemon()
    elif command == "init":
        print_banner()
        # Check for --path parameter
        target_path = None
        if len(sys.argv) > 2:
            if sys.argv[2] == "--path" and len(sys.argv) > 3:
                target_path = sys.argv[3]
            else:
                # If other parameters provided but not --path, show error
                print("❌ Geçersiz parametre. Kullanım: kairos init [--path /path/to/project]")
                return
        # Call the correct init function that builds code graph
        init_code_graph(target_path)
    elif command == "backup":
        run_backup()
    elif command == "restore":
        run_restore()
    elif command in ["help", "-h", "--help"]:
        print_banner()
        show_help()
    else:
        print(f"❌ Bilinmeyen komut: {command}")
        print("💡 Kullanılabilir komutlar için: kairos help")

if __name__ == "__main__":
    main()
