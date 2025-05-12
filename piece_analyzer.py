from recognizer import Recognizer

if __name__ == '__main__':
    rec = Recognizer()
    box, confidence = rec.identify_gap(source='resources/piece-1-1.png', show_result=True, verbose=True)
    print(box, confidence)
    