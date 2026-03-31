import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, Dropout, Conv2D, MaxPooling2D
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.datasets import mnist


# Load the dataset
(train_images, train_labels), (test_images, test_labels) = mnist.load_data()
print(f"Training samples : {train_images.shape[0]}")
print(f"Test samples     : {test_images.shape[0]}")


# Peek at a few digits to sanity check the data
fig, axes = plt.subplots(2, 5, figsize=(10, 4))
for i, ax in enumerate(axes.flat):
    ax.imshow(train_images[i], cmap='gray')
    ax.set_title(f"Label: {train_labels[i]}")
    ax.axis('off')
plt.suptitle("Sample MNIST Digits")
plt.tight_layout()
plt.savefig("sample_digits.png", dpi=150)
plt.show()

# Check if classes are balanced
plt.figure(figsize=(8, 4))
sns.countplot(x=train_labels, palette='muted')
plt.title("How many samples per digit?")
plt.xlabel("Digit")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig("class_distribution.png", dpi=150)
plt.show()


# Normalize pixels to 0-1 range
train_images = train_images / 255.0
test_images  = test_images  / 255.0

# Flatten for sklearn models
train_flat = train_images.reshape(train_images.shape[0], -1)
test_flat  = test_images.reshape(test_images.shape[0], -1)

# Sklearn trains slowly on 60k samples, so we cap it at 10k
train_flat_small   = train_flat[:10000]
train_labels_small = train_labels[:10000]

# Reshape for CNN input
train_cnn = train_images.reshape(-1, 28, 28, 1)
test_cnn  = test_images.reshape(-1, 28, 28, 1)

train_labels_ohe = to_categorical(train_labels, num_classes=10)
test_labels_ohe  = to_categorical(test_labels,  num_classes=10)


# Train a Random Forest
print("\n--- Random Forest ---")
rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
rf.fit(train_flat_small, train_labels_small)

rf_predictions = rf.predict(test_flat)
rf_accuracy    = accuracy_score(test_labels, rf_predictions)
print(f"Accuracy : {rf_accuracy * 100:.2f}%")
print(classification_report(test_labels, rf_predictions))


# Train an SVM
print("\n--- SVM ---")
svm = SVC(kernel='rbf', C=5, gamma='scale', random_state=42)
svm.fit(train_flat_small, train_labels_small)

svm_predictions = svm.predict(test_flat)
svm_accuracy    = accuracy_score(test_labels, svm_predictions)
print(f"Accuracy : {svm_accuracy * 100:.2f}%")
print(classification_report(test_labels, svm_predictions))


# Build and train a CNN
print("\n--- CNN ---")
cnn = Sequential([
    Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    MaxPooling2D((2, 2)),
    Conv2D(64, (3, 3), activation='relu'),
    MaxPooling2D((2, 2)),
    Flatten(),
    Dense(128, activation='relu'),
    Dropout(0.3),
    Dense(10, activation='softmax')
])

cnn.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
cnn.summary()

history = cnn.fit(
    train_cnn, train_labels_ohe,
    epochs=10,
    batch_size=128,
    validation_split=0.1,
    verbose=1
)

_, cnn_accuracy = cnn.evaluate(test_cnn, test_labels_ohe, verbose=0)
print(f"CNN Test Accuracy : {cnn_accuracy * 100:.2f}%")


# Confusion matrix to see where the CNN gets confused
cnn_predictions = np.argmax(cnn.predict(test_cnn), axis=1)
cm = confusion_matrix(test_labels, cnn_predictions)

plt.figure(figsize=(9, 7))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=range(10), yticklabels=range(10))
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("CNN Confusion Matrix")
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=150)
plt.show()

# Plot how training went over the epochs
plt.figure(figsize=(10, 4))

plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'],     label='Train')
plt.plot(history.history['val_accuracy'], label='Validation')
plt.title("Accuracy over epochs")
plt.xlabel("Epoch")
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(history.history['loss'],     label='Train')
plt.plot(history.history['val_loss'], label='Validation')
plt.title("Loss over epochs")
plt.xlabel("Epoch")
plt.legend()

plt.tight_layout()
plt.savefig("training_history.png", dpi=150)
plt.show()


# Final comparison
print("\n========= Results =========")
print(f"Random Forest : {rf_accuracy  * 100:.2f}%")
print(f"SVM           : {svm_accuracy * 100:.2f}%")
print(f"CNN           : {cnn_accuracy * 100:.2f}%")
print("===========================")

cnn.save("mnist_cnn_model.h5")
print("Model saved -> mnist_cnn_model.h5")