import os
import librosa
import numpy as np
import pickle
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# Dataset path, point this to your GTZAN folder
DATASET_PATH = "Data/genres_original"
MODEL_FILE   = "genre_model.pkl"
ENCODER_FILE = "label_encoder.pkl"

GENRES = [
    "blues", "classical", "country", "disco",
    "hiphop", "jazz", "metal", "pop", "reggae", "rock"
]


# Pull the audio features we care about from a file
def extract_features(file_path):
    audio, sample_rate = librosa.load(file_path, duration=30)

    tempo, _       = librosa.beat.beat_track(y=audio, sr=sample_rate)
    tempo          = float(np.mean(tempo))
    mfccs          = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=13)
    spectral_center = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)
    zero_crossings = librosa.feature.zero_crossing_rate(y=audio)
    harmonics, _   = librosa.effects.hpss(audio)

    features = [
        tempo,
        *np.mean(mfccs, axis=1),
        np.mean(spectral_center),
        np.mean(zero_crossings),
        np.mean(np.abs(harmonics))
    ]
    return np.array(features)


# Walk through the GTZAN folder and build the training data
def load_dataset():
    all_features = []
    all_labels   = []

    for genre in GENRES:
        genre_folder = os.path.join(DATASET_PATH, genre)
        if not os.path.exists(genre_folder):
            print(f"Skipping {genre}, folder not found")
            continue

        for file_name in os.listdir(genre_folder):
            if not file_name.endswith(".wav"):
                continue
            file_path = os.path.join(genre_folder, file_name)
            try:
                features = extract_features(file_path)
                all_features.append(features)
                all_labels.append(genre)
                print(f"Processed: {file_name}")
            except Exception as e:
                print(f"Skipped {file_name}: {e}")

    return np.array(all_features), np.array(all_labels)


