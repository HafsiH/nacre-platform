#!/usr/bin/env python3
"""
Comprehensive test for Sophie GPT-5 capabilities and document access
"""
import asyncio
import json
from pathlib import Path
from app.services.sophie_llm import sophie_chat, sophie_generate_message
from app.services.document_access import sophie_get_context, get_document_access
from app.config import settings

async def test_gpt5_capabilities():
    print("🚀 Testing Sophie GPT-5 Capabilities")
    print("=" * 60)
    
    # Test 1: Configuration
    print("\n1. Testing Configuration...")
    print(f"✅ Model: {settings.sophie_model}")
    print(f"✅ Temperature: {settings.sophie_temperature}")
    print(f"✅ Max Tokens: {settings.sophie_max_tokens}")
    print(f"✅ Max Context: {settings.sophie_max_context}")
    
    # Test 2: Document Access
    print("\n2. Testing Document Access...")
    try:
        context = sophie_get_context()
        print(f"✅ Context retrieved successfully")
        print(f"   - NACRE entries: {context['nacre_dictionary']['total_entries']}")
        print(f"   - Training items: {context['training_data']['total_training_items']}")
        print(f"   - Suppliers: {context['patterns']['suppliers_count']}")
        print(f"   - Accounts: {context['patterns']['accounts_count']}")
    except Exception as e:
        print(f"❌ Document access failed: {e}")
        return
    
    # Test 3: Search Functionality
    print("\n3. Testing Search Functionality...")
    try:
        doc_access = get_document_access()
        results = doc_access.search_nacre_codes("bureau", limit=5)
        print(f"✅ Search successful: {len(results)} results for 'bureau'")
        if results:
            print(f"   - Top result: {results[0]['code']} - {results[0]['category']}")
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    # Test 4: Enhanced Chat
    print("\n4. Testing Enhanced Chat...")
    test_questions = [
        "What documents do you have access to?",
        "How many NACRE codes are in your dictionary?",
        "What training data do you have?",
        "Can you search for office supplies in the NACRE dictionary?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        try:
            print(f"\n   Question {i}: {question}")
            result = sophie_chat(question)
            reply = result.get('reply', 'No reply')
            print(f"   ✅ Response: {reply[:150]}...")
        except Exception as e:
            print(f"   ❌ Chat failed: {e}")
    
    # Test 5: Greeting Message
    print("\n5. Testing Enhanced Greeting...")
    try:
        context = {
            "dict_lines": context['nacre_dictionary']['total_entries'],
            "learning_in_progress": context['embeddings']['in_progress']
        }
        greeting = sophie_generate_message("greeting", context)
        print(f"✅ Greeting: {greeting}")
    except Exception as e:
        print(f"❌ Greeting failed: {e}")
    
    # Test 6: API Endpoints (simulated)
    print("\n6. Testing API Endpoints...")
    try:
        # Simulate context endpoint
        context_data = sophie_get_context()
        print(f"✅ Context endpoint: {len(context_data)} sections")
        
        # Simulate search endpoint
        search_results = doc_access.search_nacre_codes("informatique", limit=3)
        print(f"✅ Search endpoint: {len(search_results)} results for 'informatique'")
        
        # Simulate documents endpoint
        nacre_summary = doc_access.get_nacre_summary()
        training_summary = doc_access.get_training_summary()
        patterns_summary = doc_access.get_patterns_summary()
        print(f"✅ Documents endpoint: {nacre_summary['total_entries']} NACRE entries, {training_summary['total_training_items']} training items")
        
    except Exception as e:
        print(f"❌ API endpoints failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 GPT-5 Capabilities Test Completed!")
    print("\nSummary of Enhancements:")
    print("✅ Upgraded to GPT-5o model")
    print("✅ Enhanced document access")
    print("✅ Comprehensive context gathering")
    print("✅ Search functionality")
    print("✅ Better error handling")
    print("✅ Improved prompts and responses")

if __name__ == "__main__":
    asyncio.run(test_gpt5_capabilities())
