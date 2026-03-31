# MNIST Digit Classifier

A machine learning project that trains and compares multiple classifiers on the MNIST handwritten digit dataset.

## Models Used
- Random Forest (scikit-learn)
- Support Vector Machine / SVM (scikit-learn)
- Convolutional Neural Network / CNN (TensorFlow/Keras)

## Features
- Full ML pipeline: data loading, EDA, preprocessing, training, evaluation
- Confusion matrix and training history visualizations
- Model accuracy comparison across all three approaches

## Dataset
MNIST is built into TensorFlow/Keras — no manual download needed. It loads automatically when you run the script.

## Setup & Run

```bash
pip install -r requirements.txt
python mnist_classifier.py
```

## Output Files Generated
- `sample_digits.png` — grid of sample MNIST images
- `class_distribution.png` — bar chart of digit class counts
- `confusion_matrix.png` — CNN confusion matrix heatmap
- `training_history.png` — CNN accuracy & loss curves
- `mnist_cnn_model.h5` — saved CNN model weights

## Tech Stack
Python, NumPy, Pandas, Matplotlib, Seaborn, Scikit-learn, TensorFlow/Keras
