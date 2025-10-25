# adsb_logger_mac.py
# για να τρεξει στο ενα terminal δινω =>
# running the programm from the terminal with
# /opt/homebrew/Cellar/dump1090-mutability/*/bin/dump1090 --interactive --net

##!/usr/bin/env python3
# == coding: utf-8 ==
#
# ===============================================
# ADS-B Logger (Enhanced)
# ===============================================
# Συνδέεται σε dump1090 (localhost:30003)
# Διαβάζει γραμμές τύπου MSG (SBS format)
# Εξάγει altitude, speed, lat, lon, callsign, ICAO
# Κατατάσσει το αντικείμενο (drone / airplane / helicopter / ground)
# Εκτυπώνει στην κονσόλα και αποθηκεύει περιοδικά σε CSV / SQLite
#Connects to dump1090 (localhost:30003)
# Reads MSG lines (SBS format)
# Extracts altitude, speed, lat, lon, callsign, ICAO
# Classifies the object (drone / airplane / helicopter / ground)
# Prints to the console and periodically saves to CSV / SQLite
# ===============================================

import socket         # για επικοινωνία μέσω TCP (σύνδεση με dump1090) # for communication via TCP (connection to dump1090)
import pandas as pd   # για χειρισμό και αποθήκευση δεδομένων # for data manipulation and storage
import sqlite3        # για SQLite βάση δεδομένων # for the SQL database
import os             # για έλεγχο αρχείων # archives check
import argparse       # για command-line παραμέτρους # for command-line parameters
from datetime import datetime
from typing import Optional

# ---------------------------
# Προεπιλεγμένες ρυθμίσεις
# Default settings
# ---------------------------

HOST = "127.0.0.1"     # διεύθυνση IP όπου τρέχει το dump1090 (localhost) # IP address where dump1090 is running (localhost)
PORT = 30003           # θύρα SBS (Standard Broadcast Service) # SBS (Standard Broadcast Service) port
SAVE_CSV_EVERY = 50    # κάθε 50 εγγραφές γράφει στο CSV # every 50 records writes to CSV
CSV_FILE = "adsb_data.csv"     # όνομα αρχείου για τα δεδομένα # filename for the data
SQLITE_FILE = "adsb_data.sqlite"  # SQLite αρχείο # SQLite archive
USE_SQLITE = True       # ενεργοποίηση αποθήκευσης σε SQLite # enable storage in SQLite
VERBOSE = True          # αν True => δείχνει live τις εγγραφές στην κονσόλα # if True => shows live recordings in the console

# ---------------------------
# Συνάρτηση μετατροπής σε float
#
# ---------------------------
def to_float(x: str) -> Optional[float]:
    """
    Μετατρέπει string σε float (π.χ. "12345" -> 12345.0).
    Αν δεν είναι αριθμός, επιστρέφει None.
    """
    try:
        if x is None:
            return None
        x = x.strip()  # αφαίρεση κενών # delete gaps
        if x == "" or x.upper() == "NAN":  # αγνόηση NaN # ignore NaN
            return None
        return float(x)
    except Exception:
        return None  # σε οποιοδήποτε σφάλμα parsing # to every parsing error

# ---------------------------
# Κατηγοριοποίηση αντικειμένου
#  Object Clustering
# ---------------------------
def classify_object(alt: Optional[float], spd: Optional[float]) -> str:
    """
    Απλοί κανόνες για ταξινόμηση αντικειμένων:
    Drone / Helicopter / Airplane / Ground / Unknown
    Με βάση ύψος (altitude) και ταχύτητα (speed).
    """

    # Αν δεν υπάρχουν καθόλου δεδομένα # If there are no data
    if alt is None and spd is None:
        return "Unknown"

    # Κριτήρια ανάλογα με το ύψος # Altitude Criteria
    if alt is not None:
        if alt <= 50 and (spd is None or spd <= 40):
            return "Ground"
        if alt <= 400 and spd is not None and spd <= 60:
            return "Drone"
        if alt <= 3000 and (spd is None or spd < 170):
            if spd is not None and spd < 120:
                return "Helicopter"
            else:
                return "Airplane"
        if alt > 3000:
            return "Airplane"

    # Αν δεν υπάρχει ύψος, χρησιμοποιούμε μόνο την ταχύτητα # If there is no altitude we use only the speed
    if spd is not None:
        if spd < 10:
            return "Ground"
        if spd < 60:
            return "Drone"
        if spd < 200:
            return "Airplane"

    return "Unknown"

