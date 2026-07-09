"""The graded reader — reading from zero to full stories, as data.

A ladder of levels (R0 single characters → R6 a full story) of ORIGINAL
tokenized texts: every word carries its pinyin and gloss so the UI can make it
tappable and speakable, and every text names the few new words it introduces.
Vocabulary builds slowly and deliberately: a text pre-teaches its new words,
the learner reads, answers comprehension questions, and on completion the new
words enter the SRS deck (learner.add_word) — reading feeds reviews.

Unlocks are sequential (finish a level to open the next) but the speaking
stage sets a floor so a placed learner isn't stuck reading single characters:
stage index k opens levels 0..k outright.

Text format: sentences are written in a compact notation and expanded by
_s() — tokens separated by spaces, each word as hanzi|pinyin|gloss (multi-
syllable pinyin and multi-word glosses use _ for spaces); bare punctuation
stands alone. Dialogue lines carry a speaker.
"""


def _s(line, who=None):
    toks = []
    for part in line.split():
        bits = part.split("|")
        if len(bits) == 3:
            toks.append({"z": bits[0], "p": bits[1].replace("_", " "),
                         "e": bits[2].replace("_", " ")})
        else:
            toks.append({"z": part, "p": "", "e": ""})
    return {"who": who, "t": toks}


LEVELS = [
    {"id": "R0", "idx": 0, "zh": "认字", "name": "First characters", "ruby": True,
     "desc": "Single characters, one at a time — hear each one, see its shape mean something."},
    {"id": "R1", "idx": 1, "zh": "词", "name": "Characters make words", "ruby": True,
     "desc": "Two characters snap together and mean something new — the writing system's superpower."},
    {"id": "R2", "idx": 2, "zh": "句", "name": "First sentences", "ruby": True,
     "desc": "Real sentences built from characters you know. Pinyin still rides above."},
    {"id": "R3", "idx": 3, "zh": "对话", "name": "Dialogues", "ruby": False,
     "desc": "Two people talking. Pinyin fades — tap any word you need."},
    {"id": "R4", "idx": 4, "zh": "段", "name": "Paragraphs", "ruby": False,
     "desc": "Connected sentences that tell one small thing about a day."},
    {"id": "R5", "idx": 5, "zh": "小故事", "name": "Short stories", "ruby": False,
     "desc": "A beginning, a middle, and an end — your first real stories."},
    {"id": "R6", "idx": 6, "zh": "故事", "name": "A full story", "ruby": False,
     "desc": "Several paragraphs, one story, no training wheels."},
]

