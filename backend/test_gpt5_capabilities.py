#!/usr/bin/env python3
"""
GPT-5 Capabilities Test Suite for NACRE Platform

This script tests all GPT-5 enhanced features and capabilities.
Run this after upgrading to GPT-5 to validate functionality.
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Any
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings, GPT5_MODELS, GPT5_PARAMS
from app.services.openai_classifier import get_classifier
from app.services.sophie_llm import sophie_chat, sophie_generate_message, sophie_status
from app.services.embeddings import index_status, retrieve_with_embeddings
from app.services.nacre_dict import get_nacre_dict


class GPT5TestSuite:
    def __init__(self):
        self.results = {
            "configuration": {},
            "classification": {},
            "sophie": {},
            "embeddings": {},
            "overall": {}
        }
        
    def test_configuration(self):
        """Test GPT-5 configuration and model availability"""
        print("\n🔧 Testing GPT-5 Configuration...")
        
        config_tests = {
            "openai_api_key": bool(settings.openai_api_key),
            "gpt5_models_configured": all(
                model.startswith(("gpt-5", "gpt-4")) 
                for model in GPT5_MODELS.values() 
                if not model.startswith("text-embedding")
            ),
            "advanced_features_enabled": all([
                settings.enable_advanced_reasoning,
                settings.enable_multi_step_analysis,
                settings.enable_context_enhancement
            ]),
            "enhanced_parameters": all([
                settings.sophie_max_context >= 16000,
                settings.batch_size >= 10,
                settings.sophie_max_tokens >= 1000
            ])
        }
        
        self.results["configuration"] = config_tests
        
        for test, passed in config_tests.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {test}: {passed}")
            
        print(f"\n📋 Model Configuration:")
        for task, model in GPT5_MODELS.items():
            print(f"  • {task}: {model}")
            
        return all(config_tests.values())
    
    def test_classification(self):
        """Test GPT-5 enhanced classification capabilities"""
        print("\n🎯 Testing GPT-5 Classification...")
        
        classifier = get_classifier()
        nacre_dict = get_nacre_dict()
        
        test_cases = [
            {
                "label": "Achat ordinateur portable Dell Latitude",
                "context": {
                    "fournisseur": "Dell Technologies",
                    "compte": "2183",
                    "montant": "1200.00"
                },
                "expected_category_contains": ["informatique", "ordinateur", "portable"]
            },
            {
                "label": "Formation développement Python",
                "context": {
                    "fournisseur": "Formation IT",
                    "compte": "6226",
                    "montant": "2500.00"
                },
                "expected_category_contains": ["formation", "développement"]
            },
            {
                "label": "Papeterie bureau fournitures",
                "context": {
                    "fournisseur": "Office Depot",
                    "compte": "6064",
                    "montant": "150.00"
                },
                "expected_category_contains": ["papeterie", "fourniture", "bureau"]
            }
        ]
        
        classification_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n  Test {i}: {test_case['label']}")
            
            # Get candidates
            candidates = nacre_dict.candidates_advanced(
                test_case["label"], 
                test_case["context"], 
                top_k=20
            )
            
            if not candidates:
                print(f"    ❌ No candidates found")
                classification_results.append(False)
                continue
            
            # Classify with GPT-5
            result = classifier.classify(
                test_case["label"],
                test_case["context"],
                candidates,
                top_k=3
            )
            
            # Validate results
            has_code = bool(result.get("chosen_code"))
            has_confidence = result.get("confidence", 0) > 0
            has_explanation = bool(result.get("explanation"))
            has_reasoning_quality = "reasoning_quality" in result
            has_enhanced_analysis = "enhanced_analysis" in result
            
            # Check if category matches expected keywords
            category_match = False
            chosen_category = result.get("chosen_category", "").lower()
            if chosen_category:
                category_match = any(
                    keyword in chosen_category 
                    for keyword in test_case["expected_category_contains"]
                )
            
            test_passed = all([
                has_code, has_confidence, has_explanation, 
                has_reasoning_quality, category_match
            ])
            
            status = "✅" if test_passed else "❌"
            print(f"    {status} Code: {result.get('chosen_code', 'N/A')}")
            print(f"    {status} Category: {result.get('chosen_category', 'N/A')}")
            print(f"    {status} Confidence: {result.get('confidence', 0)}%")
            print(f"    {status} Has explanation: {has_explanation}")
            print(f"    {status} Reasoning quality: {result.get('reasoning_quality', 0)}%")
            print(f"    {status} Enhanced analysis: {has_enhanced_analysis}")
            
            classification_results.append(test_passed)
        
        classification_success = sum(classification_results) / len(classification_results)
        self.results["classification"] = {
            "success_rate": classification_success,
            "tests_passed": sum(classification_results),
            "total_tests": len(classification_results),
            "gpt5_features_working": classification_success > 0.6
        }
        
        print(f"\n📊 Classification Results: {sum(classification_results)}/{len(classification_results)} tests passed")
        return classification_success > 0.6
    
    def test_sophie_capabilities(self):
        """Test Sophie GPT-5 orchestrator capabilities"""
        print("\n🤖 Testing Sophie GPT-5 Capabilities...")
        
        # Test Sophie status
        status = sophie_status()
        print(f"  📋 Sophie Status: {status}")
        
        # Test greeting generation
        print("\n  Testing greeting generation...")
        try:
            greeting = sophie_generate_message("greeting", {
                "dict_lines": 1571,
                "learning_in_progress": False
            })
            greeting_success = len(greeting) > 50 and "sophie" in greeting.lower()
            status = "✅" if greeting_success else "❌"
            print(f"    {status} Greeting generated: {greeting_success}")
            print(f"    📝 Sample: {greeting[:100]}...")
        except Exception as e:
            greeting_success = False
            print(f"    ❌ Greeting failed: {e}")
        
        # Test advanced chat capabilities
        print("\n  Testing advanced chat capabilities...")
        test_questions = [
            "Quel code NACRE pour l'achat d'un serveur informatique?",
            "Analyse les tendances de classification récentes",
            "Comment améliorer la précision des classifications?",
            "As-tu accès au dictionnaire NACRE?"
        ]
        
        chat_results = []
        for question in test_questions:
            try:
                response = sophie_chat(question)
                reply = response.get("reply", "")
                
                # Check for GPT-5 enhanced features
                has_analysis = len(reply) > 100
                has_structure = any(char in reply for char in ["•", "-", "1.", "2."])
                has_expertise = any(word in reply.lower() for word in ["nacre", "classification", "analyse"])
                is_french = any(word in reply.lower() for word in ["le", "la", "des", "pour", "avec"])
                
                test_passed = all([has_analysis, has_structure, has_expertise, is_french])
                chat_results.append(test_passed)
                
                status = "✅" if test_passed else "❌"
                print(f"    {status} Q: {question[:50]}...")
                print(f"        Analysis depth: {has_analysis}")
                print(f"        Structured response: {has_structure}")
                print(f"        Domain expertise: {has_expertise}")
                
            except Exception as e:
                chat_results.append(False)
                print(f"    ❌ Chat failed: {e}")
        
        sophie_success = sum(chat_results) / len(chat_results) if chat_results else 0
        
        self.results["sophie"] = {
            "greeting_success": greeting_success,
            "chat_success_rate": sophie_success,
            "gpt5_features_working": greeting_success and sophie_success > 0.5,
            "model_used": status.get("model", "unknown")
        }
        
        print(f"\n📊 Sophie Results: Greeting={greeting_success}, Chat={sophie_success:.1%}")
        return greeting_success and sophie_success > 0.5
    
    def test_embeddings(self):
        """Test GPT-5 compatible embeddings"""
        print("\n🔍 Testing Enhanced Embeddings...")
        
        # Check embeddings status
        status = index_status()
        print(f"  📋 Embeddings Status: {status}")
        
        embeddings_ready = status.get("ready", False)
        correct_model = GPT5_MODELS["embeddings"] in status.get("model", "")
        
        if embeddings_ready:
            # Test semantic search
            test_queries = [
                "ordinateur portable informatique",
                "formation développement logiciel",
                "mobilier bureau chaise table"
            ]
            
            search_results = []
            for query in test_queries:
                try:
                    results = retrieve_with_embeddings(query, top_k=5)
                    has_results = bool(results and len(results) > 0)
                    has_scores = all("score" in r for r in results) if results else False
                    has_codes = all("code" in r for r in results) if results else False
                    
                    test_passed = has_results and has_scores and has_codes
                    search_results.append(test_passed)
                    
                    status_icon = "✅" if test_passed else "❌"
                    print(f"    {status_icon} Query: {query}")
                    print(f"        Results: {len(results) if results else 0}")
                    
                except Exception as e:
                    search_results.append(False)
                    print(f"    ❌ Search failed: {e}")
            
            search_success = sum(search_results) / len(search_results) if search_results else 0
        else:
            search_success = 0
            print("    ⚠️ Embeddings not ready - skipping search tests")
        
        self.results["embeddings"] = {
            "embeddings_ready": embeddings_ready,
            "correct_model": correct_model,
            "search_success_rate": search_success,
            "gpt5_features_working": embeddings_ready and correct_model and search_success > 0.6
        }
        
        print(f"\n📊 Embeddings Results: Ready={embeddings_ready}, Model={correct_model}, Search={search_success:.1%}")
        return embeddings_ready and correct_model
    
    def run_full_test_suite(self):
        """Run complete GPT-5 test suite"""
        print("🚀 Starting GPT-5 Capabilities Test Suite")
        print("=" * 50)
        
        # Run all tests
        config_ok = self.test_configuration()
        classification_ok = self.test_classification()
        sophie_ok = self.test_sophie_capabilities()
        embeddings_ok = self.test_embeddings()
        
        # Overall assessment
        overall_success = sum([config_ok, classification_ok, sophie_ok, embeddings_ok]) / 4
        
        self.results["overall"] = {
            "success_rate": overall_success,
            "configuration_ok": config_ok,
            "classification_ok": classification_ok,
            "sophie_ok": sophie_ok,
            "embeddings_ok": embeddings_ok,
            "gpt5_ready": overall_success > 0.75
        }
        
        # Print final results
        print("\n" + "=" * 50)
        print("🎯 FINAL RESULTS")
        print("=" * 50)
        
        components = [
            ("Configuration", config_ok),
            ("Classification", classification_ok),
            ("Sophie Orchestrator", sophie_ok),
            ("Embeddings", embeddings_ok)
        ]
        
        for component, success in components:
            status = "✅" if success else "❌"
            print(f"{status} {component}: {'PASS' if success else 'FAIL'}")
        
        print(f"\n📊 Overall Success Rate: {overall_success:.1%}")
        
        if overall_success > 0.75:
            print("🎉 GPT-5 UPGRADE SUCCESSFUL!")
            print("   All major components are working with GPT-5 enhancements.")
        elif overall_success > 0.5:
            print("⚠️  GPT-5 PARTIALLY WORKING")
            print("   Some components need attention. Check individual test results.")
        else:
            print("❌ GPT-5 UPGRADE ISSUES")
            print("   Major issues detected. Review configuration and API access.")
        
        # Save detailed results
        results_file = "gpt5_test_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n📝 Detailed results saved to: {results_file}")
        
        return overall_success > 0.75


def main():
    """Main test runner"""
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key and try again.")
        return False
    
    test_suite = GPT5TestSuite()
    return test_suite.run_full_test_suite()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
