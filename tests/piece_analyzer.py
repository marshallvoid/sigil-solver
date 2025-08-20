# ruff: noqa: T201

from sigil.services.recognizer import RecognizerService

if __name__ == "__main__":
    rec = RecognizerService()
    box1, confidence1 = rec.identify_gap(source="resources/background-1-1.jpeg", show_result=True)
    print(f"box1: {box1}, confidence1: {confidence1}")

    box2, confidence2 = rec.identify_gap(source="resources/background-2-2.jpeg", show_result=True)
    print(f"box2: {box2}, confidence2: {confidence2}")