# (hanzi, pinyin, english, tones) — added to the SRS deck when the text is done
TEXTS = [
    # ── R0 — single characters ────────────────────────────────────────────────
    {"id": "r0-1", "level": "R0", "title": "一 二 三 四 五", "title_en": "Counting: one to five",
     "intro": "Your first characters count: 一 二 三 are literally counting rods. "
              "Tap each one and hear it.",
     "note": "Reading tip: the little circle 。 is the Chinese full stop — it ends "
             "a sentence exactly like a period.",
     "new_words": [("一", "yī", "one", [1]), ("二", "èr", "two", [4]),
                   ("三", "sān", "three", [1]), ("四", "sì", "four", [4]),
                   ("五", "wǔ", "five", [3])],
     "sentences": [_s("一|yī|one"), _s("二|èr|two"), _s("三|sān|three"),
                   _s("四|sì|four"), _s("五|wǔ|five")],
     "en": "One. Two. Three. Four. Five.",
     "qs": [{"q": "Which character means “four”?", "choices": ["四", "五", "二", "一"], "a": 0},
            {"q": "How is 三 read?", "choices": ["sān", "sì", "èr", "wǔ"], "a": 0}]},
    {"id": "r0-2", "level": "R0", "title": "六 七 八 九 十", "title_en": "Counting: six to ten",
     "intro": "The second half of counting. With these ten characters you can read "
              "any number to ninety-nine — 十一 is ten-one, eleven; 二十 is two-tens, twenty.",
     "new_words": [("六", "liù", "six", [4]), ("七", "qī", "seven", [1]),
                   ("八", "bā", "eight", [1]), ("九", "jiǔ", "nine", [3]),
                   ("十", "shí", "ten", [2])],
     "sentences": [_s("六|liù|six"), _s("七|qī|seven"), _s("八|bā|eight"),
                   _s("九|jiǔ|nine"), _s("十|shí|ten"),
                   _s("十|shí|ten 一|yī|one"), _s("二|èr|two 十|shí|ten")],
     "en": "Six. Seven. Eight. Nine. Ten. Eleven (ten-one). Twenty (two-tens).",
     "qs": [{"q": "Which character means “nine”?", "choices": ["九", "六", "七", "八"], "a": 0},
            {"q": "十一 (ten-one) means…", "choices": ["eleven", "twelve", "twenty", "one"], "a": 0},
            {"q": "二十 (two-tens) means…", "choices": ["twenty", "twelve", "eleven", "two"], "a": 0}]},
    {"id": "r0-3", "level": "R0", "title": "人 我 你 他", "title_en": "People",
     "intro": "人 is a person walking. From it: I, you, and he.",
     "new_words": [("人", "rén", "person", [2]), ("我", "wǒ", "I, me", [3]),
                   ("你", "nǐ", "you", [3]), ("他", "tā", "he, him", [1])],
     "sentences": [_s("人|rén|person"), _s("我|wǒ|I"), _s("你|nǐ|you"), _s("他|tā|he")],
     "en": "Person. I. You. He.",
     "qs": [{"q": "Which one is “I”?", "choices": ["我", "你", "他", "人"], "a": 0},
            {"q": "他 means…", "choices": ["he", "you", "person", "I"], "a": 0}]},
    {"id": "r0-4", "level": "R0", "title": "大 小 好 口", "title_en": "Big, small, good",
     "intro": "大 is a person with arms stretched wide — big. 口 is an open mouth.",
     "new_words": [("大", "dà", "big", [4]), ("小", "xiǎo", "small", [3]),
                   ("好", "hǎo", "good", [3]), ("口", "kǒu", "mouth", [3])],
     "sentences": [_s("大|dà|big"), _s("小|xiǎo|small"), _s("好|hǎo|good"), _s("口|kǒu|mouth")],
     "en": "Big. Small. Good. Mouth.",
     "qs": [{"q": "Which character means “small”?", "choices": ["小", "大", "口", "好"], "a": 0},
            {"q": "好 means…", "choices": ["good", "big", "mouth", "small"], "a": 0}]},
    {"id": "r0-5", "level": "R0", "title": "日 月 山 水", "title_en": "Sun, moon, mountain, water",
     "intro": "Four little pictures: the sun, a crescent moon, three peaks, and flowing water.",
     "new_words": [("日", "rì", "sun; day", [4]), ("月", "yuè", "moon; month", [4]),
                   ("山", "shān", "mountain", [1]), ("水", "shuǐ", "water", [3])],
     "sentences": [_s("日|rì|sun"), _s("月|yuè|moon"), _s("山|shān|mountain"), _s("水|shuǐ|water")],
     "en": "Sun. Moon. Mountain. Water.",
     "qs": [{"q": "山 is a picture of…", "choices": ["mountain peaks", "the sun", "a mouth", "water"], "a": 0},
            {"q": "Which character means “water”?", "choices": ["水", "山", "月", "日"], "a": 0}]},

    # ── R1 — characters make words ────────────────────────────────────────────
    {"id": "r1-1", "level": "R1", "title": "你好", "title_en": "Hello",
     "intro": "You + good = hello. Add 吗 and any statement becomes a question.",
     "note": "Reading tip: ？ is the question mark, just like in English — and in "
             "Chinese it usually arrives with a question word like 吗 at the end.",
     "new_words": [("你好", "nǐ hǎo", "hello", [3, 3]), ("吗", "ma", "question word", [5]),
                   ("很", "hěn", "very; is", [3])],
     "sentences": [_s("你好|nǐ_hǎo|hello 。"),
                   _s("你|nǐ|you 好|hǎo|good 吗|ma|question_word ？"),
                   _s("我|wǒ|I 很|hěn|very 好|hǎo|good 。")],
     "en": "Hello. How are you? I'm fine.",
     "qs": [{"q": "“你好吗？” is asking…", "choices": ["how you are", "your name", "where you live", "what you want"], "a": 0},
            {"q": "你 + 好 together mean…", "choices": ["hello", "goodbye", "thanks", "yes"], "a": 0}]},
    {"id": "r1-2", "level": "R1", "title": "妈妈 爸爸", "title_en": "Mom and dad",
     "intro": "Doubling a character makes it warm: 妈妈, 爸爸. With family, 我妈妈 is simply “my mom.”",
     "new_words": [("妈妈", "mā ma", "mom", [1, 5]), ("爸爸", "bà ba", "dad", [4, 5])],
     "sentences": [_s("妈妈|mā_ma|mom 。"), _s("爸爸|bà_ba|dad 。"),
                   _s("我|wǒ|my 妈妈|mā_ma|mom 很|hěn|very 好|hǎo|good 。"),
                   _s("你|nǐ|your 爸爸|bà_ba|dad 好|hǎo|good 吗|ma|question_word ？")],
     "en": "Mom. Dad. My mom is well. Is your dad well?",
     "qs": [{"q": "我妈妈 means…", "choices": ["my mom", "your mom", "his mom", "a mom"], "a": 0},
            {"q": "The last line asks about…", "choices": ["your dad", "my dad", "your mom", "the weather"], "a": 0}]},
    {"id": "r1-3", "level": "R1", "title": "大 + 山 = 大山", "title_en": "Characters combine",
     "intro": "This is the trick that makes reading Chinese possible: characters you know combine into words you can guess.",
     "new_words": [("大人", "dà rén", "adult, grown-up", [4, 2]),
                   ("山水", "shān shuǐ", "landscape, scenery", [1, 3])],
     "sentences": [_s("大|dà|big 山|shān|mountain 。"),
                   _s("小|xiǎo|small 山|shān|mountain 。"),
                   _s("大人|dà_rén|adult 。"),
                   _s("山水|shān_shuǐ|landscape 。")],
     "en": "Big mountain. Small mountain (a hill). Big-person (an adult). Mountain-water (a landscape).",
     "qs": [{"q": "大人 — big + person — means…", "choices": ["an adult", "a giant", "a crowd", "a boss"], "a": 0},
            {"q": "山水 literally “mountains and water” means…", "choices": ["scenery", "a flood", "a well", "an island"], "a": 0}]},
    {"id": "r1-4", "level": "R1", "title": "是 不 — yes and no", "title_en": "To be, or not",
     "intro": "是 links things: A 是 B. 不 in front says no. Together: 不是, is not.",
     "new_words": [("是", "shì", "to be", [4]), ("不", "bù", "not", [4])],
     "sentences": [_s("是|shì|is 。"), _s("不|bù|not 。"), _s("不是|bú_shì|is_not 。"),
                   _s("我|wǒ|I 是|shì|am 大人|dà_rén|adult 。"),
                   _s("他|tā|he 不是|bú_shì|is_not 大人|dà_rén|adult 。")],
     "en": "Is. Not. Is not. I am an adult. He is not an adult.",
     "qs": [{"q": "不是 means…", "choices": ["is not", "is", "maybe", "also"], "a": 0},
            {"q": "Who is NOT an adult here?", "choices": ["him", "me", "mom", "everyone is"], "a": 0}]},

    # ── R2 — first sentences ──────────────────────────────────────────────────
    {"id": "r2-1", "level": "R2", "title": "我是老师", "title_en": "Who is who",
     "intro": "Your first full sentences about people.",
     "new_words": [("老师", "lǎo shī", "teacher", [3, 1]), ("她", "tā", "she, her", [1]),
                   ("谁", "shéi", "who", [2])],
     "sentences": [_s("我|wǒ|I 是|shì|am 老师|lǎo_shī|teacher 。"),
                   _s("她|tā|she 是|shì|is 我|wǒ|my 妈妈|mā_ma|mom 。"),
                   _s("他|tā|he 是|shì|is 我|wǒ|my 爸爸|bà_ba|dad 。"),
                   _s("你|nǐ|you 是|shì|are 谁|shéi|who ？")],
     "en": "I am a teacher. She is my mom. He is my dad. Who are you?",
     "qs": [{"q": "What is the speaker's job?", "choices": ["teacher", "doctor", "shopkeeper", "student"], "a": 0},
            {"q": "谁 asks…", "choices": ["who", "what", "where", "when"], "a": 0}]},
    {"id": "r2-2", "level": "R2", "title": "我要喝茶", "title_en": "I want tea",
     "intro": "要 wants things; 喝 drinks them.",
     "new_words": [("要", "yào", "to want", [4]), ("喝", "hē", "to drink", [1]),
                   ("茶", "chá", "tea", [2]), ("咖啡", "kā fēi", "coffee", [1, 1])],
     "sentences": [_s("我|wǒ|I 要|yào|want 喝|hē|drink 茶|chá|tea 。"),
                   _s("妈妈|mā_ma|mom 要|yào|wants 喝|hē|drink 咖啡|kā_fēi|coffee 。"),
                   _s("你|nǐ|you 要|yào|want 喝|hē|drink 水|shuǐ|water 吗|ma|question_word ？")],
     "en": "I want to drink tea. Mom wants to drink coffee. Do you want to drink water?",
     "qs": [{"q": "What does mom want?", "choices": ["coffee", "tea", "water", "nothing"], "a": 0},
            {"q": "The last sentence is…", "choices": ["a question", "a statement", "a story", "a name"], "a": 0}]},
    {"id": "r2-3", "level": "R2", "title": "我家有猫", "title_en": "My family",
     "intro": "有 means to have — and families are counted in 口, mouths.",
     "note": "Reading tip: 、 is the listing comma — it separates items in a list "
             "(爸爸、妈妈和我). The ordinary comma ， separates phrases.",
     "new_words": [("家", "jiā", "home, family", [1]), ("有", "yǒu", "to have", [3]),
                   ("猫", "māo", "cat", [1]), ("和", "hé", "and", [2])],
     "sentences": [_s("我|wǒ|my 家|jiā|family 有|yǒu|has 三|sān|three 口|kǒu|mouths_(family_measure) 人|rén|people 。"),
                   _s("爸爸|bà_ba|dad 、 妈妈|mā_ma|mom 和|hé|and 我|wǒ|me 。"),
                   _s("我|wǒ|my 家|jiā|family 有|yǒu|has 猫|māo|cat 。"),
                   _s("猫|māo|cat 很|hěn|very 小|xiǎo|small 。")],
     "en": "My family has three people. Dad, mom and me. My family has a cat. The cat is very small.",
     "qs": [{"q": "How many people are in the family?", "choices": ["three", "two", "four", "ten"], "a": 0},
            {"q": "What is small?", "choices": ["the cat", "the house", "dad", "the tea"], "a": 0}]},
    {"id": "r2-4", "level": "R2", "title": "你喜欢什么？", "title_en": "What do you like?",
     "intro": "喜欢 likes things — or whole activities.",
     "new_words": [("喜欢", "xǐ huan", "to like", [3, 5]), ("什么", "shén me", "what", [2, 5]),
                   ("吃", "chī", "to eat", [1]), ("米饭", "mǐ fàn", "cooked rice", [3, 4])],
     "sentences": [_s("我|wǒ|I 喜欢|xǐ_huan|like 喝|hē|drink 茶|chá|tea 。"),
                   _s("妈妈|mā_ma|mom 喜欢|xǐ_huan|likes 吃|chī|eat 米饭|mǐ_fàn|rice 。"),
                   _s("猫|māo|cat 不|bù|not 喜欢|xǐ_huan|like 米饭|mǐ_fàn|rice 。"),
                   _s("你|nǐ|you 喜欢|xǐ_huan|like 什么|shén_me|what ？")],
     "en": "I like drinking tea. Mom likes eating rice. The cat doesn't like rice. What do you like?",
     "qs": [{"q": "Who likes rice?", "choices": ["mom", "the cat", "the speaker", "dad"], "a": 0},
            {"q": "什么 means…", "choices": ["what", "who", "cat", "like"], "a": 0}]},
    {"id": "r2-5", "level": "R2", "title": "我去商店", "title_en": "To the shop",
     "intro": "去 goes places; 买 buys things — with 钱.",
     "new_words": [("去", "qù", "to go", [4]), ("商店", "shāng diàn", "shop", [1, 4]),
                   ("买", "mǎi", "to buy", [3]), ("钱", "qián", "money", [2])],
     "sentences": [_s("我|wǒ|I 去|qù|go 商店|shāng_diàn|shop 。"),
                   _s("我|wǒ|I 要|yào|want 买|mǎi|buy 茶|chá|tea 。"),
                   _s("我|wǒ|I 有|yǒu|have 钱|qián|money 。"),
                   _s("爸爸|bà_ba|dad 不|bú|not 去|qù|go 。")],
     "en": "I go to the shop. I want to buy tea. I have money. Dad isn't going.",
     "qs": [{"q": "What will the speaker buy?", "choices": ["tea", "rice", "coffee", "a cat"], "a": 0},
            {"q": "Who stays home?", "choices": ["dad", "mom", "the speaker", "the cat"], "a": 0}]},

    # ── R3 — dialogues ────────────────────────────────────────────────────────
    {"id": "r3-1", "level": "R3", "title": "在茶店", "title_en": "At the tea shop",
     "intro": "Your first conversation — buying tea, start to finish. The prices "
              "put your R0 numbers to work.",
     "note": "Reading tip: ！ is the exclamation mark, and dialogue lines are "
             "labeled with the speaker's name — tap a name to hear it.",
     "new_words": [("杯", "bēi", "cup (measure word)", [1]), ("多少", "duō shao", "how much", [1, 5]),
                   ("块", "kuài", "yuan (money)", [4]), ("老板", "lǎo bǎn", "shopkeeper, boss", [3, 3]),
                   ("谢谢", "xiè xie", "thanks", [4, 5])],
     "sentences": [_s("你好|nǐ_hǎo|hello ！ 我|wǒ|I 要|yào|want 一|yì|one 杯|bēi|cup 茶|chá|tea 。 多少|duō_shao|how_much 钱|qián|money ？", "安娜"),
                   _s("大|dà|big 杯|bēi|cup 十|shí|ten 块|kuài|yuan ， 小|xiǎo|small 杯|bēi|cup 五|wǔ|five 块|kuài|yuan 。", "老板"),
                   _s("要|yào|want 大|dà|big 杯|bēi|cup 。", "安娜"),
                   _s("好|hǎo|okay ！ 十|shí|ten 块|kuài|yuan 。", "老板"),
                   _s("谢谢|xiè_xie|thanks ！", "安娜")],
     "en": "Anna: Hello! I want a cup of tea. How much? — Shopkeeper: A large cup is ten yuan, a small one is five. — Anna: The large one, please. — Shopkeeper: Okay! Ten yuan. — Anna: Thanks!",
     "qs": [{"q": "What size does Anna choose?", "choices": ["large", "small", "medium", "none"], "a": 0},
            {"q": "How much does she pay?", "choices": ["10 yuan", "5 yuan", "3 yuan", "15 yuan"], "a": 0}]},
    {"id": "r3-2", "level": "R3", "title": "明天见", "title_en": "See you tomorrow",
     "intro": "Two friends run into each other. 呢 bounces a question back; 也 says “me too.”",
     "new_words": [("明天", "míng tiān", "tomorrow", [2, 1]), ("见", "jiàn", "to see, to meet", [4]),
                   ("再见", "zài jiàn", "goodbye", [4, 4]), ("呢", "ne", "and…? (bounce-back)", [5]),
                   ("也", "yě", "also", [3])],
     "sentences": [_s("你好|nǐ_hǎo|hello ， 安娜|Ān_nà|Anna ！ 你|nǐ|you 好|hǎo|well 吗|ma|question_word ？", "王明"),
                   _s("我|wǒ|I 很|hěn|very 好|hǎo|well ！ 你|nǐ|you 呢|ne|and_you ？", "安娜"),
                   _s("我|wǒ|I 也|yě|also 很|hěn|very 好|hǎo|well 。", "王明"),
                   _s("我|wǒ|I 去|qù|go 商店|shāng_diàn|shop 买|mǎi|buy 茶|chá|tea 。 明天|míng_tiān|tomorrow 见|jiàn|see ！", "安娜"),
                   _s("好|hǎo|okay ， 明天|míng_tiān|tomorrow 见|jiàn|see ！ 再见|zài_jiàn|goodbye ！", "王明")],
     "en": "Wang Ming: Hello, Anna! How are you? — Anna: I'm great! And you? — Wang Ming: I'm great too. — Anna: I'm off to the shop to buy tea. See you tomorrow! — Wang Ming: Okay, see you tomorrow! Bye!",
     "qs": [{"q": "Where is Anna going?", "choices": ["to the shop", "home", "to school", "to the mountain"], "a": 0},
            {"q": "When will they meet?", "choices": ["tomorrow", "today", "next week", "never"], "a": 0}]},
    {"id": "r3-3", "level": "R3", "title": "你家有几口人？", "title_en": "How many in your family?",
     "intro": "几 asks “how many” for small numbers — and 两, not 二, counts pairs of things.",
     "new_words": [("几", "jǐ", "how many", [3]),
                   ("妹妹", "mèi mei", "little sister", [4, 5]), ("两", "liǎng", "two (of something)", [3]),
                   ("只", "zhī", "(measure for animals)", [1])],
     "sentences": [_s("你|nǐ|your 家|jiā|family 有|yǒu|has 几|jǐ|how_many 口|kǒu|mouths 人|rén|people ？", "王明"),
                   _s("四|sì|four 口|kǒu|mouths 人|rén|people ： 爸爸|bà_ba|dad 、 妈妈|mā_ma|mom 、 我|wǒ|me 和|hé|and 我|wǒ|my 妹妹|mèi_mei|little_sister 。", "安娜"),
                   _s("你|nǐ|your 家|jiā|family 有|yǒu|has 猫|māo|cat 吗|ma|question_word ？", "王明"),
                   _s("有|yǒu|have ！ 我|wǒ|my 家|jiā|family 有|yǒu|has 两|liǎng|two 只|zhī|(measure) 猫|māo|cats 。", "安娜")],
     "en": "Wang Ming: How many people are in your family? — Anna: Four: dad, mom, me and my little sister. — Wang Ming: Does your family have a cat? — Anna: We do! We have two cats.",
     "qs": [{"q": "How many people are in Anna's family?", "choices": ["four", "three", "two", "five"], "a": 0},
            {"q": "How many cats?", "choices": ["two", "one", "four", "none"], "a": 0}]},

    # ── R4 — paragraphs ───────────────────────────────────────────────────────
    {"id": "r4-1", "level": "R4", "title": "今天天气很好", "title_en": "A fine day",
     "intro": "A whole little paragraph — notice 了 marking what got done.",
     "new_words": [("今天", "jīn tiān", "today", [1, 1]), ("天气", "tiān qì", "weather", [1, 4]),
                   ("热", "rè", "hot", [4]), ("冷", "lěng", "cold", [3]),
                   ("我们", "wǒ men", "we, us", [3, 5]), ("了", "le", "(done!)", [5]),
                   ("多", "duō", "many, much", [1])],
     "sentences": [_s("今天|jīn_tiān|today 天气|tiān_qì|weather 很|hěn|very 好|hǎo|good 。"),
                   _s("不|bú|not 热|rè|hot ， 不|bù|not 冷|lěng|cold 。"),
                   _s("我|wǒ|I 和|hé|and 妈妈|mā_ma|mom 去|qù|go 商店|shāng_diàn|shop 。"),
                   _s("我们|wǒ_men|we 买|mǎi|bought 了|le|(done) 很|hěn|very 多|duō|much 茶|chá|tea 。")],
     "en": "The weather is lovely today. Not hot, not cold. Mom and I go to the shop. We bought a lot of tea.",
     "qs": [{"q": "What's the weather like?", "choices": ["just right", "too hot", "too cold", "raining"], "a": 0},
            {"q": "What did they buy?", "choices": ["a lot of tea", "a little tea", "coffee", "rice"], "a": 0}]},
    {"id": "r4-2", "level": "R4", "title": "我的家", "title_en": "My family",
     "intro": "的 marks belonging — 我的家, my family. Meet everyone.",
     "new_words": [("的", "de", "'s (belonging)", [5]), ("医生", "yī shēng", "doctor", [1, 1]),
                   ("工作", "gōng zuò", "to work; job", [1, 4]), ("忙", "máng", "busy", [2]),
                   ("累", "lèi", "tired", [4]), ("每天", "měi tiān", "every day", [3, 1])],
     "sentences": [_s("我|wǒ|my 的|de|'s 家|jiā|family 有|yǒu|has 四|sì|four 口|kǒu|mouths 人|rén|people 。"),
                   _s("我|wǒ|my 妈妈|mā_ma|mom 是|shì|is 医生|yī_shēng|doctor 。"),
                   _s("她|tā|she 每天|měi_tiān|every_day 工作|gōng_zuò|works ， 很|hěn|very 忙|máng|busy ， 也|yě|also 很|hěn|very 累|lèi|tired 。"),
                   _s("我|wǒ|my 爸爸|bà_ba|dad 不是|bú_shì|is_not 医生|yī_shēng|doctor ， 他|tā|he 是|shì|is 老师|lǎo_shī|teacher 。"),
                   _s("我|wǒ|I 和|hé|and 妹妹|mèi_mei|little_sister 喜欢|xǐ_huan|like 我们|wǒ_men|our 的|de|'s 家|jiā|home 。")],
     "en": "My family has four people. My mom is a doctor. She works every day — very busy, and very tired too. My dad isn't a doctor; he's a teacher. My little sister and I love our home.",
     "qs": [{"q": "What is mom's job?", "choices": ["doctor", "teacher", "shopkeeper", "driver"], "a": 0},
            {"q": "How does mom feel?", "choices": ["busy and tired", "bored", "cold", "hungry"], "a": 0},
            {"q": "Who is a teacher?", "choices": ["dad", "mom", "the sister", "nobody"], "a": 0}]},
    {"id": "r4-3", "level": "R4", "title": "小猫要吃什么？", "title_en": "What does the kitten want?",
     "intro": "A tiny scene at home. 它 is “it” — for animals and things.",
     "note": "Reading tip: speech is quoted with ：“ … ” — a colon and double "
             "quotes, right where English would use a comma and quotes.",
     "new_words": [("它", "tā", "it", [1]), ("鱼", "yú", "fish", [2]),
                   ("给", "gěi", "to give", [3]), ("看", "kàn", "to look at", [4]),
                   ("说", "shuō", "to say, to speak", [1]), ("喵", "miāo", "meow", [1])],
     "sentences": [_s("我|wǒ|my 家|jiā|family 的|de|'s 小|xiǎo|little 猫|māo|cat 很|hěn|very 好|hǎo|nice 。"),
                   _s("它|tā|it 不|bù|not 吃|chī|eat 米饭|mǐ_fàn|rice 。"),
                   _s("我|wǒ|I 给|gěi|give 它|tā|it 鱼|yú|fish 。 一|yī|one 、 二|èr|two 、 三|sān|three ！"),
                   _s("它|tā|it 看|kàn|looks_at 我|wǒ|me ， 说|shuō|says ： “ 喵|miāo|meow ！ ”"),
                   _s("妈妈|mā_ma|mom 说|shuō|says ： 小|xiǎo|little 猫|māo|cat 很|hěn|really 喜欢|xǐ_huan|likes 你|nǐ|you ！")],
     "en": "Our little cat is lovely. It doesn't eat rice. I give it fish — one, two, three! It looks at me and says: “Meow!” Mom says: the kitten really likes you!",
     "qs": [{"q": "What won't the cat eat?", "choices": ["rice", "fish", "tea", "anything"], "a": 0},
            {"q": "How many fish does it get?", "choices": ["three", "one", "two", "none"], "a": 0}]},

    # ── R5 — short stories ────────────────────────────────────────────────────
    {"id": "r5-1", "level": "R5", "title": "小马找朋友", "title_en": "The little horse looks for a friend",
     "intro": "Your first story with a beginning, a middle, and an end.",
     "new_words": [("马", "mǎ", "horse", [3]), ("上", "shàng", "on, on top of", [4]),
                   ("找", "zhǎo", "to look for", [3]),
                   ("朋友", "péng you", "friend", [2, 5]), ("来", "lái", "to come", [2]),
                   ("没有", "méi yǒu", "to not have", [2, 3]), ("高兴", "gāo xìng", "happy", [1, 4]),
                   ("现在", "xiàn zài", "now", [4, 4])],
     "sentences": [_s("山|shān|mountain 上|shàng|on_top 有|yǒu|there_is 一|yì|one 只|zhī|(measure) 小|xiǎo|little 马|mǎ|horse 。"),
                   _s("小|xiǎo|little 马|mǎ|horse 没有|méi_yǒu|doesn't_have 朋友|péng_you|friend 。"),
                   _s("它|tā|it 去|qù|goes 找|zhǎo|look_for 朋友|péng_you|friend 。"),
                   _s("它|tā|it 看|kàn|looks_at 大|dà|big 山|shān|mountain ， 看|kàn|looks_at 山水|shān_shuǐ|scenery ， 不|bú|not 看|kàn|see 人|rén|anyone 。"),
                   _s("一|yì|one 只|zhī|(measure) 小|xiǎo|little 猫|māo|cat 来|lái|comes 了|le|(done) ， 说|shuō|says ： “ 你好|nǐ_hǎo|hello ！ 你|nǐ|you 要|yào|want 朋友|péng_you|friend 吗|ma|question_word ？ ”"),
                   _s("小|xiǎo|little 马|mǎ|horse 说|shuō|says ： “ 要|yào|yes_I_want ！ ”"),
                   _s("现在|xiàn_zài|now 小|xiǎo|little 马|mǎ|horse 有|yǒu|has 朋友|péng_you|friend 了|le|(done) ， 它|tā|it 很|hěn|very 高兴|gāo_xìng|happy 。")],
     "en": "On the mountain there lives a little horse. The little horse has no friends. It goes looking for one. It sees the big mountain, sees the scenery — but no one at all. A little cat comes along and says: “Hello! Do you want a friend?” The little horse says: “Yes!” Now the little horse has a friend, and it is very happy.",
     "qs": [{"q": "What is the little horse looking for?", "choices": ["a friend", "food", "water", "its mom"], "a": 0},
            {"q": "Who comes along?", "choices": ["a little cat", "a big horse", "a person", "a fish"], "a": 0},
            {"q": "How does the story end?", "choices": ["the horse is happy", "the horse is lost", "it rains", "the cat leaves"], "a": 0}]},
    {"id": "r5-2", "level": "R5", "title": "下雨了", "title_en": "It's raining",
     "intro": "A rainy day at home — and 吧, the gentle “let's.”",
     "new_words": [("下雨", "xià yǔ", "to rain", [4, 3]), ("在", "zài", "at; -ing", [4]),
                   ("书", "shū", "book", [1]), ("吧", "ba", "let's… (suggestion)", [5]),
                   ("天", "tiān", "day; sky", [1])],
     "sentences": [_s("今天|jīn_tiān|today 下雨|xià_yǔ|rains 了|le|(done) 。"),
                   _s("我们|wǒ_men|we 不|bú|not 去|qù|go 商店|shāng_diàn|shop 。"),
                   _s("我|wǒ|I 在|zài|at 家|jiā|home 看|kàn|read 书|shū|book 。"),
                   _s("妹妹|mèi_mei|little_sister 在|zài|is_-ing 看|kàn|watching 小|xiǎo|little 猫|māo|cat 。"),
                   _s("妈妈|mā_ma|mom 说|shuō|says ： “ 我们|wǒ_men|we 喝|hē|drink 茶|chá|tea 吧|ba|let's 。 ”"),
                   _s("爸爸|bà_ba|dad 说|shuō|says ： “ 好|hǎo|great ！ 我|wǒ|I 也|yě|also 要|yào|want 一|yì|one 杯|bēi|cup ！ ”"),
                   _s("下雨|xià_yǔ|rainy 天|tiān|day 也|yě|also 很|hěn|very 好|hǎo|good 。")],
     "en": "It's raining today. We're not going to the shop. I read a book at home. My little sister is watching the kitten. Mom says: “Let's have some tea.” Dad says: “Great! I want a cup too!” Rainy days are lovely too.",
     "qs": [{"q": "Why does no one go to the shop?", "choices": ["it's raining", "it's closed", "no money", "too far"], "a": 0},
            {"q": "What is the speaker doing?", "choices": ["reading a book", "watching the cat", "drinking coffee", "sleeping"], "a": 0},
            {"q": "The story's feeling is…", "choices": ["cozy", "scary", "sad", "angry"], "a": 0}]},

    # ── R6 — a full story ─────────────────────────────────────────────────────
    {"id": "r6-1", "level": "R6", "title": "安娜去中国", "title_en": "Anna goes to China",
     "intro": "Everything you've read comes together: a full story, three parts, no pinyin unless you ask.",
     "new_words": [("中国", "Zhōng guó", "China", [1, 2]), ("汉语", "Hàn yǔ", "Chinese language", [4, 3]),
                   ("想", "xiǎng", "to want to; to think", [3]), ("坐", "zuò", "to take (transport); to sit", [4]),
                   ("飞机", "fēi jī", "airplane", [1, 1]), ("新", "xīn", "new", [1]),
                   ("他们", "tā men", "they, them", [1, 5]), ("明年", "míng nián", "next year", [2, 2]),
                   ("还", "hái", "still; again", [2])],
     "sentences": [_s("安娜|Ān_nà|Anna 很|hěn|really 喜欢|xǐ_huan|likes 汉语|Hàn_yǔ|Chinese 。"),
                   _s("她|tā|she 每天|měi_tiān|every_day 看|kàn|reads 书|shū|books ， 每天|měi_tiān|every_day 说|shuō|speaks 汉语|Hàn_yǔ|Chinese 。"),
                   _s("她|tā|she 想|xiǎng|wants_to 去|qù|go 中国|Zhōng_guó|China 。"),
                   _s("二月|èr_yuè|February 八日|bā_rì|the_8th ， 她|tā|she 坐|zuò|takes 飞机|fēi_jī|airplane 去|qù|to 中国|Zhōng_guó|China 。"),
                   _s("中国|Zhōng_guó|China 很|hěn|very 大|dà|big ！ 天气|tiān_qì|weather 很|hěn|very 好|hǎo|good 。"),
                   _s("她|tā|she 去|qù|goes_to 商店|shāng_diàn|shop 买|mǎi|buy 茶|chá|tea ， 说|shuō|says ： “ 我|wǒ|I 要|yào|want 一|yì|one 杯|bēi|cup 茶|chá|tea ， 谢谢|xiè_xie|thanks ！ ”"),
                   _s("老板|lǎo_bǎn|shopkeeper 说|shuō|says ： “ 你|nǐ|your 的|de|'s 汉语|Hàn_yǔ|Chinese 很|hěn|very 好|hǎo|good ！ ”"),
                   _s("安娜|Ān_nà|Anna 很|hěn|very 高兴|gāo_xìng|happy 。"),
                   _s("在|zài|in 中国|Zhōng_guó|China ， 安娜|Ān_nà|Anna 有|yǒu|has 了|le|(done) 很|hěn|very 多|duō|many 新|xīn|new 朋友|péng_you|friends 。"),
                   _s("他们|tā_men|they 和|hé|with 她|tā|her 说|shuō|speak 汉语|Hàn_yǔ|Chinese ， 喝|hē|drink 茶|chá|tea ， 看|kàn|look_at 大|dà|big 山|shān|mountains 。"),
                   _s("安娜|Ān_nà|Anna 说|shuō|says ： “ 我|wǒ|I 很|hěn|really 喜欢|xǐ_huan|like 中国|Zhōng_guó|China ！ 明年|míng_nián|next_year 我|wǒ|I 还|hái|again 要|yào|will 来|lái|come ！ ”")],
     "en": "Anna really likes Chinese. Every day she reads, and every day she speaks Chinese. She wants to go to China. On February 8th, she takes a plane to China. China is huge! The weather is beautiful. She goes to a shop to buy tea and says: “One cup of tea please, thank you!” The shopkeeper says: “Your Chinese is really good!” Anna is delighted. In China, Anna makes many new friends. They speak Chinese with her, drink tea, and look at the big mountains. Anna says: “I love China! Next year I'm coming back!”",
     "qs": [{"q": "How does Anna get to China?", "choices": ["by plane", "by train", "by boat", "on foot"], "a": 0},
            {"q": "What does the shopkeeper praise?", "choices": ["her Chinese", "her hat", "her money", "her friend"], "a": 0},
            {"q": "What does Anna do with her new friends?", "choices": ["speak Chinese and drink tea", "play football", "watch movies", "go fishing"], "a": 0},
            {"q": "What does she promise at the end?", "choices": ["to come back next year", "to move to China", "to open a shop", "to buy a horse"], "a": 0}]},
]

