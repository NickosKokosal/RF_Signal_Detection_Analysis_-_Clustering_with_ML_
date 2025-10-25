# \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ADS-B Offline Analyzer με Clustering & Anomaly Detection
# ADS-B Offline Analyzer with Clustering & Anomaly Detection
# -----------------------------------------------
# Είσοδος: adsb_data.csv (με πεδία time, icao, callsign, altitude, speed)
# Import: adsb_data.csv (με πεδία time, icao, callsign, altitude, speed)
# Έξοδος: clusters.png, anomalies.png
# Export: clusters.png, anomalies.png
# /////////////////////////////////////////////////

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
import numpy as np

# Διαβάζουμε τα δεδομένα από το CSV
# Read tha data from CSV
# df = pd.read_csv("adsb_data.csv")
# df = pd.read_csv("adsb_data.csv", on_bad_lines='warn') shows which line gives error
df = pd.read_csv("adsb_data.csv", on_bad_lines="skip")


# Καθαρίζουμε τα δεδομένα (κρατάμε μόνο έγκυρες τιμές)
# Clean the data (keep only the usefull)
df["altitude"] = pd.to_numeric(df["altitude"], errors="coerce")
df["speed"] = pd.to_numeric(df["speed"], errors="coerce")

# Αντί για dropna σε δύο στήλες, κρατάμε όσες έχουν έστω ένα πεδίο μη κενό
# Instead of dropna in two columns, we keep those that have at least one non-empty field
df = df.dropna(subset=["altitude", "speed"], how="all")


print(f" Records loaded: {len(df)}")

if len(df) < 10:
    print("Not a lot data clustering. Let it take more.")
    exit()

# Clustering των πτήσεων (KMeans)
# Clustering of the flights (KMeans)
# Αντικαθιστούμε NaN με τη μέση τιμή της στήλης (safe imputation)
# Replace NaN with the average value of the column (safe imputation)
df["altitude"] = df["altitude"].fillna(df["altitude"].mean())
df["speed"] = df["speed"].fillna(df["speed"].mean())

# Τώρα δεν υπάρχουν NaN
# Now there are no NaNs
X = df[["altitude", "speed"]].values

# Εκτέλεση KMeans
kmeans = KMeans(n_clusters=3, random_state=42)
df["cluster"] = kmeans.fit_predict(X)


# Οπτικοποίηση clusters
# Visualization of the clusters
plt.figure(figsize=(8,6))
for c in df["cluster"].unique():
    cluster_data = df[df["cluster"] == c]
    plt.scatter(cluster_data["speed"], cluster_data["altitude"], label=f"Cluster {c}", s=30)
plt.xlabel("Speed (knots)")
plt.ylabel("Altitude (ft)")
plt.title("ADS-B Flight Clusters")
plt.legend()
plt.grid(True)
plt.savefig("clusters.png")
print(" Saved plot: clusters.png")

# Εντοπισμός ανωμαλιών (Isolation Forest)
# Anomalies detection
iso = IsolationForest(contamination=0.1, random_state=42)
df["anomaly"] = iso.fit_predict(X)

# Οπτικοποίηση ανωμαλιών
# Visualization of the anomalies
plt.figure(figsize=(8,6))
normal = df[df["anomaly"] == 1]
anomalies = df[df["anomaly"] == -1]
plt.scatter(normal["speed"], normal["altitude"], color="blue", s=25, label="Normal")
plt.scatter(anomalies["speed"], anomalies["altitude"], color="red", s=40, label="Anomaly")
plt.xlabel("Speed (knots)")
plt.ylabel("Altitude (ft)")
plt.title("Anomaly Detection (Isolation Forest)")
plt.legend()
plt.grid(True)
plt.savefig("anomalies.png")
print(" Saved plot: anomalies.png ")

# Εξαγωγή αναφοράς
# Report Export
df.to_csv("adsb_analyzed.csv", index=False)
print(" Saved analyzed data to adsb_analyzed.csv ")

# Γρήγορη σύνοψη
# Quick summary
print("\n=== Summary ===")
print(df.groupby("cluster")[["altitude", "speed"]].mean())
print(f"\n Anomalies detected: {len(anomalies)}")