# Train the model and save it to disk
def train_model():
    print("Loading dataset, this takes a few minutes...")
    features, labels = load_dataset()

    encoder = LabelEncoder()
    encoded_labels = encoder.fit_transform(labels)

    X_train, X_test, y_train, y_test = train_test_split(
        features, encoded_labels, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    accuracy = accuracy_score(y_test, model.predict(X_test))
    print(f"Model accuracy: {accuracy * 100:.2f}%")

    with open(MODEL_FILE,   "wb") as f: pickle.dump(model,   f)
    with open(ENCODER_FILE, "wb") as f: pickle.dump(encoder, f)

    print("Model saved.")
    return model, encoder


# Load a saved model or train a fresh one if none exists
def load_or_train_model():
    if os.path.exists(MODEL_FILE) and os.path.exists(ENCODER_FILE):
        with open(MODEL_FILE,   "rb") as f: model   = pickle.load(f)
        with open(ENCODER_FILE, "rb") as f: encoder = pickle.load(f)
        print("Loaded existing model.")
    else:
        print("No saved model found, training a new one...")
        model, encoder = train_model()
    return model, encoder


# Classify a single audio file and return the predicted genre
def classify_file(file_path, model, encoder):
    features = extract_features(file_path).reshape(1, -1)
    prediction = model.predict(features)
    return encoder.inverse_transform(prediction)[0]


# GUI

class MusicClassifierApp:
    def __init__(self, root):
        self.root    = root
        self.model, self.encoder = load_or_train_model()
        self.results = []   # list of (filename, genre) tuples

        self.root.title("Music Genre Classifier")
        self.root.geometry("750x520")
        self.root.resizable(False, False)

        self._build_ui()

    def _build_ui(self):
        # Top bar with buttons
        top = tk.Frame(self.root, pady=10)
        top.pack(fill=tk.X, padx=15)

        tk.Button(top, text="Add Music Files",  width=16, command=self.add_files).pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="Classify All",     width=16, command=self.classify_all).pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="Clear",            width=10, command=self.clear_all).pack(side=tk.LEFT, padx=5)

        # Tab switcher for All Files and By Genre
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.all_files_tab = tk.Frame(self.tabs)
        self.by_genre_tab  = tk.Frame(self.tabs)

        self.tabs.add(self.all_files_tab, text="All Files")
        self.tabs.add(self.by_genre_tab,  text="By Genre")

        # All Files tab, simple list
        all_cols = ("File Name", "Genre")
        self.all_files_tree = ttk.Treeview(self.all_files_tab, columns=all_cols, show="headings")
        for col in all_cols:
            self.all_files_tree.heading(col, text=col)
            self.all_files_tree.column(col, width=340)
        self.all_files_tree.pack(fill=tk.BOTH, expand=True)

        all_scroll = ttk.Scrollbar(self.all_files_tab, orient="vertical", command=self.all_files_tree.yview)
        self.all_files_tree.configure(yscrollcommand=all_scroll.set)
        all_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # By Genre tab, grouped by genre and alphabetical within each
        genre_cols = ("Genre", "File Name")
        self.genre_tree = ttk.Treeview(self.by_genre_tab, columns=genre_cols, show="headings")
        for col in genre_cols:
            self.genre_tree.heading(col, text=col)
            self.genre_tree.column(col, width=340)
        self.genre_tree.pack(fill=tk.BOTH, expand=True)

        genre_scroll = ttk.Scrollbar(self.by_genre_tab, orient="vertical", command=self.genre_tree.yview)
        self.genre_tree.configure(yscrollcommand=genre_scroll.set)
        genre_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar at the bottom
        self.status = tk.StringVar(value="Load some music files to get started.")
        tk.Label(self.root, textvariable=self.status, anchor="w", fg="gray").pack(fill=tk.X, padx=15, pady=5)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select audio files",
            filetypes=[("Audio Files", "*.wav *.mp3 *.flac")]
        )
        for path in files:
            name = os.path.basename(path)
            # Don't add duplicates
            if not any(r[0] == name for r in self.results):
                self.results.append((name, path, "Not classified"))

        self._refresh_all_files_view()
        self.status.set(f"{len(self.results)} file(s) loaded. Hit 'Classify All' to run.")

    def classify_all(self):
        if not self.results:
            messagebox.showinfo("Nothing to classify", "Add some music files first.")
            return

        classified = []
        for i, (name, path, _) in enumerate(self.results):
            self.status.set(f"Classifying {i + 1} of {len(self.results)}: {name}")
            self.root.update()
            try:
                genre = classify_file(path, self.model, self.encoder)
            except Exception as e:
                genre = "Error"
                print(f"Failed on {name}: {e}")
            classified.append((name, path, genre))

        self.results = classified
        self._refresh_all_files_view()
        self._refresh_genre_view()
        self.status.set("Done! Switch to the 'By Genre' tab to see sorted results.")

    def _refresh_all_files_view(self):
        # Show files sorted alphabetically by name
        self.all_files_tree.delete(*self.all_files_tree.get_children())
        for name, _, genre in sorted(self.results, key=lambda x: x[0].lower()):
            self.all_files_tree.insert("", tk.END, values=(name, genre))

    def _refresh_genre_view(self):
        # Group by genre, then sort alphabetically within each group
        self.genre_tree.delete(*self.genre_tree.get_children())

        grouped = {}
        for name, _, genre in self.results:
            grouped.setdefault(genre, []).append(name)

        for genre in sorted(grouped.keys()):
            for file_name in sorted(grouped[genre]):
                self.genre_tree.insert("", tk.END, values=(genre, file_name))

    def clear_all(self):
        self.results = []
        self.all_files_tree.delete(*self.all_files_tree.get_children())
        self.genre_tree.delete(*self.genre_tree.get_children())
        self.status.set("Cleared.")


if __name__ == "__main__":
    root = tk.Tk()
    app  = MusicClassifierApp(root)
    root.mainloop()