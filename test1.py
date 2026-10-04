import streamlit as st
import pandas as pd
import numpy as np
import math
import uuid
from datetime import datetime
import json
import pickle
import os
from together import Together
from googletrans import Translator
from gtts import gTTS
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
str2= "Provide a detailed guide on how to grow " + str('kidneybean') + " including specific treatments, preventative measures, and any relevant environmental factors."
client = Together(api_key=('064227b6f158ec7d8248690ab32012ce5ee0e87f5ef6d6d1646e91633c4c33cf'))

response = client.chat.completions.create(
    model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    messages=[{"role": "user", "content": str2}],
    max_tokens=512,
    temperature=0.7

)
print(response.choices[0].message.content)
result = ''
for choice in response.choices:
    result += choice.message.content
result = result.replace("*", "")


INDIAN_LANGUAGES = {
"Hindi": "hi",
    "Bengali": "bn", 
    "Telugu": "te",
    "Marathi": "mr",
    "Tamil": "ta",
    "Urdu": "ur",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Odia": "or",
    "Punjabi": "pa"
}

translator = Translator()
lang_code = INDIAN_LANGUAGES['Hindi']
translation = translator.translate(result, dest=lang_code)
translated_text = translation.text

print(translated_text)
tts = gTTS(text=translated_text, lang=lang_code)
# audio_buffer = BytesIO()
# tts.write_to_fp(audio_buffer)
tts.save("translated_audio.mp3")
# with open(audio_buffer, 'rb') as audio:
