import os
import tensorflow as tf

print(f"--- TensorFlow Version: {tf.__version__} ---")

# Try Method A: Legacy Keras via tf_keras
try:
    import tf_keras
    model = tf_keras.models.load_model("pel_artifacts/model")
    print("✅ METHOD A SUCCESS: Loaded with tf_keras!")
except Exception as e:
    print(f"❌ METHOD A FAILED: {e}\n")

# Try Method B: Native TensorFlow SavedModel
try:
    loaded = tf.saved_model.load("pel_artifacts/model")
    infer = loaded.signatures["serving_default"]
    print("✅ METHOD B SUCCESS: Loaded via tf.saved_model.load!")
except Exception as e:
    print(f"❌ METHOD B FAILED: {e}\n")