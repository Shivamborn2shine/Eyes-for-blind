"""Bilingual (English / Hindi) phrases and object names."""

PHRASES = {
    "en": {
        "welcome": "Vistara Vision is ready. Press F1 for help.",
        "help": ("Press C to identify currency, X for auto-counting, U to undo. "
                 "O to read text on packaging. K to identify color. "
                 "R to remember items, L when leaving. D to describe what is in front. "
                 "W to ask where items were last seen. T to teach new objects. H to switch language. Escape to quit."),
        "lang_switched": "Language set to English.",
        "hold_note": "Hold the note flat in front of the camera.",
        "note_found": "This is a {value} rupee note.",
        "note_unsure": "I am not sure. Please hold the note steady, flat and in good light.",
        "note_none": "I cannot see a currency note.",
        "total": "Total so far: {total} rupees.",
        "scanning": "Scanning.",
        "remembered": "I will remember {items}.",
        "remember_none": "I do not see any personal items here.",
        "left_items": "Wait! You left your {items}.",
        "nothing_left": "All clear. You have not left anything behind.",
        "no_memory": "I have not remembered any items yet. Press R first.",
        "auto_left": "Attention! You may have forgotten your {items}.",
        "describe": "I can see {items}.",
        "describe_none": "I do not see any familiar objects.",
        "where_item": "Your {item} was last seen {pos}, {ago}.",
        "where_item_precise": "Your {item} was seen {clock}, {prox}, {ago}.",
        "item_not_found": "I have not seen your {name} recently.",
        "currency_breakdown": "Total is {total} rupees across {count} notes: {details}.",
        "where_none": "I have no record of your belongings yet.",
        "teach_start": "Please hold the {name} steady in front of the camera.",
        "teach_done": "I have learned {name}. I will recognize it from now on.",
        "teach_empty": "Please specify a name for the object.",
        "read_text_reading": "Reading text, please hold still.",
        "read_text_none": "No readable text detected.",
        "read_text_found": "It reads: {text}",
        "color_inspecting": "Checking color.",
        "color_found": "This appears to be {color}.",
        "undo_note": "Removed {value} rupees. New total is {total} rupees.",
        "undo_none": "No notes to undo.",
        "auto_currency_on": "Continuous currency counting is on. Hold notes up one by one.",
        "auto_currency_off": "Continuous currency counting is off.",
        "camera_error": "Camera not found. Please check the camera connection.",
        "goodbye": "Goodbye.",
        "and": "and",
        "left": "on the left", "center": "in the middle", "right": "on the right",
        "close": "right in front of you", "medium": "nearby", "far": "further away",
        "just_now": "just now",
        "min_ago": "{n} minutes ago",
        "hr_ago": "{n} hours ago",
    },
    "hi": {
        "welcome": "विस्तारा विज़न तैयार है। सहायता के लिए F1 दबाएँ।",
        "help": ("नोट जाँचने के लिए C, लगातार गिनने के लिए X, और नोट हटाने के लिए U दबाएँ। "
                 "लिखावट पढ़ने के लिए O दबाएँ। रंग पहचानने के लिए K दबाएँ। "
                 "सामान याद रखने के लिए R और निकलते समय L दबाएँ। सामने देखने के लिए D और ढूँढने के लिए W दबाएँ। "
                 "नया सामान सिखाने के लिए T, भाषा बदलने के लिए H, और बंद करने के लिए Escape दबाएँ।"),
        "lang_switched": "भाषा हिंदी कर दी गई है।",
        "hold_note": "नोट को कैमरे के सामने सीधा पकड़ें।",
        "note_found": "यह {value} रुपये का नोट है।",
        "note_unsure": "मुझे पक्का नहीं पता। नोट को रोशनी में सीधा और स्थिर पकड़ें।",
        "note_none": "मुझे कोई नोट दिखाई नहीं दे रहा।",
        "total": "अब तक कुल {total} रुपये।",
        "scanning": "जाँच रहा हूँ।",
        "remembered": "मैं याद रखूँगा: {items}।",
        "remember_none": "मुझे यहाँ कोई निजी सामान नहीं दिख रहा।",
        "left_items": "रुकिए! आपका {items} यहीं छूट गया है।",
        "nothing_left": "सब ठीक है। आपका कुछ भी नहीं छूटा।",
        "no_memory": "अभी तक कोई सामान याद नहीं रखा गया। पहले R दबाएँ।",
        "auto_left": "ध्यान दें! शायद आपका {items} छूट गया है।",
        "describe": "मुझे {items} दिख रहा है।",
        "describe_none": "मुझे कोई जानी-पहचानी चीज़ नहीं दिख रही।",
        "where_item": "आपका {item} आख़िरी बार {pos}, {ago} देखा गया था।",
        "where_item_precise": "आपका {item} {clock}, {prox}, {ago} देखा गया था।",
        "item_not_found": "मुझे आपका {name} हाल ही में नहीं दिखा।",
        "currency_breakdown": "कुल {count} नोटों का योग {total} रुपये है: {details}।",
        "where_none": "अभी तक आपके सामान का कोई रिकॉर्ड नहीं है।",
        "teach_start": "कृपया {name} को कैमरे के सामने सीधा पकड़ें।",
        "teach_done": "मैंने {name} याद कर लिया है। अब मैं इसे पहचानूँगा।",
        "teach_empty": "कृपया वस्तु का नाम बताएं।",
        "read_text_reading": "लिखावट पढ़ रहा हूँ, कृपया सीधा रखें।",
        "read_text_none": "कोई लिखावट नहीं मिली।",
        "read_text_found": "लिखा है: {text}",
        "color_inspecting": "रंग पहचान रहा हूँ।",
        "color_found": "यह {color} रंग का है।",
        "undo_note": "{value} रुपये हटा दिए गए। नया कुल: {total} रुपये।",
        "undo_none": "हटाने के लिए कोई नोट नहीं है।",
        "auto_currency_on": "लगातार नोट गिनना चालू है। एक-एक करके नोट दिखाएँ।",
        "auto_currency_off": "लगातार नोट गिनना बंद कर दिया गया है।",
        "camera_error": "कैमरा नहीं मिला। कृपया कैमरा कनेक्शन जाँचें।",
        "goodbye": "अलविदा।",
        "and": "और",
        "left": "बाईं ओर", "center": "बीच में", "right": "दाईं ओर",
        "close": "बिल्कुल पास में", "medium": "पास में", "far": "कुछ दूरी पर",
        "just_now": "अभी-अभी",
        "min_ago": "{n} मिनट पहले",
        "hr_ago": "{n} घंटे पहले",
    },
}

