import streamlit as st
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import pickle
import os
from together import Together
from googletrans import Translator
from gtts import gTTS
from io import BytesIO
from pydub import AudioSegment
from pydub.playback import play


class PreTrainedModelApp:
    def __init__(self, model_path,decoder_path, feature_names=None, input_types=None):
        """
        Initialize the app with a pre-trained model
        
        :param model_path: Path to the saved model file
        :param feature_names: List of feature names (optional)
        :param input_types: List of input types for each feature (optional)
        """
        # Load the pre-trained model
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
             
        except Exception as e:
            st.error(f"Error loading model: {e}")
            self.model = None
        try:
            with open(decoder_path, 'rb') as f:
                self.decoder = pickle.load(f)
        except Exception as e:
            st.error(f"Error loading decoder: {e}")
            self.decoder = None


        
        # Set feature names and input types
        self.feature_names = feature_names or [f"Feature {i+1}" for i in range(7)]
        self.input_types = input_types or ['float'] * len(self.feature_names)
        
        # Initialize session state for storing input data
        if 'input_data' not in st.session_state:
            st.session_state.input_data = None
        if 'prediction' not in st.session_state:
            st.session_state.prediction = None

    def create_input_interface(self):
        """
        Create dynamic input interface based on feature names and types
        """
        st.header("Model Input Parameters")
        
        # Create columns for input fields
        cols = st.columns(2)
        
        # Store input values
        input_values = []
        
        # Create input fields dynamically
        for i, (name, input_type) in enumerate(zip(self.feature_names, self.input_types)):
            col = cols[i % 2]
            
            with col:
                # Different input types
                if input_type == 'int':
                    value = st.number_input(
                        name, 
                        min_value=0, 
                        value=0, 
                        step=1, 
                        key=f"input_{i}"
                    )
                elif input_type == 'float':
                    value = st.number_input(
                        name, 
                        value=0.0, 
                        step=0.1, 
                        format="%.2f", 
                        key=f"input_{i}"
                    )
                elif input_type == 'categorical':
                    # Placeholder for categorical input
                    value = st.selectbox(
                        name, 
                        options=['Option 1', 'Option 2', 'Option 3'], 
                        key=f"input_{i}"
                    )
                else:
                    # Default to float
                    value = st.number_input(
                        name, 
                        value=0.0, 
                        step=0.1, 
                        format="%.2f", 
                        key=f"input_{i}"
                    )
                
                input_values.append(value)
        
        return input_values

    def predict(self, input_data):

        try:
            # Convert input to numpy array
            input_array = np.array(input_data).reshape(1, -1)
            
            # Make prediction
            if hasattr(self.model, 'predict_proba'):
                # If model supports probability prediction
                prediction = self.model.predict(input_array)[0]
                probabilities = self.model.predict_proba(input_array)[0]
                return prediction, probabilities
            else:
                # If model only supports basic prediction
                prediction = self.model.predict(input_array)[0]
                return self.decoder.inverse_transform([ prediction]), None
        
        except Exception as e:
            st.error(f"Prediction error: {e}")
            return None, None

    def visualize_prediction(self, prediction, probabilities):
        """
        Create visualizations for the prediction
        
        :param prediction: Model prediction
        :param probabilities: Prediction probabilities
        """
        st.header("Prediction Results")
        
        # Create columns for result display
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Predicted Output", str(prediction))
        
        # Probability visualization if available
        if probabilities is not None:
            with col2:
                st.metric("Confidence", f"{max(probabilities):.2%}")
            
            # Probability distribution plot
            fig = go.Figure(data=[
                go.Bar(
                    x=[f'Class {i}' for i in range(len(probabilities))],
                    y=probabilities,
                    text=[f'{p:.2%}' for p in probabilities],
                    textposition='auto'
                )
            ])
            fig.update_layout(
                title='Class Probability Distribution',
                xaxis_title='Classes',
                yaxis_title='Probability',
                yaxis_range=[0, 1]
            )
            st.plotly_chart(fig)


   


    def run(self,selected_language):
        """
        Main Streamlit app runner
        """
        # Check if model is loaded
        if self.model is None:
            st.error("Model could not be loaded. Please check the model file.")
            return
        
        # App title
        st.title("Machine Learning Model Crop Predictor")
        
        # Create input interface
        input_values = self.create_input_interface()
        
        # Prediction button
        if st.button("Make Prediction"):
            # Store input data in session state
            st.session_state.input_data = input_values
            
            # Make prediction
            prediction, probabilities = self.predict(input_values)
            prediction=self.decoder.inverse_transform([prediction])
            
            
            # Store prediction in session state
            st.session_state.prediction = prediction
            
            # Visualize results
            if prediction is not None:
                self.visualize_prediction(prediction, probabilities)
                str2= "Provide a detailed guide on how to grow " + str(prediction) + " including specific treatments, preventative measures, and any relevant environmental factors."
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
                lang_code = INDIAN_LANGUAGES[selected_language]
                translation = translator.translate(result, dest=lang_code)
                translated_text = translation.text

                st.header(translated_text)
                tts = gTTS(text=translated_text, lang=lang_code)
                # audio_buffer = BytesIO()
                # tts.write_to_fp(audio_buffer)
                tts.save("translated_audio.mp3")
                # with open(audio_buffer, 'rb') as audio:
                st.audio("translated_audio.mp3", format='audio/mp3')
                    
                



def main():
    # Example usage
    # Replace with your actual model path and configuration
    model_app = PreTrainedModelApp(
        model_path='RandomForest.pkl',decoder_path="label_encoder.pkl",
        feature_names=[
            'N', 
            'P',
            'K',
            'temperature', 
            'humidity', 
            'ph', 
            'rainfall'
        ],
        input_types=[
            'float',  # Temperature
            'float',  # Humidity
            'float',  # Pressure
            'float',  # Wind Speed
            'float',  # Rainfall
            'float',
            'float'  # Altitude
        ]
    )

    
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
       # Language selection dropdown
    selected_language = st.selectbox(
                "Select Target Language:", 
                list(INDIAN_LANGUAGES.keys())
    )
    model_app.run(selected_language)

if __name__ == "__main__":
    main()