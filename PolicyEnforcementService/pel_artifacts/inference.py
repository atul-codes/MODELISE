import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences
import sentencepiece as spm
import json
import keras
import numpy as np

# Load model
model = keras.layers.TFSMLayer("pel_artifacts/model", call_endpoint="serving_default")

# Load tokenizer
sp = spm.SentencePieceProcessor()
sp.load("pel_artifacts/tokenizers/pel_tokenizer.model")

# Load config
with open("pel_artifacts/config.json") as f:
    config = json.load(f)

max_len = config["max_len"]
threshold = config["threshold"]

def normalize_text(text):
    import re, unicodedata
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r'[\W_]+', '', text)
    return text

def encode_spm(text, max_len):
    ids = sp.encode(str(text), out_type=int)
    return pad_sequences(
        [ids],
        maxlen=max_len,
        padding="post",
        truncating="post"
    )


def predict_text_policy(text: str):
    """
    Core PEL inference function.
    This is what your gRPC Inspect() method should call.
    """

    if text is None or not str(text).strip():
        return {
            "risk_score": 0.0,
            "action": "ALLOW",
            "details": ["empty_input"]
        }

    text = str(text)

    raw_seq = encode_spm(text, max_len)
    raw_prob = float(model.predict(raw_seq, verbose=0)[0][0])

    norm_text = normalize_text(text)
    norm_seq = encode_spm(norm_text, max_len)
    norm_prob = float(model.predict(norm_seq, verbose=0)[0][0])

    final_risk = max(raw_prob, norm_prob)

    if final_risk >= 0.60:
        action = "BLOCK"
    else:
        action = "ALLOW"

    return {
        "action": action,
    }


import io
import torch
from PIL import Image
from transformers import AutoModelForImageClassification, ViTImageProcessor

# NOTE: previously named `model` / `processor`, identical to the text
# model's globals above - the second assignment silently clobbered the
# first, so predict_text_policy's `model.predict(...)` call was actually
# hitting this HuggingFace model object once both had loaded, not the
# Keras classifier. Renamed so both models coexist correctly.
nsfw_model = AutoModelForImageClassification.from_pretrained("Falconsai/nsfw_image_detection")
nsfw_processor = ViTImageProcessor.from_pretrained('Falconsai/nsfw_image_detection')

def predict_image_policy(image_bytes: bytes):
    """
    Core PEL image-inspection function. Takes raw image bytes (as sent over
    gRPC in ImageRequest.image_data) rather than a pre-decoded image object,
    since the caller only has bytes off the wire.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    with torch.no_grad():
        inputs = nsfw_processor(images=image, return_tensors="pt")
        outputs = nsfw_model(**inputs)
        logits = outputs.logits

    predicted_label = logits.argmax(-1).item()
    final_risk = nsfw_model.config.id2label[predicted_label]

    if final_risk == "nsfw":
        action = "BLOCK"
    else:
        action = "ALLOW"

    return {
        "action": action,
    }