OBJECT_NAMES_HI = {
    "person": "व्यक्ति", "cell phone": "मोबाइल फ़ोन", "bottle": "बोतल",
    "backpack": "बैग", "handbag": "हैंडबैग", "umbrella": "छाता", "book": "किताब",
    "laptop": "लैपटॉप", "cup": "कप", "remote": "रिमोट", "keyboard": "कीबोर्ड",
    "mouse": "माउस", "scissors": "कैंची", "suitcase": "सूटकेस", "clock": "घड़ी",
    "toothbrush": "टूथब्रश", "wine glass": "गिलास", "teddy bear": "टेडी बियर",
    "chair": "कुर्सी", "dining table": "मेज़", "tv": "टीवी", "bed": "बिस्तर",
    "couch": "सोफ़ा", "door": "दरवाज़ा", "car": "कार", "motorcycle": "मोटरसाइकिल",
    "bicycle": "साइकिल", "dog": "कुत्ता", "cat": "बिल्ली", "bowl": "कटोरा",
    "spoon": "चम्मच", "knife": "चाकू", "fork": "काँटा", "potted plant": "गमला",
    "sink": "सिंक", "refrigerator": "फ्रिज", "bench": "बेंच", "bus": "बस",
    "truck": "ट्रक", "traffic light": "ट्रैफ़िक लाइट", "stop sign": "स्टॉप साइन",
}

OBJECT_NAMES_EN = {"cell phone": "phone", "wine glass": "glass", "tv": "television"}


class I18N:
    def __init__(self, lang: str = "en"):
        self.lang = lang if lang in PHRASES else "en"

    def toggle(self):
        self.lang = "hi" if self.lang == "en" else "en"
        return self.lang

    def t(self, key: str, **kw) -> str:
        text = PHRASES[self.lang].get(key) or PHRASES["en"].get(key, key)
        return text.format(**kw)

    def obj(self, name: str) -> str:
        if self.lang == "hi":
            return OBJECT_NAMES_HI.get(name, name)
        return OBJECT_NAMES_EN.get(name, name)

    def join(self, words):
        words = list(words)
        if not words:
            return ""
        if len(words) == 1:
            return words[0]
        return ", ".join(words[:-1]) + f" {self.t('and')} " + words[-1]

    def items_phrase(self, counts: dict, positions: dict | None = None, proximities: dict | None = None) -> str:
        """{'bottle': 2, 'cell phone': 1} -> '2 bottles and phone on the left (nearby)'"""
        parts = []
        for name, n in counts.items():
            label = self.obj(name)
            if n > 1:
                label = f"{n} {label}" + ("s" if self.lang == "en" and not label.endswith("s") else "")
            pos_str = (" " + self.t(positions[name])) if positions and name in positions else ""
            prox_str = (" (" + self.t(proximities[name]) + ")") if proximities and name in proximities and proximities[name] != "medium" else ""
            parts.append(label + pos_str + prox_str)
        return self.join(parts)
