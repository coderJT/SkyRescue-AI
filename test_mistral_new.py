import os
import asyncio
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage

async def test_mistral():
    # Use the specific API key provided by the user
    api_key = "CgliNVW7W1SIfqFzJNguINrmgXw5ueSs"
    
    print(f"--- 🧪 Mistral API Connection Test ---")
    print(f"Key: {api_key[:5]}...{api_key[-5:]}")
    
    # Try different models to see which one works
    models = ["mistral-small-latest", "open-mistral-7b", "mistral-tiny-latest"]
    
    for model in models:
        print(f"\n📡 Testing Model: {model}")
        llm = ChatMistralAI(model=model, mistral_api_key=api_key)
        
        try:
            print(f"💬 Prompt: 'What is 2+2?'")
            response = await llm.ainvoke([HumanMessage(content="What is 2+2? Answer only with the number.")])
            print(f"✅ SUCCESS! Response from {model}: {response.content.strip()}")
            return # Exit if successful
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ RATE LIMITED (429): This model ({model}) is hitting usage limits.")
            else:
                print(f"❌ ERROR with {model}: {e}")
                
    print("\n❌ Final Result: All tested models failed or are rate-limited.")

if __name__ == "__main__":
    asyncio.run(test_mistral())
