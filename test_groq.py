import os
import asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

async def test_groq():
    # Use the specific API key provided by the user
    api_key = "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"
    
    print(f"--- 🧪 Groq API Connection Test ---")
    print(f"Key: {api_key[:10]}...{api_key[-5:]}")
    
    # Try different models to see which one works
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    for model in models:
        print(f"\n📡 Testing Model: {model}")
        llm = ChatGroq(model=model, groq_api_key=api_key)
        
        try:
            print(f"💬 Prompt: 'What is 2+2?'")
            response = await llm.ainvoke([HumanMessage(content="What is 2+2? Answer only with the number.")])
            print(f"✅ SUCCESS! Response from {model}: {response.content.strip()}")
            return # Exit if successful
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ RATE LIMITED (429): This model ({model}) is hitting usage limits on Groq.")
            else:
                print(f"❌ ERROR with {model}: {e}")
                
    print("\n❌ Final Result: All tested models failed or are rate-limited on Groq.")

if __name__ == "__main__":
    asyncio.run(test_groq())
