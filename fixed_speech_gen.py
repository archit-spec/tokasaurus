import torch
import numpy as np
import soundfile as sf
from openai import OpenAI
from snac import SNAC
import re

class SpeechGenerator:
    def __init__(self, server_url="http://0.0.0.0:10210/v1", chosen_voice="tara"):
        """
        Initialize the speech generator.

        Args:
            server_url: URL of the tokasaurus server
            chosen_voice: Voice to use for generation
        """
        self.client = OpenAI(
            api_key='fake-key',
            base_url=server_url
        )
        self.chosen_voice = chosen_voice

        # Load SNAC model for audio decoding
        print("Loading SNAC audio decoder...")
        self.snac_model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz")
        self.snac_model = self.snac_model.to("cpu")
        print("SNAC model loaded successfully!")

    def generate_speech(self, text, temperature=0.6, max_tokens=500):
        """
        Generate speech from text input.

        Args:
            text: Input text to convert to speech
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Audio samples as numpy array
        """
        # Format prompt with voice prefix
        prompt = f"{self.chosen_voice}: {text}"

        print(f"Generating speech for: '{text}'")
        print("Sending request to tokasaurus server...")

        try:
            # Make request to tokasaurus server
            response = self.client.completions.create(
                model="default",
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                n=1,
                stop=["<|endoftext|>", "\n\n", f"{self.chosen_voice}:"]  # Add stop tokens
            )

            generated_text = response.choices[0].text
            print(f"Generated text: {generated_text[:200]}...")
            print(f"Generated tokens: {len(generated_text.split())}")

            # Parse the generated text to extract audio codes
            audio_samples = self._parse_and_decode_audio(generated_text)

            return audio_samples

        except Exception as e:
            print(f"Error during generation: {e}")
            return None

    def _parse_and_decode_audio(self, generated_text):
        """
        Parse generated text and decode audio codes.
        """
        try:
            # Extract audio codes from generated text
            codes = self._extract_audio_codes(generated_text)

            if not codes:
                print("No audio codes found in generated text")
                print("Generated text sample:", generated_text[:500])
                return None

            print(f"Extracted {len(codes)} audio codes")

            # Decode using SNAC
            audio_samples = self._redistribute_and_decode_codes(codes)

            return audio_samples

        except Exception as e:
            print(f"Error parsing audio codes: {e}")
            return None

    def _extract_audio_codes(self, text):
        """
        Extract audio codes from generated text.
        Orpheus typically outputs codes in specific token formats.
        """
        codes = []
        
        # Method 1: Look for custom tokens like <custom_token_XXXX>
        custom_token_pattern = r'<custom_token_(\d+)>'
        custom_matches = re.findall(custom_token_pattern, text)
        if custom_matches:
            print(f"Found {len(custom_matches)} custom tokens")
            codes = [int(match) for match in custom_matches]
            return codes
        
        # Method 2: Look for patterns like [XXXX] or (XXXX)
        bracket_pattern = r'[\[\(](\d+)[\]\)]'
        bracket_matches = re.findall(bracket_pattern, text)
        if bracket_matches:
            print(f"Found {len(bracket_matches)} bracketed numbers")
            codes = [int(match) for match in bracket_matches]
            return codes
        
        # Method 3: Look for sequences of numbers separated by spaces/commas
        number_sequence_pattern = r'\b(\d{3,5})\b'  # 3-5 digit numbers
        number_matches = re.findall(number_sequence_pattern, text)
        if number_matches:
            print(f"Found {len(number_matches)} number sequences")
            codes = [int(match) for match in number_matches]
            return codes
        
        # Method 4: Look for any 4-digit numbers (typical for audio codes)
        four_digit_pattern = r'\b(\d{4})\b'
        four_digit_matches = re.findall(four_digit_pattern, text)
        if four_digit_matches:
            print(f"Found {len(four_digit_matches)} four-digit numbers")
            codes = [int(match) for match in four_digit_matches]
            return codes

        print("No recognizable audio code patterns found")
        return []

    def _redistribute_and_decode_codes(self, code_list):
        """
        Redistribute codes into layers and decode audio.
        Based on SNAC's expected format.
        """
        if len(code_list) < 7:
            print(f"Not enough codes: {len(code_list)} (need at least 7)")
            return None
            
        # Ensure we have a multiple of 7 codes
        new_length = (len(code_list) // 7) * 7
        code_list = code_list[:new_length]
        print(f"Using {new_length} codes (from {len(code_list)} total)")

        # Redistribute codes into 3 layers based on SNAC format
        layer_1 = []
        layer_2 = []
        layer_3 = []

        for i in range(new_length // 7):
            base_idx = 7 * i
            layer_1.append(code_list[base_idx])
            layer_2.extend([code_list[base_idx + 1], code_list[base_idx + 4]])
            layer_3.extend([
                code_list[base_idx + 2], 
                code_list[base_idx + 3],
                code_list[base_idx + 5], 
                code_list[base_idx + 6]
            ])

        # Convert to tensors and ensure valid ranges
        try:
            # Clamp values to valid SNAC ranges
            layer_1 = torch.clamp(torch.tensor(layer_1, dtype=torch.long), 0, 4095)
            layer_2 = torch.clamp(torch.tensor(layer_2, dtype=torch.long), 0, 4095)
            layer_3 = torch.clamp(torch.tensor(layer_3, dtype=torch.long), 0, 4095)
            
            codes = [
                layer_1.unsqueeze(0),
                layer_2.unsqueeze(0), 
                layer_3.unsqueeze(0)
            ]

            print(f"Layer shapes: {[c.shape for c in codes]}")

            # Decode audio
            with torch.no_grad():
                audio_hat = self.snac_model.decode(codes)

            return audio_hat.squeeze().numpy()
            
        except Exception as e:
            print(f"Error during SNAC decoding: {e}")
            return None

    def save_audio(self, audio_samples, filename="output.wav", sample_rate=24000):
        """Save audio samples to file."""
        if audio_samples is not None and len(audio_samples) > 0:
            # Normalize audio to prevent clipping
            if np.max(np.abs(audio_samples)) > 1.0:
                audio_samples = audio_samples / np.max(np.abs(audio_samples)) * 0.95
                
            sf.write(filename, audio_samples, sample_rate)
            print(f"Audio saved to {filename}")
            return filename
        return None

def main():
    """Interactive speech generation."""
    print("Initializing Speech Generator...")
    print("Make sure tokasaurus server is running with:")
    print("toka model=canopylabs/orpheus-3b-0.1-ft")
    print()

    generator = SpeechGenerator()

    while True:
        try:
            text = input("\nEnter text to convert to speech (or 'quit' to exit): ")

            if text.lower() in ['quit', 'exit', 'q']:
                break

            if not text.strip():
                print("Please enter some text!")
                continue

            # Generate speech
            audio = generator.generate_speech(text)

            if audio is not None:
                # Save audio file
                filename = f"speech_{hash(text) % 10000}.wav"
                generator.save_audio(audio, filename)
                print("Audio generation successful!")
            else:
                print("Failed to generate speech")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()