# ---------------------------
#  Δημιουργία SQLite βάσης
#  SQLite database creation
# ---------------------------
def init_sqlite(dbfile: str):
    """
    Δημιουργεί SQLite βάση (αν δεν υπάρχει) με πίνακα adsb.
    """
    conn = sqlite3.connect(dbfile)  # άνοιγμα ή δημιουργία βάσης # datase creation or opening
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS adsb (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            icao TEXT,
            callsign TEXT,
            altitude REAL,
            lat REAL,
            lon REAL,
            speed REAL,
            classification TEXT
        )
    """)  # δημιουργία πίνακα με τις στήλες που χρειαζόμαστε # Board creation with the usefull columns
    conn.commit()
    return conn

# ---------------------------
# Κύριος Logger # Basic logger
# ---------------------------
def run_logger(host=HOST, port=PORT, csv_file=CSV_FILE, sqlite_file=SQLITE_FILE,
               save_csv_every=SAVE_CSV_EVERY, use_sqlite=USE_SQLITE):
    """
    Συνδέεται στο dump1090 και αρχίζει να λαμβάνει δεδομένα.
    Τα αποθηκεύει σε CSV και (προαιρετικά) σε SQLite.
    """

    # Δημιουργούμε σύνδεση TCP με το dump1090 # TCP connnection creation with the dump1090
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f" Connecting to {host}:{port} ...")
    sock.connect((host, port))
    print(" Connected.")

    # Αν επιλέχθηκε, ανοίγει SQLite # If the choise is made, it opens the SQLite
    conn = None
    if use_sqlite:
        conn = init_sqlite(sqlite_file)
        print(f" SQLite DB ready: {sqlite_file}")

    rows = []

    try:
        buffer = ""  # αποθήκευση τυχόν μισών γραμμών
        while True:
            data = sock.recv(4096)  # λαμβάνει bytes από το dump1090 # receives bytes from dump1090
            if not data:
                print(" Connection closed by remote.")
                break

            # Μετατροπή των bytes σε string # Convert bytes to string
            chunk = data.decode("utf-8", errors="ignore")
            buffer += chunk

            # Διαχωρισμός σε γραμμές (κάθε μήνυμα είναι μία γραμμή) # Line separation (each message is one line)
            lines = buffer.split("\n")
            buffer = lines.pop()  # κρατάμε το υπόλοιπο (αν κοπεί στη μέση) # keep the rest (if cut in half)

            # Επεξεργασία κάθε πλήρους γραμμής # Edit each complete line
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if not line.startswith("MSG"):
                    continue  # αγνοούμε γραμμές που δεν είναι MSG # ignore lines that are not MSG

                parts = line.split(",")
                if len(parts) < 16:
                    continue  # όχι αρκετά πεδία # not enough fields

                # Απόπειρα εξαγωγής βασικών πληροφοριών # Attempt to extract basic information
                try:
                    icao = parts[4].strip()        # ICAO hex code του αεροσκάφους # ICAO hex code of the aircraft
                    callsign = parts[10].strip() if parts[10] else ""  # flight number
                    altitude = to_float(parts[11])
                    speed = to_float(parts[12])
                    lat = to_float(parts[14])
                    lon = to_float(parts[15])
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

                # Κατηγοριοποίηση του αντικειμένου # Categorization of the object
                classification = classify_object(altitude, speed)

                # Εμφάνιση στην κονσόλα (αν VERBOSE = True) # Display in console (if VERBOSE = True)
                if VERBOSE:
                    print(f"{ts} | {icao:6} | {callsign:8} | "
                          f"alt={altitude if altitude else '-':>6} ft | "
                          f"spd={speed if speed else '-':>6} kt | "
                          f"{classification:10} | "
                          f"lat={lat if lat else '-'} lon={lon if lon else '-'}")

                # Αποθήκευση στη μνήμη # Save to memory
                rows.append({
                    "time": ts,
                    "icao": icao,
                    "callsign": callsign,
                    "altitude": altitude,
                    "lat": lat,
                    "lon": lon,
                    "speed": speed,
                    "classification": classification
                })

                # Αν ενεργό SQLite, αποθηκεύουμε άμεσα # If SQLite is active, save immediately
                if use_sqlite and conn is not None:
                    try:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO adsb (ts, icao, callsign, altitude, lat, lon, speed, classification)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (ts, icao, callsign, altitude, lat, lon, speed, classification))
                        conn.commit()
                    except Exception as e:
                        print("SQLite insert error:", e)

                # Κάθε N εγγραφές γράφουμε CSV # Every N records we write CSV
                if len(rows) >= save_csv_every:
                    try:
                        df = pd.DataFrame(rows)
                        if os.path.exists(csv_file):
                            df.to_csv(csv_file, mode="a", header=False, index=False)
                        else:
                            df.to_csv(csv_file, mode="w", header=True, index=False)
                        print(f"💾 Saved {len(rows)} rows to {csv_file}")
                        rows = []  # καθαρισμός buffer # buffer clearing
                    except Exception as e:
                        print("CSV save error:", e)

    # Αν ο χρήστης πατήσει Ctrl+C => σταμάτα καθαρά # If the user presses Ctrl+C => stop cleanly
    except KeyboardInterrupt:
        print("\n User requested stop (Ctrl+C). Shutting down...")

    # Αν άλλο απρόβλεπτο σφάλμα # If another unexpected error
    except Exception as e:
        print("️ Unexpected error:", e)

    finally:
        # Κλείσιμο όλων # Close all
        try:
            sock.close()
        except:
            pass
        if conn:
            conn.close()

        # Τελευταίο γράψιμο υπολοίπων # Last write of remainders
        if rows:
            try:
                df = pd.DataFrame(rows)
                if os.path.exists(csv_file):
                    df.to_csv(csv_file, mode="a", header=False, index=False)
                else:
                    df.to_csv(csv_file, mode="w", header=True, index=False)
                print(f"💾 Final save: {len(rows)} rows appended to {csv_file}")
            except Exception as e:
                print("Final CSV save error:", e)

# ---------------------------
# Command-line interface
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ADS-B enhanced logger.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--csv", default=CSV_FILE)
    parser.add_argument("--sqlite", default=SQLITE_FILE)
    parser.add_argument("--no-sqlite", action="store_true", help="Disable SQLite saving")
    parser.add_argument("--batch", type=int, default=SAVE_CSV_EVERY, help="Rows per CSV save")
    args = parser.parse_args()

    # Εκκίνηση με τις επιλεγμένες παραμέτρους # Start with the selected parameters
    run_logger(host=args.host, port=args.port, csv_file=args.csv,
               sqlite_file=args.sqlite, save_csv_every=args.batch,
               use_sqlite=(not args.no_sqlite))
