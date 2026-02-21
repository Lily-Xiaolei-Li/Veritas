"""Quick test for multi-source resolver."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.services.proliferomaxima.api_resolver import ProliferomaximaAPIResolver

async def test():
    resolver = ProliferomaximaAPIResolver()
    
    # Test DOIs that only OpenAlex has abstract
    test_dois = [
        ("10.1080/0969160x.2011.556414", "Stakeholder Inclusivity"),
        ("10.1016/j.aos.2011.07.007", "Big 4 Ethnography"),
        ("10.1080/0969160x.2011.593832", "Family Firms Pollute Less"),
    ]
    
    for doi, name in test_dois:
        print(f"=== {name} ===")
        print(f"DOI: {doi}")
        result = await resolver.resolve({"doi": doi})
        if result:
            print(f"Source: {result.get('source')}")
            abstract = result.get("abstract", "")
            if abstract:
                print(f"Abstract: {abstract[:120]}...")
            else:
                print("Abstract: NONE")
        else:
            print("Result: NONE")
        print()

if __name__ == "__main__":
    asyncio.run(test())
