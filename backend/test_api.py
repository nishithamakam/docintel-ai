"""
Quick test to verify BMS API connection works.
Run this once to confirm the gateway is reachable and the key is valid.
"""
from openai import OpenAI
from app.config import settings

# Create the OpenAI client pointed at the BMS gateway
client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

print(f"🔌 Connecting to: {settings.openai_base_url}")
print(f"🤖 Using model: {settings.chat_model}")
print("📤 Sending test message...\n")

# Send a simple test prompt
response = client.chat.completions.create(
    model=settings.chat_model,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in exactly 5 words."},
    ],
)

# Print the response
answer = response.choices[0].message.content
print(f"✅ Response received!")
print(f"💬 Model said: {answer}")
print(f"\n📊 Tokens used: {response.usage.total_tokens}")