_LEVEL_IDX = {lv["id"]: lv["idx"] for lv in LEVELS}
_BY_ID = {t["id"]: t for t in TEXTS}


def get_text(tid):
    return _BY_ID.get(tid)


def _level_complete(done, level_id):
    return all(t["id"] in done for t in TEXTS if t["level"] == level_id)


def open_through(state, stage_idx):
    """Highest open level index: sequential progress, with the speaking stage
    as a floor so a placed learner starts reading at their level."""
    done = state.get("reader", {})
    first_incomplete = len(LEVELS) - 1
    for lv in LEVELS:
        if not _level_complete(done, lv["id"]):
            first_incomplete = lv["idx"]
            break
    return min(len(LEVELS) - 1, max(first_incomplete, stage_idx))


def next_text(state, stage_idx):
    """The next unread text in an open level, in ladder order — what the
    recommendation engine points at."""
    done = state.get("reader", {})
    limit = open_through(state, stage_idx)
    for t in TEXTS:
        if _LEVEL_IDX[t["level"]] <= limit and t["id"] not in done:
            return t
    return None


def view(state, stage_idx):
    """The Read tab's payload: levels with per-text status, no bodies."""
    done = state.get("reader", {})
    limit = open_through(state, stage_idx)
    nxt = next_text(state, stage_idx)
    levels = []
    for lv in LEVELS:
        texts = [{"id": t["id"], "title": t["title"], "title_en": t["title_en"],
                  "words": len(t["new_words"]),
                  "done": t["id"] in done,
                  "score": done.get(t["id"], {}).get("score")}
                 for t in TEXTS if t["level"] == lv["id"]]
        levels.append({**{k: lv[k] for k in ("id", "idx", "zh", "name", "desc", "ruby")},
                       "open": lv["idx"] <= limit,
                       "complete": _level_complete(done, lv["id"]),
                       "texts": texts})
    return {"levels": levels, "open_through": limit,
            "next": nxt["id"] if nxt else None,
            "read_count": len(done), "text_count": len(TEXTS)}


def text_payload(tid):
    """Full text for the reader view (adds the level's ruby default)."""
    t = get_text(tid)
    if not t:
        return None
    return {**t, "new_words": [{"hanzi": w[0], "pinyin": w[1], "english": w[2],
                                "tones": w[3]} for w in t["new_words"]],
            "ruby": LEVELS[_LEVEL_IDX[t["level"]]]["ruby"]}


def complete(state, tid, score):
    """Mark a text read and return the new words that should join the SRS deck
    (caller adds them via learner.add_word — reading builds the vocabulary)."""
    t = get_text(tid)
    if not t:
        return None
    import datetime
    state.setdefault("reader", {})[tid] = {
        "date": datetime.date.today().isoformat(), "score": score}
    return t["new_words"]
